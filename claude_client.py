"""All Claude API calls live here. Every call returns parsed JSON, or a safe fallback."""
import json
import os
from pathlib import Path

import anthropic
import streamlit as st

MODEL = "claude-sonnet-5-5"
ROOT = Path(__file__).parent
PROMPTS = ROOT / "prompts"
DATA = ROOT / "data"


def _secret(name: str) -> str | None:
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.environ.get(name)


@st.cache_resource
def _client() -> anthropic.Anthropic:
    # Org-level keys (not scoped to a workspace) must name the workspace to bill.
    workspace = _secret("ANTHROPIC_WORKSPACE_ID")
    headers = {"anthropic-workspace-id": workspace} if workspace else None
    return anthropic.Anthropic(api_key=_secret("ANTHROPIC_API_KEY"), default_headers=headers)


@st.cache_data
def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.txt").read_text(encoding="utf-8")


@st.cache_data
def _examples_block() -> str:
    path = DATA / "examples.json"
    if not path.exists():
        return ""
    examples = json.loads(path.read_text(encoding="utf-8"))
    return "\n\n".join(
        f"Client: {e['question']}\nCounselor: {e['answer']}" for e in examples
    )


def _call_json(system: str, user: str, schema: dict, effort: str = "medium") -> dict | None:
    """One Claude call constrained to `schema`. Returns parsed dict, or None on any failure."""
    try:
        response = _client().beta.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={
                "effort": effort,
                "format": {"type": "json_schema", "schema": schema},
            },
            # If a safety classifier declines, retry server-side on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIError as e:
        st.session_state["last_error"] = f"Claude API error, please try again. ({e})"
        return None
    except TypeError:  # raised by the SDK when no API key is configured
        st.session_state["last_error"] = "No ANTHROPIC_API_KEY found in .streamlit/secrets.toml."
        return None

    if response.stop_reason == "refusal":
        st.session_state["last_error"] = "Claude declined this request."
        return None
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        st.session_state["last_error"] = "Could not read Claude's reply."
        return None



# =====================================================================
# PERSON A: vagueness detection + clarification
# Only edit inside this section. Prompts: prompts/vagueness.txt, prompts/clarify.txt
# =====================================================================
def detect_vagueness(text: str, feelings_wheel: str) -> dict | None:
    """Is this journal entry vague about how she feels?
    Returns {"is_vague": bool,
             "vague_phrases": [exact substrings of text, e.g. "just off"],
             "question": gentle "what fits best for you?"-style question,
             "feeling_options": [6 words from the feelings wheel that might fit]}
    or None on failure (vagueness.py then uses a keyword fallback).
    """
    system = _prompt("vagueness").replace("{feelings_wheel}", feelings_wheel)
    result = _call_json(system, f"Journal entry:\n{text}", _VAGUENESS_SCHEMA, effort="low")
    if result is None:
        return None
    if not result["is_vague"]:
        return {"is_vague": False, "vague_phrases": [], "question": "", "feeling_options": []}

    # Only keep phrases that really appear in her text (otherwise highlighting can't find them).
    lowered = text.lower()
    phrases = [p for p in result["vague_phrases"] if p.strip() and p.lower() in lowered][:3]
    # Only keep feeling words that are really on the wheel.
    wheel = _wheel_words(feelings_wheel)
    options = list(dict.fromkeys(w.lower() for w in result["feeling_options"] if w.lower() in wheel))[:6]
    return {
        "is_vague": True,
        "vague_phrases": phrases,
        "question": result["question"].strip(),
        "feeling_options": options if len(options) >= 3 else [],  # [] -> vagueness.py fallback words
    }


def clarify(text: str, answers: dict) -> str | None:
    """One first-person sentence built ONLY from what she picked in `answers`
    ({"feelings": [...], "body": [...], "duration": str|None}). Never add anything she didn't pick.
    Returns the sentence, or None on failure (vagueness.py then uses a template).
    `text` is deliberately NOT sent to Claude, so nothing beyond her picks can leak into the sentence.
    """
    picks = {"feelings": answers.get("feelings") or [], "body": answers.get("body") or [],
             "duration": answers.get("duration")}
    result = _call_json(_prompt("clarify"), json.dumps(picks), _CLARIFY_SCHEMA, effort="low")
    if result is None:
        return None
    sentence = result["sentence"].strip()
    return sentence or None


_VAGUENESS_SCHEMA = {
    "type": "object",
    "properties": {
        "is_vague": {"type": "boolean"},
        "vague_phrases": {"type": "array", "items": {"type": "string"}},
        "question": {"type": "string"},
        "feeling_options": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["is_vague", "vague_phrases", "question", "feeling_options"],
    "additionalProperties": False,
}

_CLARIFY_SCHEMA = {
    "type": "object",
    "properties": {"sentence": {"type": "string"}},
    "required": ["sentence"],
    "additionalProperties": False,
}


def _wheel_words(feelings_wheel: str) -> set[str]:
    """All words on the wheel ("Sad: lonely, empty" -> {"sad", "lonely", "empty"})."""
    words = set()
    for line in feelings_wheel.splitlines():
        if ":" in line and not line.startswith("#"):
            core, rest = line.split(":", 1)
            words.add(core.strip().lower())
            words.update(w.strip().lower() for w in rest.split(",") if w.strip())
    return words


# =====================================================================
# PERSON B: summary with sources
# Only edit inside this section. Prompt: prompts/summary.txt
# =====================================================================
def summarize(entries: list[dict]) -> dict | None:
    """Short running-text summary of the given entries.
    Input per entry: id, date, text (her original words) and answers (what she picked).
    The clarification sentence must NOT be sent - the summary is built from her own words + answers.
    Returns {"sentences": [{"text": str, "sources": ["E2", ...]}]} or None on failure.
    """
    # Send only the allowed fields, even if a caller passes more (e.g. the clarification).
    payload = [{k: e.get(k) for k in ("id", "date", "text", "answers")} for e in entries]
    result = _call_json(_prompt("summary"), json.dumps(payload, ensure_ascii=False), _SUMMARY_SCHEMA)
    if result is None:
        return None

    # Keep only source IDs that really exist; drop sentences left without a source.
    valid_ids = {e["id"] for e in entries}
    sentences = []
    for s in result["sentences"]:
        sources = list(dict.fromkeys(src for src in s["sources"] if src in valid_ids))
        text = s["text"].strip()
        if text and sources:
            sentences.append({"text": text, "sources": sources})
    if not sentences:
        st.session_state["last_error"] = "The summary came back empty, showing your entries instead."
        return None
    return {"sentences": sentences}


_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "sentences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "sources"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["sentences"],
    "additionalProperties": False,
}
