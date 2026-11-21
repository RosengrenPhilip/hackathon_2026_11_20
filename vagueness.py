"""PERSON A owns this file: detect vagueness + help her be more specific.

Contract (don't change without telling the team):
  handle_new_entry(day, text) - called by app.py when she clicks "Save entry".
      Not vague -> saves right away via entries.add_entry(day, text).
      Vague     -> stores st.session_state.pending = {"day", "text", "phrases", "question", "feelings"}.
  render_pending(day)         - called by app.py under the entry box. Shows the help flow if pending.
      Optional: she can always "Save as is".
      On save: entries.add_entry(day, text, answers, clarification).
"""
import re
from datetime import date
from pathlib import Path

import streamlit as st

import claude_client
import entries

FEELINGS_FILE = Path(__file__).parent / "data" / "feelings.txt"
BODY = ["Head", "Throat", "Chest", "Stomach", "Shoulders", "Whole body", "Nowhere specific"]
DURATION = ["Today", "A few days", "A few weeks", "Months", "As long as I remember"]
FALLBACK_FEELINGS = ["numb", "tired", "anxious", "irritated", "lonely", "overwhelmed"]
VAGUE_WORDS = ["idk", "just off", "off", "weird", "meh", "bad day", "fine", "whatever",
               "don't know", "not great", "strange", "kinda", "something"]


@st.cache_data
def feelings_wheel() -> str:
    return FEELINGS_FILE.read_text(encoding="utf-8")


def _fallback_detect(text: str) -> dict:
    clean = " " + re.sub(r"[^\w' ]", " ", text.lower()) + " "
    found = [w for w in VAGUE_WORDS if f" {w} " in clean]
    phrases = [w for w in found if not any(w != o and w in o for o in found)]  # "off" inside "just off"
    return {"is_vague": bool(phrases), "vague_phrases": phrases,
            "question": "What fits best for you?", "feeling_options": FALLBACK_FEELINGS}


def _fallback_clarify(answers: dict) -> str:
    parts = []
    if answers["feelings"]:
        parts.append("I've felt " + ", ".join(answers["feelings"]))
    if answers["body"]:
        parts.append("I notice it in my " + " and ".join(b.lower() for b in answers["body"]))
    if answers["duration"]:
        parts.append(f"({answers['duration'].lower()})")
    return " - ".join(parts) + "."


def _highlight(text: str, phrases: list[str]) -> str:
    for p in phrases:
        i = text.lower().find(p.lower())
        if i >= 0:
            text = text[:i] + f":orange-background[{text[i:i + len(p)]}]" + text[i + len(p):]
    return text


def _clear() -> None:
    for k in ["pending", "wf_words", "wf_body", "wf_feelings", "wf_body_parts", "wf_duration"]:
        st.session_state.pop(k, None)


def handle_new_entry(day: date, text: str) -> None:
    with st.spinner("Reading your entry..."):
        result = claude_client.detect_vagueness(text, feelings_wheel()) or _fallback_detect(text)
    if not result["is_vague"]:
        entries.add_entry(day, text)
        st.toast("Saved")
        return
    st.session_state.pending = {
        "day": day, "text": text, "phrases": result["vague_phrases"],
        "question": result.get("question") or "What fits best for you?",
        "feelings": result.get("feeling_options") or FALLBACK_FEELINGS,
    }


def render_pending(day: date) -> None:
    p = st.session_state.get("pending")
    if not p or p["day"] != day:
        return
    with st.container(border=True):
        st.markdown(_highlight(p["text"], p["phrases"]))
        st.caption("Some of this sounds a bit hard to pin down. Want help putting it into words? (optional)")

        c1, c2 = st.columns(2)
        if c1.button("Help me find the words", key="wf_words_btn", use_container_width=True):
            st.session_state.wf_words = True
        if c2.button("Mark where in my body", key="wf_body_btn", use_container_width=True):
            st.session_state.wf_body = True

        feelings, body, duration = [], [], None
        if st.session_state.get("wf_words"):
            feelings = st.pills(p["question"], p["feelings"], selection_mode="multi", key="wf_feelings") or []
        if st.session_state.get("wf_body"):
            body = st.pills("Where do you notice it?", BODY, selection_mode="multi", key="wf_body_parts") or []
            duration = st.pills("How long has it felt like this?", DURATION, key="wf_duration")

        s1, s2 = st.columns(2)
        picked = bool(feelings or body or duration)
        if s1.button("Save with these", key="wf_save", type="primary", disabled=not picked,
                     use_container_width=True):
            answers = {"feelings": feelings, "body": body, "duration": duration}
            with st.spinner("Putting it into words..."):
                clarification = claude_client.clarify(p["text"], answers) or _fallback_clarify(answers)
            entries.add_entry(day, p["text"], answers, clarification)
            _clear()
            st.rerun()
        if s2.button("Save as is", key="wf_skip", use_container_width=True):
            entries.add_entry(day, p["text"])
            _clear()
            st.rerun()
