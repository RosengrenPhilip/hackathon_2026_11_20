"""PERSON C owns this file: page layout + day view. Other people's features plug in via one call each."""
import html
from datetime import date

import streamlit as st

import brand
import calendar_view
import entries
import questionnaire
import summary
import vagueness
from auth import require_password

# ---------------- Clickable summary text (GUI layer on top of summary.py) ----------------
# summary.py writes the running summary text with one st.markdown call, then a row of source buttons.
# We hand summary.py a thin wrapper around `st` that:
#   - swaps that paragraph for a component where hovering a sentence shows the entries it came from
#     and clicking it opens that day (selected_day + highlight, same as the old source buttons),
#   - drops the "Sources" caption and button row, since the text itself is now the link.
# Everything else passes straight through to Streamlit.
_SUMMARY_CSS = """
.i2w-card { position: relative; margin: 0.25rem 0 1rem; padding: 26px 30px 20px; border-radius: 18px;
            background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFE 100%);
            border: 1px solid #D5E0EA; box-shadow: 0 10px 30px rgba(31, 50, 69, .08);
            color: var(--st-text-color, #1F3245); font-family: var(--st-font); }
.i2w-bar { position: absolute; top: -1px; left: -1px; right: -1px; height: 6px;
           border-radius: 18px 18px 0 0; background: linear-gradient(90deg, #3A6D9A 0%, #6C5BBF 100%); }
.i2w-eyebrow { font-size: .72rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
               background: linear-gradient(90deg, #3A6D9A, #6C5BBF); -webkit-background-clip: text;
               background-clip: text; color: transparent; }
.i2w-title { margin: 4px 0 2px; font-family: 'Sora', sans-serif; font-weight: 600; font-size: 1.35rem;
             letter-spacing: -0.02em; color: #1F3245; }
.i2w-meta { font-size: .82rem; color: #6B7C8D; }
.i2w-summary { margin: 18px 0 18px; padding-top: 18px; border-top: 1px solid #E8EFF6;
               font-size: 1.08rem; line-height: 1.85; }
.i2w-sent { position: relative; cursor: default; border-radius: 6px; padding: 2px 3px;
            transition: background .15s, box-shadow .15s; }
.i2w-sent:hover { background: #EEF2FB; box-shadow: inset 0 -2px 0 #B9C4EA; }
.i2w-tip { visibility: hidden; opacity: 0; position: absolute; left: 0; top: 1.9em; z-index: 1000;
           width: min(340px, 80vw); padding: 10px 12px; border-radius: 12px; background: #fff;
           border: 1px solid #D5E0EA; box-shadow: 0 8px 24px rgba(31, 50, 69, .15);
           font-size: .85rem; line-height: 1.45; transition: opacity .15s; pointer-events: none; }
.i2w-sent:hover .i2w-tip { visibility: visible; opacity: 1; }
.i2w-src { display: block; }
.i2w-src + .i2w-src { margin-top: 8px; padding-top: 8px; border-top: 1px solid #E8EFF6; }
.i2w-tip b { color: var(--st-primary-color, #3A6D9A); font-weight: 600; }
.i2w-foot { display: flex; gap: 8px; align-items: center; font-size: .78rem; color: #6B7C8D; }
.i2w-dot { width: 6px; height: 6px; border-radius: 50%; flex: none;
           background: linear-gradient(135deg, #3A6D9A, #6C5BBF); }
"""

_SUMMARY_JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;
    let root = parentElement.querySelector('.i2w-root');
    if (!root) {
        root = document.createElement('div');
        root.className = 'i2w-root';
        parentElement.appendChild(root);
    }
    root.innerHTML = data;
    root.querySelectorAll('.i2w-sent').forEach((el) => {
        el.onclick = () => setTriggerValue('clicked', el.dataset.idx);
    });
}
"""


@st.cache_resource
def _register_summary_component(css: str, js: str):
    """Register once per server (re-registering every rerun logs warnings). css/js are the cache key,
    so editing _SUMMARY_CSS/_SUMMARY_JS re-registers it without restarting Streamlit."""
    return st.components.v2.component("i2w_summary_text", css=css, js=js)


def _summary_component():
    return _register_summary_component(_SUMMARY_CSS, _SUMMARY_JS)


def _open_sources(sources: list[str]) -> None:
    """Same effect as summary.py's source buttons: jump to the (first) source day and highlight."""
    found = [e for e in (entries.by_id(src) for src in sources) if e]
    if not found:
        return
    st.session_state.selected_day = date.fromisoformat(found[0]["date"])
    st.session_state.cal_month = st.session_state.selected_day.replace(day=1)
    st.session_state.highlight = {e["id"] for e in found}
    st.rerun()


def _summary_card(sentences: list[dict], body_html: str) -> str:
    """The highlighted summary card: period title, what it's based on, the text, a short footer."""
    ids = {src for s in sentences for src in s.get("sources", [])}
    found = [e for e in (entries.by_id(i) for i in ids) if e]
    days = {e["date"] for e in found}
    period = st.session_state.get("sum_period")
    if isinstance(period, tuple) and len(period) == 2:
        start, end = period
        title = (f"{start:%d} – {end:%d %B}" if (start.year, start.month) == (end.year, end.month)
                 else f"{start:%d %B} – {end:%d %B}")
    else:
        title = "Your summary"
    n_e, n_d = len(found), len(days)
    meta = (f"Based on {n_e} {'entry' if n_e == 1 else 'entries'} over {n_d} {'day' if n_d == 1 else 'days'}"
            " · hover a sentence to see where it came from, click to open that day")
    return (
        "<div class='i2w-card'><div class='i2w-bar'></div>"
        "<div class='i2w-eyebrow'>In your own words</div>"
        f"<div class='i2w-title'>{html.escape(title)}</div>"
        f"<div class='i2w-meta'>{html.escape(meta)}</div>"
        f"<div class='i2w-summary'>{body_html}</div>"
        "<div class='i2w-foot'><span class='i2w-dot'></span>"
        "Built only from what you wrote and the words you picked. Not a diagnosis.</div>"
        "</div>"
    )


def _render_clickable_summary(body: str) -> bool:
    """Render the clickable version if `body` is the summary paragraph. Returns False otherwise."""
    sentences = (st.session_state.get("summary") or {}).get("sentences") or []
    if not sentences or not all(s.get("text", "") in body for s in sentences):
        return False
    parts = []
    for i, s in enumerate(sentences):
        tips = []
        for src in s.get("sources", []):
            e = entries.by_id(src)
            if e:
                day = date.fromisoformat(e["date"])
                tips.append(f"<span class='i2w-src'><b>{day:%A %d %B}</b><br>“{html.escape(e['text'])}”</span>")
        tip = f"<span class='i2w-tip'>{''.join(tips)}</span>" if tips else ""
        parts.append(f"<span class='i2w-sent' data-idx='{i}'>{html.escape(s['text'])}{tip}</span>")
    result = _summary_component()(
        data=_summary_card(sentences, " ".join(parts)),
        key="summary_text", on_clicked_change=lambda: None,
    )
    st.session_state["_summary_is_clickable"] = True
    clicked = getattr(result, "clicked", None)
    if clicked is not None and str(clicked).isdigit() and int(clicked) < len(sentences):
        _open_sources(sentences[int(clicked)].get("sources", []))
    return True


class _Nothing:
    """Swallows summary.py's source-button row: every call does nothing and returns None (falsy)."""

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class _SummarySt:
    """Stateless stand-in for `st` inside summary.py (state lives in st.session_state, per session)."""

    def __getattr__(self, name):
        return getattr(st, name)

    def markdown(self, body, *args, **kwargs):
        if isinstance(body, str) and _render_clickable_summary(body):
            return None
        return st.markdown(body, *args, **kwargs)

    def caption(self, body, *args, **kwargs):
        if st.session_state.get("_summary_is_clickable") and str(body).startswith("Sources"):
            return None
        return st.caption(body, *args, **kwargs)

    def columns(self, spec, *args, **kwargs):
        if st.session_state.get("_summary_is_clickable"):
            return [_Nothing() for _ in range(spec if isinstance(spec, int) else len(spec))]
        return st.columns(spec, *args, **kwargs)


summary.st = _SummarySt()

st.set_page_config(page_title="In2Words", page_icon=":material/spa:", layout="wide")
require_password()

entries.init()
st.session_state.setdefault("selected_day", date.today())
st.session_state.setdefault("highlight", set())  # entry IDs to highlight (summary sources)
st.session_state.setdefault("entry_box", 0)  # bump to clear the text box after saving

# ---------------- Layout: main area (left) + calendar column (right) ----------------
head, cal = st.columns([3, 1.2], gap="large")
VIEWS = {"journal": ":material/edit_note: Journal", "summary": ":material/summarize: My summary"}

with head:
    brand.wordmark()
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
        st.session_state["_summary_is_clickable"] = False
        summary.render_summary()
    with cal:
        st.divider()
        render_day(compact=True)
else:
    # Journal: the writing box is the main thing on the page, right under the title.
    with head:
        render_day(compact=False)

maybe_open_questions()
