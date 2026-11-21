"""PERSON C owns this file: the In2Words wordmark (used by app.py and the password screen in auth.py).

Font: Sora (headingFont in .streamlit/config.toml loads it). The "2" uses a blue-to-purple gradient
in the app's own primary and appointment colors.
"""
import streamlit as st

NAME = "In2Words"

_WORDMARK = """
<div style="font-family: 'Sora', sans-serif; font-weight: 700; font-size: 2.9rem;
            letter-spacing: -0.045em; line-height: 1.05; color: #1F3245; margin: 0.2rem 0 0.1rem 0;">
  In<span style="background: linear-gradient(135deg, #3A6D9A 0%, #6C5BBF 100%);
                 -webkit-background-clip: text; background-clip: text; color: transparent;
                 padding: 0 0.04em;">2</span>Words
</div>
"""


def wordmark() -> None:
    st.html(_WORDMARK)
