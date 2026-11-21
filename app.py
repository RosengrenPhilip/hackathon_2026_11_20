import json
from datetime import date
from pathlib import Path

import streamlit as st

import claude_client

st.set_page_config(page_title="Pre-visit companion", layout="wide")

DATA = Path(__file__).parent / "data"


def init_state():
    if "notes" not in st.session_state:
        st.session_state.notes = json.loads((DATA / "sara.json").read_text(encoding="utf-8"))
    st.session_state.setdefault("questions", [])
    st.session_state.setdefault("asked", [])
    st.session_state.setdefault("brief", [])


def next_note_id() -> str:
    nums = [int(n["id"][1:]) for n in st.session_state.notes if n["id"][1:].isdigit()]
    return f"E{max(nums, default=0) + 1}"


init_state()

st.title("Pre-visit companion")
st.caption("Others summarize what patients say. We help patients say it.")

left, right = st.columns(2, gap="large")

# ---------------- LEFT: Notes ----------------
with left:
    st.subheader("My notes")
    for i, note in enumerate(st.session_state.notes):
        with st.container(border=True):
            st.markdown(f"**{note['id']}** · {note['date']}")
            new_text = st.text_area(
                "Note", note["text"], key=f"note_{note['id']}", label_visibility="collapsed"
            )
            st.session_state.notes[i]["text"] = new_text

    with st.form("add_note", clear_on_submit=True):
        text = st.text_area("New note", placeholder="How was today?")
        if st.form_submit_button("Add note") and text.strip():
            st.session_state.notes.append(
                {"id": next_note_id(), "date": date.today().isoformat(), "text": text.strip()}
            )
            st.rerun()

# ---------------- RIGHT: Brief + questions ----------------
with right:
    st.subheader("My visit brief")
    with st.container(border=True):
        st.markdown("**What I want from today**")
        st.caption("Answer questions below to build your brief.")

    if st.button("Reflect on my week", type="primary", use_container_width=True):
        st.session_state.pop("last_error", None)
        with st.spinner("Reading your notes..."):
            qs = claude_client.get_questions(st.session_state.notes, st.session_state.asked)
        st.session_state.questions = qs
        st.session_state.asked += [q["question"] for q in qs]

    if err := st.session_state.get("last_error"):
        st.warning(f"{err} Please try again.")

    for q in st.session_state.questions:
        with st.container(border=True):
            st.markdown(q["question"])
            st.caption(f"About {q['note_id']} · {q['angle']}")
