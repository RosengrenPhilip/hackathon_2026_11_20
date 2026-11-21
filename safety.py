"""PERSON C owns this file: crisis check + banner.

Contract (don't change without telling the team):
  check_text(text, source) -> bool  - called on every new note (app.py) and answer (questions.py).
                                      Sets st.session_state.crisis = {"source", "reason"} when triggered.
  render_banner()                   - called at the top of app.py, every run.
Not therapy. Never diagnose.
"""
import streamlit as st

import claude_client

# Fallback if the Claude check fails: better a false alarm than a miss.
KEYWORDS = ("kill myself", "suicide", "end it all", "self-harm", "hurt myself", "no point living",
            "want to die", "better off without me", "skada mig", "ta livet av mig")


def check_text(text: str, source: str) -> bool:
    result = claude_client.crisis_check(text)
    if result is None:
        hit = any(k in text.lower() for k in KEYWORDS)
        result = {"crisis": hit, "reason": "keyword match" if hit else ""}
    if result["crisis"]:
        st.session_state.crisis = {"source": source, "reason": result["reason"]}
    return result["crisis"]


def render_banner() -> None:
    if crisis := st.session_state.get("crisis"):
        st.error(
            "**You don't have to handle this alone.** If you are thinking about hurting yourself, "
            "call **112** (emergency) or **1177** (healthcare advice, 24/7). "
            f"This has been flagged for your clinician. _(from {crisis['source']})_",
            icon="🆘",
        )
