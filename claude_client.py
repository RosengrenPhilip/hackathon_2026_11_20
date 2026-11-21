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


def _notes_block(notes: list[dict]) -> str:
    return "\n".join(f"[{n['id']}] {n['date']}: {n['text']}" for n in notes)


QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "note_id": {"type": "string"},
                    "angle": {
                        "type": "string",
                        "enum": ["body", "situations", "people", "changes", "goals"],
                    },
                },
                "required": ["question", "note_id", "angle"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}


def get_questions(notes: list[dict], asked: list[str]) -> list[dict]:
    """Return 3 questions [{question, note_id, angle}], each tied to a real note."""
    system = _prompt("questions").replace("{examples}", _examples_block())
    previously = "\n".join(f"- {q}" for q in asked) or "(none yet)"
    user = (
        f"<notes>\n{_notes_block(notes)}\n</notes>\n\n"
        f"<previously_asked>\n{previously}\n</previously_asked>\n\n"
        "Write 3 new questions."
    )
    data = _call_json(system, user, QUESTIONS_SCHEMA)
    if not data:
        return []
    valid_ids = {n["id"] for n in notes}
    return [q for q in data.get("questions", []) if q.get("note_id") in valid_ids][:3]


# =====================================================================
# PERSON A (feature/questions): answer -> brief line
# Only edit inside this section. Prompt: prompts/brief_line.txt
# =====================================================================
def answer_to_brief_line(question: str, answer: str, note_id: str, notes: list[dict]) -> dict | None:
    """Turn her answer into ONE first-person brief line.
    Returns {"text": str, "sources": ["E2", ...], "section": str} or None on failure.
    TODO(A): call Claude via _call_json with prompts/brief_line.txt.
    """
    return {"text": answer.strip(), "sources": [note_id], "section": "What I want from today"}


# =====================================================================
# PERSON B (feature/wordfinder): word finder
# Only edit inside this section. Prompt: prompts/wordfinder.txt
# =====================================================================
def wordfinder_options(answer: str, note_text: str) -> dict | None:
    """Suggest 6 feeling words from data/feelings.txt that might fit.
    Returns {"feelings": [6 words]} or None.
    TODO(B): call Claude via _call_json.
    """
    return None


def rephrase(answer: str, feelings: list[str], body: list[str], duration: str | None) -> str | None:
    """Write ONE first-person sentence using ONLY what she picked. Never add symptoms.
    TODO(B): call Claude via _call_json.
    """
    return None


# =====================================================================
# FROZEN (was person C): crisis check - not used, safety.py uses keywords
# Nobody edits this section.
# =====================================================================
def crisis_check(text: str) -> dict | None:
    """Check text for self-harm, hopelessness, plans.
    Returns {"crisis": bool, "reason": str} or None on failure (safety.py then uses keywords).
    TODO(C): call Claude via _call_json with prompts/safety.txt.
    """
    return None
