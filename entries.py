"""PERSON C owns this file: journal entries in st.session_state.

Contract (don't change without telling the team):
  An entry is {"id": "E3", "date": "YYYY-MM-DD", "text": her original words,
               "answers": {"feelings": [...], "body": [...], "duration": str|None} or None,
               "clarification": one sentence or None}
  Several entries on the same date = that day's entry (they're shown together, in order).
  update_entry(entry_id, text) - she edited her words; answers/clarification are kept.
  set_answers(entry_id, answers, clarification) - she re-did the questionnaire for a saved entry.
"""
import json
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

DATA = Path(__file__).parent / "data"


def init() -> None:
    """Load Sara's demo entries once. Dates are relative to today so the demo always looks current."""
    if "entries" in st.session_state:
        return
    raw = json.loads((DATA / "sara.json").read_text(encoding="utf-8"))
    today = date.today()
    st.session_state.entries = [
        {
            "id": e["id"],
            "date": (today - timedelta(days=e["days_ago"])).isoformat(),
            "text": e["text"],
            "answers": e.get("answers"),
            "clarification": e.get("clarification"),
        }
        for e in raw
    ]


def add_entry(day: date, text: str, answers: dict | None = None, clarification: str | None = None) -> str:
    entries = st.session_state.entries
    nums = [int(e["id"][1:]) for e in entries if e["id"][1:].isdigit()]
    entry_id = f"E{max(nums, default=0) + 1}"
    entries.append({
        "id": entry_id, "date": day.isoformat(), "text": text.strip(),
        "answers": answers, "clarification": clarification,
    })
    return entry_id


def update_entry(entry_id: str, text: str) -> None:
    entry = by_id(entry_id)
    if entry is not None and text.strip():
        entry["text"] = text.strip()


def set_answers(entry_id: str, answers: dict | None, clarification: str | None) -> None:
    entry = by_id(entry_id)
    if entry is not None:
        entry["answers"] = answers
        entry["clarification"] = clarification


def for_day(day: date) -> list[dict]:
    return [e for e in st.session_state.entries if e["date"] == day.isoformat()]


def between(start: date, end: date) -> list[dict]:
    """Entries from start to end (inclusive), oldest first."""
    s, t = start.isoformat(), end.isoformat()
    return sorted((e for e in st.session_state.entries if s <= e["date"] <= t), key=lambda e: e["date"])


def by_id(entry_id: str) -> dict | None:
    return next((e for e in st.session_state.entries if e["id"] == entry_id), None)


def days_with_entries() -> set[str]:
    return {e["date"] for e in st.session_state.entries}
