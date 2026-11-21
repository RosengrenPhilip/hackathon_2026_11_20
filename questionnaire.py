"""PERSON C owns this file: the 3-step popup wizard ("What fits?" -> "Where?" -> "How long?").

Built for low energy: one question per screen, one tap answers and moves on, Back on every step,
and "Skip" only skips the current question (on the last one it finishes and saves).

Two modes:
  new entry  - a vague entry is pending (person A's contract: st.session_state.pending =
               {"day", "text", "phrases", "question", "feelings"}); finishing adds it via
               entries.add_entry(day, text, answers, clarification).
  edit entry - start_edit(entry) re-opens the wizard for a saved entry, pre-filled with its answers;
               finishing updates it via entries.set_answers(entry_id, answers, clarification).
Clarification via claude_client.clarify (fallback: vagueness._fallback_clarify). Option lists from vagueness.
State: st.session_state.wizard = {"step": 0..3, "entry_id": str|None, "feelings", "body", "duration"}
"""
import streamlit as st

import claude_client
import entries
import vagueness

STEPS = ["feelings", "body", "duration"]
DONE = len(STEPS)

# Answer pills (keys start with "wiz-pills-"): larger and softly tinted so they're easy to tap.
_CSS = """
<style>
[class*="st-key-wiz-pills-"] button {
    padding: 0.65rem 1.3rem !important;
    min-height: 2.9rem !important;
    border-radius: 999px !important;
    background: #E8EFF6 !important;
    border: 1px solid #C9D8E6 !important;
    color: #1F3245 !important;
}
[class*="st-key-wiz-pills-"] button p { font-size: 1.02rem !important; }
[class*="st-key-wiz-pills-"] button:hover { background: #DCE7F2 !important; border-color: #3A6D9A !important; }
[class*="st-key-wiz-pills-"] button[aria-checked="true"] {
    background: #3A6D9A !important; border-color: #3A6D9A !important; color: #fff !important;
}
</style>
"""


# ---------------- Starting the wizard ----------------

def reset() -> None:
    """New vague entry became pending: start a fresh wizard for it."""
    st.session_state.wizard = {"step": 0, "entry_id": None, "feelings": None, "body": None, "duration": None}


def start_edit(entry: dict) -> None:
    """Re-open the wizard for a saved entry, pre-filled with its earlier answers."""
    a = entry.get("answers") or {}
    st.session_state.wizard = {
        "step": 0,
        "entry_id": entry["id"],
        "feelings": (a.get("feelings") or [None])[0],
        "body": (a.get("body") or [None])[0],
        "duration": a.get("duration"),
    }


def is_active() -> bool:
    """Is there something for the wizard to work on (a pending entry or an entry being edited)?"""
    w = st.session_state.get("wizard") or {}
    return bool(w.get("entry_id") and entries.by_id(w["entry_id"])) or bool(st.session_state.get("pending"))


def resume_pending() -> None:
    """Reopen the wizard for the pending new entry (drops an abandoned edit, keeps progress otherwise)."""
    w = st.session_state.get("wizard")
    if not w or w.get("entry_id"):
        reset()


def on_dismiss() -> None:
    """Popup closed with X/Esc. Editing an entry: just drop it. A new entry stays pending (app shows a reopen card)."""
    if (st.session_state.get("wizard") or {}).get("entry_id"):
        st.session_state.pop("wizard", None)


# ---------------- Wizard steps ----------------

def _state() -> dict:
    if "wizard" not in st.session_state:
        reset()
    return st.session_state.wizard


def _target() -> dict | None:
    """What the wizard is about: {"text", "question", "feelings"} from the edited entry or the pending one."""
    w = _state()
    if w["entry_id"]:
        e = entries.by_id(w["entry_id"])
        if not e:
            return None
        feelings = list(vagueness.FALLBACK_FEELINGS)
        if w["feelings"] and w["feelings"] not in feelings:
            feelings.insert(0, w["feelings"])  # keep her earlier pick visible
        return {"text": e["text"], "question": "What fits best for you?", "feelings": feelings}
    return st.session_state.get("pending")


def _next(field: str, value: str | None) -> None:
    w = _state()
    w[field] = value
    w["step"] += 1


def _on_pill(step: int) -> None:
    """A pill was tapped: store it and go to the next step."""
    field = STEPS[step]
    # Tapping the already-selected pill "deselects" it (value None): treat as "yes, that one".
    _next(field, st.session_state.get(f"wiz-pills-{step}") or _state()[field])


def _skip(step: int) -> None:
    """Skip just this question: keep whatever was there (nothing, for a new entry) and move on."""
    _state()["step"] = step + 1


def _back() -> None:
    _state()["step"] -= 1


def _question(step: int, target: dict) -> tuple[str, list[str]]:
    if step == 0:
        return (target.get("question") or "What fits best for you?",
                target.get("feelings") or vagueness.FALLBACK_FEELINGS)
    if step == 1:
        return "Where do you notice it?", vagueness.BODY
    return "How long has it felt like this?", vagueness.DURATION


def _save(target: dict) -> None:
    w = _state()
    answers = {
        "feelings": [w["feelings"]] if w["feelings"] else [],
        "body": [w["body"]] if w["body"] else [],
        "duration": w["duration"],
    }
    has_answers = bool(answers["feelings"] or answers["body"] or answers["duration"])
    clarification = None
    if has_answers:
        with st.spinner("Putting it into words..."):
            clarification = claude_client.clarify(target["text"], answers) or vagueness._fallback_clarify(answers)

    if w["entry_id"]:
        entries.set_answers(w["entry_id"], answers if has_answers else None, clarification)
        st.toast("Answers updated", icon=":material/check:")
    else:
        entries.add_entry(target["day"], target["text"], answers if has_answers else None, clarification)
        st.session_state.pop("pending", None)
        st.toast("Saved", icon=":material/check:")

    st.session_state.pop("wizard", None)
    st.session_state.questions_open = False
    st.rerun()  # closes the popup


def render() -> None:
    """Draw the current wizard step. Call inside an st.dialog."""
    target = _target()
    if not target:
        return
    w = _state()
    if w["step"] >= DONE:
        _save(target)
        return

    step = w["step"]
    field = STEPS[step]
    question, options = _question(step, target)

    st.html(_CSS)
    st.progress((step + 1) / DONE, text=f"{step + 1} of {DONE}")
    st.caption(f"“{target['text']}”")
    st.subheader(question, anchor=False)
    st.caption("Just tap what feels closest. You can skip anything.")

    # Answer pills. One tap = answer + next screen. Earlier picks show as selected.
    st.pills(
        question, options, key=f"wiz-pills-{step}", default=w[field],
        on_change=_on_pill, args=(step,), label_visibility="collapsed",
    )

    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        if step > 0:
            st.button("Back", key=f"wiz-back-{step}", type="tertiary", icon=":material/arrow_back:",
                      on_click=_back)
        else:
            st.space("small")  # keeps Skip on the right on the first step
        st.button("Skip" if step < DONE - 1 else "Skip and save", key=f"wiz-skip-{step}", type="tertiary",
                  icon=":material/skip_next:", on_click=_skip, args=(step,))
