"""Layout + state + wiring. SHARED: keep edits tiny, or ask the team first."""
import json
from datetime import date
from pathlib import Path

import streamlit as st

import brief
import claude_client
import questions
import safety
from auth import require_password

st.set_page_config(page_title="Pre-visit companion", layout="wide")
require_password()

DATA = Path(__file__).parent / "data"


def init_state():
    if "notes" not in st.session_state:
        st.session_state.notes = json.loads((DATA / "sara.json").read_text(encoding="utf-8"))
    st.session_state.setdefault("questions", [])  # see questions.py for item format
    st.session_state.setdefault("asked", [])  # every question text ever shown
    st.session_state.setdefault("brief", [])  # see questions.py for line format
    st.session_state.setdefault("highlight", set())  # note IDs to highlight (receipts)


def next_note_id() -> str:
    nums = [int(n["id"][1:]) for n in st.session_state.notes if n["id"][1:].isdigit()]
    return f"E{max(nums, default=0) + 1}"


init_state()
safety.render_banner()

st.title("Pre-visit companion")
st.caption("Others summarize what patients say. We help patients say it.")

left, right = st.columns(2, gap="large")

# ---------------- LEFT: Notes ----------------
with left:
    st.subheader("My notes")
    for i, note in enumerate(st.session_state.notes):
        label = f"**{note['id']}** · {note['date']}"
        if note["id"] in st.session_state.highlight:
            label = f":orange-background[{label} · source]"
        with st.container(border=True):
            st.markdown(label)
            new_text = st.text_area(
                "Note", note["text"], key=f"note_{note['id']}", label_visibility="collapsed"
            )
            st.session_state.notes[i]["text"] = new_text

    with st.form("add_note", clear_on_submit=True):
        text = st.text_area("New note", placeholder="How was today?")
        if st.form_submit_button("Add note") and text.strip():
            note_id = next_note_id()
            st.session_state.notes.append(
                {"id": note_id, "date": date.today().isoformat(), "text": text.strip()}
            )
            safety.check_text(text, source=f"note {note_id}")
            st.rerun()

# ---------------- RIGHT: Brief + questions ----------------
with right:
    st.subheader("My visit brief")
    brief.render_brief()

    if st.button("Reflect on my week", type="primary", use_container_width=True):
        st.session_state.pop("last_error", None)
        with st.spinner("Reading your notes..."):
            qs = claude_client.get_questions(st.session_state.notes, st.session_state.asked)
        st.session_state.questions = qs
        st.session_state.asked += [q["question"] for q in qs]

    if err := st.session_state.get("last_error"):
        st.warning(err)

    questions.render_questions()
