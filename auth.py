"""Simple password gate so a public link can't spend the API credits."""
import hmac

import streamlit as st

import brand


def _expected_password() -> str | None:
    try:
        return st.secrets.get("APP_PASSWORD")
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return None


def require_password() -> None:
    """Stop the app until the right password is entered. No-op if APP_PASSWORD is unset."""
    expected = _expected_password()
    if not expected or st.session_state.get("authenticated"):
        return

    brand.wordmark()
    with st.form("login"):
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Enter"):
            if hmac.compare_digest(pw, expected):
                st.session_state.authenticated = True
                st.rerun()
            st.error("Wrong password.")
    st.stop()
