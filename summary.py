"""PERSON B owns this file: "Summarize week" with sources.

Contract (don't change without telling the team):
  render_summary() - called by app.py.
  Summary is built from her ORIGINAL text + her answers, never from the clarification sentence.
  Every sentence shows which entries it came from. Clicking a source sets
  st.session_state.selected_day (calendar jumps there) and st.session_state.highlight = {entry id}.
"""
from datetime import date, timedelta

import streamlit as st

import claude_client
import entries


def _fallback(items: list[dict]) -> dict:
    return {"sentences": [{"text": f"On {e['date']} I wrote: \"{e['text']}\"", "sources": [e["id"]]}
                          for e in items]}


def render_summary() -> None:
    end = st.session_state.selected_day
    period = st.date_input("Period", value=(end - timedelta(days=6), end), key="sum_period")
    if not isinstance(period, tuple) or len(period) != 2:
        st.caption("Pick a start and an end date.")
        return
    start, end = period

    if st.button("Summarize week", type="primary", use_container_width=True):
        items = entries.between(start, end)
        if not items:
            st.session_state.summary = {"sentences": []}
        else:
            # Only original words + answers go to Claude, never the clarification.
            payload = [{k: e[k] for k in ("id", "date", "text", "answers")} for e in items]
            with st.spinner("Summarizing..."):
                st.session_state.summary = claude_client.summarize(payload) or _fallback(items)

    summary = st.session_state.get("summary")
    if summary is None:
        return
    if not summary["sentences"]:
        st.info("No entries in this period.")
        return

    # Running text with numbered source markers.
    numbered = {}
    parts = []
    for s in summary["sentences"]:
        marks = []
        for src in s["sources"]:
            numbered.setdefault(src, len(numbered) + 1)
            marks.append(f":blue-background[{src}]")
        parts.append(f"{s['text']} {' '.join(marks)}")
    st.markdown(" ".join(parts))

    st.caption("Sources: click to open the entry")
    cols = st.columns(max(len(numbered), 1))
    for col, src in zip(cols, numbered):
        e = entries.by_id(src)
        if e and col.button(f"{src} · {e['date'][5:]}", key=f"src_{src}"):
            st.session_state.selected_day = date.fromisoformat(e["date"])
            st.session_state.cal_month = st.session_state.selected_day.replace(day=1)
            st.session_state.highlight = {src}
            st.rerun()
