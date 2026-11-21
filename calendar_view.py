"""PERSON C owns this file: the small month calendar.

Green = day has an entry, red = no entry. Clicking a day sets st.session_state.selected_day.
(Named calendar_view.py, not calendar.py, so it doesn't shadow Python's built-in calendar module.)
"""
import calendar
from datetime import date

import streamlit as st

import entries


def _shift_month(d: date, step: int) -> date:
    m = d.month - 1 + step
    return date(d.year + m // 12, m % 12 + 1, 1)


def render_calendar() -> None:
    selected: date = st.session_state.selected_day
    month: date = st.session_state.setdefault("cal_month", selected.replace(day=1))
    filled = entries.days_with_entries()
    today = date.today()

    prev, title, nxt = st.columns([1, 4, 1])
    if prev.button("‹", key="cal_prev", type="tertiary"):
        st.session_state.cal_month = _shift_month(month, -1)
        st.rerun()
    title.markdown(f"<div style='text-align:center'><b>{month:%B %Y}</b></div>", unsafe_allow_html=True)
    if nxt.button("›", key="cal_next", type="tertiary"):
        st.session_state.cal_month = _shift_month(month, 1)
        st.rerun()

    for col, name in zip(st.columns(7), "MTWTFSS"):
        col.caption(name)

    for week in calendar.Calendar().monthdatescalendar(month.year, month.month):
        for col, d in zip(st.columns(7), week):
            if d.month != month.month:
                continue
            color = "green" if d.isoformat() in filled else ("red" if d <= today else "gray")
            label = f":{color}-background[{d.day}]"
            if d == selected:
                label = f"**{label}**"
            if col.button(label, key=f"cal_{d}", type="tertiary"):
                st.session_state.selected_day = d
                st.rerun()
