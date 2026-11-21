"""PERSON C owns this file: page layout + day view. Other people's features plug in via one call each."""
from datetime import date

import streamlit as st

import calendar_view
import entries
import summary
import vagueness
from auth import require_password

st.set_page_config(page_title="Pre-visit companion", layout="wide")
require_password()

entries.init()
st.session_state.setdefault("selected_day", date.today())
st.session_state.setdefault("highlight", set())  # entry IDs to highlight (summary sources)
st.session_state.setdefault("entry_box", 0)  # bump to clear the text box after saving

# ---------------- Top: title + small calendar in the corner ----------------
head, cal = st.columns([3, 1.2], gap="large")
with head:
    st.title("Pre-visit companion")
    st.caption("Others summarize what patients say. We help patients say it.")
with cal:
    calendar_view.render_calendar()

if err := st.session_state.pop("last_error", None):
    st.warning(err)

day_col, sum_col = st.columns(2, gap="large")

# ---------------- Left: the selected day ----------------
with day_col:
    day: date = st.session_state.selected_day
    st.subheader(f"{day:%A %d %B}")

    for e in entries.for_day(day):
        with st.container(border=True):
            text = e["text"]
            if e["id"] in st.session_state.highlight:
                text = f":blue-background[{e['id']}] {text}"
            st.markdown(text)
            if e["clarification"]:
                st.caption(f"↳ In other words: {e['clarification']}")

    if not st.session_state.get("pending"):
        box_key = f"new_entry_{st.session_state.entry_box}"
        label = "Add to this day's entry" if entries.for_day(day) else "How was your day?"
        text = st.text_area(label, key=box_key, placeholder="Write anything, even if it's vague.")
        if st.button("Save entry", type="primary") and text.strip():
            vagueness.handle_new_entry(day, text)
            st.session_state.entry_box += 1
            st.rerun()

    vagueness.render_pending(day)

# ---------------- Right: summary ----------------
with sum_col:
    st.subheader("Summary")
    summary.render_summary()
