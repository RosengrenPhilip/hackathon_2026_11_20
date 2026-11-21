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
    TODO(A): call Claude via _call_json with prompts/vagueness.txt.
    """
    return None


def clarify(text: str, answers: dict) -> str | None:
    """One first-person sentence built ONLY from what she picked in `answers`
    ({"feelings": [...], "body": [...], "duration": str|None}). Never add anything she didn't pick.
    Returns the sentence, or None on failure (vagueness.py then uses a template).
    TODO(A): call Claude via _call_json with prompts/clarify.txt.
    """
    return None


# =====================================================================
# PERSON B: summary with sources
# Only edit inside this section. Prompt: prompts/summary.txt
# =====================================================================
def summarize(entries: list[dict]) -> dict | None:
    """Short running-text summary of the given entries.
    Input per entry: id, date, text (her original words) and answers (what she picked).
    The clarification sentence must NOT be sent - the summary is built from her own words + answers.
    Returns {"sentences": [{"text": str, "sources": ["E2", ...]}]} or None on failure.
    TODO(B): call Claude via _call_json with prompts/summary.txt.
    """
    return None
