"""PERSON C owns this file: the small month calendar.

Green = day has an entry, gray = no entry, purple = psychiatrist appointment.
The selected day has a blue ring; today is underlined.
Clicking a past day (or today) sets st.session_state.selected_day; future days are locked.
(Named calendar_view.py, not calendar.py, so it doesn't shadow Python's built-in calendar module.)
"""
import calendar
import json
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

import entries

APPOINTMENTS_FILE = Path(__file__).parent / "data" / "appointments.json"

ENTRY_GREEN = "#2E8B66"
APPT_PURPLE = "#6C5BBF"
EMPTY_BG, EMPTY_TEXT = "#E2E8EF", "#5B6B7B"
FUTURE_TEXT = "#A9B6C3"
SELECTED_RING = "#1F4E79"
PAGE_BG = "#F5F8FB"  # matches backgroundColor in .streamlit/config.toml

# Day cells are buttons keyed "cal-<kind>[-sel][-today]-<date>"; Streamlit adds the class
# "st-key-<key>" to each, so the colors below target them by kind.
_CSS = f"""
<style>
[class*="st-key-cal-"] {{ flex: 1 1 0 !important; min-width: 0; }}
[class*="st-key-cal-"] button {{
    min-height: 1.9rem; min-width: 0; padding: 0;
    border-radius: 8px; border: none !important; font-size: 0.85rem;
}}
[class*="st-key-cal-entry"] button {{ background: {ENTRY_GREEN} !important; color: #fff !important; }}
[class*="st-key-cal-appt"] button {{ background: {APPT_PURPLE} !important; color: #fff !important; }}
[class*="st-key-cal-empty"] button {{ background: {EMPTY_BG} !important; color: {EMPTY_TEXT} !important; }}
[class*="st-key-cal-future"] button {{ background: transparent !important; color: {FUTURE_TEXT} !important; }}
[class*="st-key-cal-blank"] {{ visibility: hidden; }}
[class*="st-key-cal-"]:not([class*="-future"]) button:hover {{ filter: brightness(1.08); }}
[class*="st-key-cal-"][class*="-sel-"] button {{
    box-shadow: 0 0 0 2px {PAGE_BG}, 0 0 0 4px {SELECTED_RING};
    font-weight: 700;
}}
[class*="st-key-cal-"][class*="-today-"] button p {{
    font-weight: 700; text-decoration: underline; text-underline-offset: 3px;
}}
</style>
"""


def appointments() -> dict[date, str]:
    """{date: who} from data/appointments.json. Dates are relative to today so the demo stays current."""
    raw = json.loads(APPOINTMENTS_FILE.read_text(encoding="utf-8"))
    today = date.today()
    return {today + timedelta(days=a["days_from_now"]): a.get("with", "your psychiatrist") for a in raw}


def _shift_month(d: date, step: int) -> date:
    m = d.month - 1 + step
    return date(d.year + m // 12, m % 12 + 1, 1)


def _select(d: date) -> None:
    st.session_state.selected_day = d


def render_calendar() -> None:
    selected: date = st.session_state.selected_day
    month: date = st.session_state.setdefault("cal_month", selected.replace(day=1))
    filled = entries.days_with_entries()
    appts = appointments()
    today = date.today()

    st.html(_CSS)

    prev, title, nxt = st.columns([1, 4, 1], vertical_alignment="center")
    if prev.button(":material/chevron_left:", key="cal_prev", type="tertiary"):
        st.session_state.cal_month = _shift_month(month, -1)
        st.rerun()
    title.markdown(f"**{month:%B %Y}**", text_alignment="center")
    if nxt.button(":material/chevron_right:", key="cal_next", type="tertiary"):
        st.session_state.cal_month = _shift_month(month, 1)
        st.rerun()

    # Tight grid: small vertical gap between rows, equal-width cells (horizontal containers shrink to fit).
    with st.container(gap="xxsmall"):
        with st.container(horizontal=True, gap="xxsmall"):
            for name in "MTWTFSS":
                st.caption(name, text_alignment="center", width="stretch")

        for week in calendar.Calendar().monthdatescalendar(month.year, month.month):
            with st.container(horizontal=True, gap="xxsmall"):
                for d in week:
                    if d.month != month.month:
                        st.button(" ", key=f"cal-blank-{d}", disabled=True, width="stretch")
                        continue
                    if d in appts:
                        kind, tip = "appt", f"Appointment with {appts[d]}"
                    elif d > today:
                        kind, tip = "future", None
                    elif d.isoformat() in filled:
                        kind, tip = "entry", "You wrote this day"
                    else:
                        kind, tip = "empty", "No entry"
                    flags = ("-sel" if d == selected else "") + ("-today" if d == today else "")
                    st.button(
                        str(d.day), key=f"cal-{kind}{flags}-{d}", help=tip,
                        on_click=_select, args=(d,), disabled=d > today, width="stretch",
                    )

    # Legend + next appointment use the exact calendar colors above (theme colors differ slightly).
    def swatch(bg: str, label: str, outline: str = "transparent") -> str:
        return (f"<span style='display:inline-flex;align-items:center;gap:6px;margin-right:14px'>"
                f"<span style='width:14px;height:14px;border-radius:4px;background:{bg};"
                f"box-shadow:inset 0 0 0 1px {outline}'></span>{label}</span>")

    legend = swatch(ENTRY_GREEN, "Entry") + swatch(EMPTY_BG, "No entry", outline="#B8C4D0") + swatch(APPT_PURPLE, "Appointment")
    html = f"<div style='font-size:0.85rem;color:{EMPTY_TEXT};margin-top:4px'>{legend}</div>"

    upcoming = sorted(d for d in appts if d >= today)
    if upcoming:
        nxt_day = upcoming[0]
        days_left = (nxt_day - today).days
        when = "today" if days_left == 0 else "tomorrow" if days_left == 1 else f"in {days_left} days"
        html += (
            f"<div style='margin-top:12px;padding:10px 14px;border-radius:12px;"
            f"background:{APPT_PURPLE};color:#fff;font-size:0.9rem;line-height:1.35'>"
            f"<div style='opacity:0.85;font-size:0.78rem'>Next appointment · {when}</div>"
            f"<div style='font-weight:600'>{nxt_day:%A} {nxt_day.day} {nxt_day:%B}</div>"
            f"<div style='opacity:0.9;font-size:0.8rem'>{appts[nxt_day]}</div></div>"
        )
    st.html(html)
