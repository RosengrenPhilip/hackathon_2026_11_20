"""PERSON C owns this file: page layout + day view. Other people's features plug in via one call each."""
from datetime import date

import streamlit as st

import calendar_view
import entries
import questionnaire
import summary
import vagueness
from auth import require_password

st.set_page_config(page_title="Inwords", page_icon=":material/spa:", layout="wide")
require_password()

entries.init()
st.session_state.setdefault("selected_day", date.today())
st.session_state.setdefault("highlight", set())  # entry IDs to highlight (summary sources)
st.session_state.setdefault("entry_box", 0)  # bump to clear the text box after saving

# ---------------- Layout: main area (left) + calendar column (right) ----------------
head, cal = st.columns([3, 1.2], gap="large")
VIEWS = {"journal": ":material/edit_note: Journal", "summary": ":material/summarize: My summary"}

with head:
    st.title("Inwords", anchor=False)
    st.caption("Others summarize what patients say. We help patients say it.")
    view = st.segmented_control(
        "View", list(VIEWS), format_func=VIEWS.get, key="view",
        default="journal", required=True, label_visibility="collapsed",
    )
    if err := st.session_state.pop("last_error", None):
        st.warning(err)
with cal:
    calendar_view.render_calendar()


def _set_editing(day_iso: str | None) -> None:
    st.session_state.editing = day_iso


def _close_questions() -> None:
    st.session_state.questions_open = False
    questionnaire.on_dismiss()


def _open_questions_for(entry_id: str) -> None:
    """From edit mode: keep any text she already changed, then open the wizard for that entry."""
    new_text = st.session_state.get(f"edit_text_{entry_id}")
    if new_text:
        entries.update_entry(entry_id, new_text)
    questionnaire.start_edit(entries.by_id(entry_id))
    st.session_state.questions_open = True


def _reopen_pending() -> None:
    questionnaire.resume_pending()
    st.session_state.questions_open = True


@st.dialog("Let's put it into words", width="medium", icon=":material/psychology:", on_dismiss=_close_questions)
def questions_dialog() -> None:
    """Popup with the 3-step wizard (questionnaire.py). Its last tap saves and closes the popup."""
    questionnaire.render()


def render_day_box(day: date, day_entries: list[dict]) -> None:
    """All of a day's entries in ONE box, each followed by its "In other words" line.
    One Edit button for the whole day; edit mode shows a text box per entry and one Save."""
    day_iso = day.isoformat()
    with st.container(border=True):
        if st.session_state.get("editing") == day_iso:
            new_texts = {}
            for e in day_entries:
                new_texts[e["id"]] = st.text_area(
                    "Edit entry", e["text"], key=f"edit_text_{e['id']}", label_visibility="collapsed"
                )
                with st.container(horizontal=True, vertical_alignment="center"):
                    if e["clarification"]:
                        st.caption(f"↳ In other words: {e['clarification']}", width="stretch")
                    st.button(
                        "Change answers" if e.get("answers") else "Help me put it into words",
                        key=f"edit_questions_{e['id']}", type="tertiary", icon=":material/quiz:",
                        on_click=_open_questions_for, args=(e["id"],),
                    )
            with st.container(horizontal=True):
                if st.button("Save changes", key=f"edit_save_{day_iso}", type="primary",
                             icon=":material/check:"):
                    for entry_id, text in new_texts.items():
                        entries.update_entry(entry_id, text)  # empty text is ignored
                    _set_editing(None)
                    st.toast("Entry updated")
                    st.rerun()
                st.button("Cancel", key=f"edit_cancel_{day_iso}", type="tertiary",
                          on_click=_set_editing, args=(None,))
            return

        for e in day_entries:
            text = e["text"]
            if e["id"] in st.session_state.highlight:
                text = f":blue-background[{e['id']}] {text}"
            st.markdown(text)
            if e["clarification"]:
                st.caption(f"↳ In other words: {e['clarification']}")
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button("Edit", key=f"edit_{day_iso}", type="tertiary", icon=":material/edit:",
                      on_click=_set_editing, args=(day_iso,))


def render_day(compact: bool) -> None:
    """The selected day: its entries, then the writing box (big in journal view, smaller next to the summary)."""
    day: date = st.session_state.selected_day
    is_today = day == date.today()
    st.subheader("Today" if is_today else f"{day:%A %d %B}", anchor=False)
    if is_today:
        st.caption(f"{day:%A %d %B}")

    day_entries = entries.for_day(day)
    if day_entries:
        render_day_box(day, day_entries)

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
            # Vague entry -> person A stored it as pending; open the 3-step wizard popup.
            if st.session_state.get("pending"):
                questionnaire.reset()
                st.session_state.questions_open = True
            st.rerun()
    else:
        # Popup was closed without answering: keep the entry safe and let her reopen it.
        with st.container(border=True):
            st.markdown(f"Your entry from **{pending['day']:%A %d %B}** isn't saved yet.")
            st.caption(pending["text"])
            st.button("Answer a few questions", type="primary", icon=":material/quiz:",
                      key="reopen_questions", on_click=_reopen_pending)


def maybe_open_questions() -> None:
    """Call once per run (only one dialog may be open at a time)."""
    if st.session_state.get("questions_open") and questionnaire.is_active():
        questions_dialog()


if view == "summary":
    # Summary takes the main area; the selected day sits under the calendar so clicking a source shows it.
    with head:
        st.subheader("My summary", anchor=False)
        summary.render_summary()
    with cal:
        st.divider()
        render_day(compact=True)
else:
    # Journal: the writing box is the main thing on the page, right under the title.
    with head:
        render_day(compact=False)

maybe_open_questions()
