"""PERSON B owns this file: "Help me find the words".

Contract (don't change without telling the team):
  render_wordfinder(key, answer, note_id) - called by questions.py inside a card when an answer is vague.
  When she accepts a rephrasing, call questions.add_brief_line(
      {"text": ..., "sources": [note_id], "section": ...})
  Rules: 6 feeling words (data/feelings.txt), body-area + duration chips (st.pills),
  Claude rephrases ONLY from what she picked. Never add symptoms.
"""
import streamlit as st


def render_wordfinder(key: str, answer: str, note_id: str) -> None:
    # TODO(B): build the real word finder here.
    st.button("Help me find the words", key=f"wf_{key}", disabled=True, help="Coming soon")
