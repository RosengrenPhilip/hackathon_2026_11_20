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

# ---------------- Layout: main area (left) + calendar column (right) ----------------
head, cal = st.columns([3, 1.2], gap="large")
VIEWS = {"journal": ":material/edit_note: Journal", "summary": ":material/summarize: My summary"}

with head:
    st.title("Pre-visit companion")
    st.caption("Others summarize what patients say. We help patients say it.")
    view = st.segmented_control(
        "View", list(VIEWS), format_func=VIEWS.get, key="view",
        default="journal", required=True, label_visibility="collapsed",
    )
    if err := st.session_state.pop("last_error", None):
        st.warning(err)
with cal:
    calendar_view.render_calendar()


def _set_editing(entry_id: str | None) -> None:
    st.session_state.editing = entry_id


def _close_questions() -> None:
    st.session_state.questions_open = False


@st.dialog("Let's put it into words", width="medium", icon=":material/psychology:", on_dismiss=_close_questions)
def questions_dialog() -> None:
    """Popup around person A's questionnaire (vagueness.render_pending). Their buttons save and close it."""
    # Open both question groups straight away so it reads as one short questionnaire.
    st.session_state.setdefault("wf_words", True)
    st.session_state.setdefault("wf_body", True)
    vagueness.render_pending(st.session_state.pending["day"])


def render_entry(e: dict) -> None:
    """One saved entry: read mode with an Edit button, or edit mode with Save/Cancel."""
    with st.container(border=True):
        if st.session_state.get("editing") == e["id"]:
            new_text = st.text_area(
                "Edit entry", e["text"], key=f"edit_text_{e['id']}", label_visibility="collapsed"
            )
            with st.container(horizontal=True):
                if st.button("Save changes", key=f"edit_save_{e['id']}", type="primary",
                             icon=":material/check:", disabled=not new_text.strip()):
                    entries.update_entry(e["id"], new_text)
                    _set_editing(None)
                    st.toast("Entry updated")
                    st.rerun()
                st.button("Cancel", key=f"edit_cancel_{e['id']}", type="tertiary",
                          on_click=_set_editing, args=(None,))
            return

        text = e["text"]
        if e["id"] in st.session_state.highlight:
            text = f":blue-background[{e['id']}] {text}"
        st.markdown(text)
        if e["clarification"]:
            st.caption(f"↳ In other words: {e['clarification']}")
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button("Edit", key=f"edit_{e['id']}", type="tertiary", icon=":material/edit:",
                      on_click=_set_editing, args=(e["id"],))


def render_day(compact: bool) -> None:
    """The selected day: its entries, then the writing box (big in journal view, smaller next to the summary)."""
    day: date = st.session_state.selected_day
    is_today = day == date.today()
    st.subheader("Today" if is_today else f"{day:%A %d %B}")
    if is_today:
        st.caption(f"{day:%A %d %B}")

    for e in entries.for_day(day):
        render_entry(e)

    pending = st.session_state.get("pending")
    if not pending:
        box_key = f"new_entry_{st.session_state.entry_box}"
        label = "Add to this day's entry" if entries.for_day(day) else "How was your day?"
        text = st.text_area(
            label, key=box_key, height=120 if compact else 240,
            placeholder="Write anything, even if it's vague.",
        )
        if st.button("Save entry", type="primary", icon=":material/check:") and text.strip():
            vagueness.handle_new_entry(day, text)
            st.session_state.entry_box += 1
            # Vague entry -> person A stored it as pending; show their questions in a popup.
            st.session_state.questions_open = bool(st.session_state.get("pending"))
            st.rerun()
    else:
        # Popup was closed without answering: keep the entry safe and let her reopen it.
        with st.container(border=True):
            st.markdown(f"Your entry from **{pending['day']:%A %d %B}** isn't saved yet.")
            st.caption(pending["text"])
            st.button("Answer a few questions", type="primary", icon=":material/quiz:",
                      key="reopen_questions", on_click=lambda: st.session_state.update(questions_open=True))


def maybe_open_questions() -> None:
    """Call once per run (only one dialog may be open at a time)."""
    if st.session_state.get("pending") and st.session_state.get("questions_open"):
        questions_dialog()


if view == "summary":
    # Summary takes the main area; the selected day sits under the calendar so clicking a source shows it.
    with head:
        st.subheader("My summary")
        summary.render_summary()
    with cal:
        st.divider()
        render_day(compact=True)
else:
    # Journal: the writing box is the main thing on the page, right under the title.
    with head:
        render_day(compact=False)

maybe_open_questions()
