"""PERSON A owns this file: the visit brief panel + receipts.

Contract (don't change without telling the team):
  render_brief() - called by app.py at the top of the right column.
  Reads st.session_state.brief (line format: see questions.py).
  Receipts: set st.session_state.highlight = set of note IDs; app.py highlights those notes.
  A line with no sources is flagged red. Crisis lines are flagged for the clinician.
  "What I want from today" is always the first section.
"""
import streamlit as st

FIRST_SECTION = "What I want from today"


def render_brief() -> None:
    brief = st.session_state.brief
    sections = [FIRST_SECTION] + sorted({line["section"] for line in brief} - {FIRST_SECTION})
    with st.container(border=True):
        for section in sections:
            st.markdown(f"**{section}**")
            lines = [line for line in brief if line["section"] == section]
            if not lines:
                st.caption("Answer questions below to build your brief.")
            for line in lines:
                # TODO(C): approve / edit / remove buttons.
                text = line["text"] if line["sources"] else f":red[{line['text']} (no source)]"
                if line.get("crisis"):
                    text = f"🚩 {text}"
                if st.button(text, key=f"brief_{line['id']}", type="tertiary"):
                    st.session_state.highlight = set(line["sources"])
                    st.rerun()
