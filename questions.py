"""PERSON A owns this file: question cards with Answer / Skip -> brief lines.

Contract (don't change without telling the team):
  render_questions()  - called by app.py under the Reflect button.
  Each item in st.session_state.questions:
      {"question", "note_id", "angle", "status": "open"|"answered"|"skipped", "answer"}
  Each brief line appended to st.session_state.brief:
      {"id": "L1", "text", "sources": ["E2"], "section", "status": "draft"|"approved"}
"""
import streamlit as st

import claude_client
import wordfinder

VAGUE = ("idk", "i don't know", "dunno", "just off", "not sure", "whatever")


def is_vague(answer: str) -> bool:
    a = answer.lower().strip()
    return len(a.split()) < 4 or any(v in a for v in VAGUE)


def add_brief_line(line: dict) -> None:
    """Shared helper (wordfinder.py uses it too)."""
    brief = st.session_state.brief
    brief.append({"id": f"L{len(brief) + 1}", "status": "draft", **line})


def render_questions() -> None:
    for i, q in enumerate(st.session_state.questions):
        q.setdefault("status", "open")
        with st.container(border=True):
            st.markdown(q["question"])
            st.caption(f"About {q['note_id']} · {q['angle']}")

            if q["status"] == "skipped":
                st.caption("Skipped")
                continue
            if q["status"] == "answered":
                st.caption(f"You said: {q['answer']}")
                if is_vague(q["answer"]):
                    wordfinder.render_wordfinder(f"q{i}", q["answer"], q["note_id"])
                continue

            answer = st.text_area("Your answer", key=f"ans_{i}", label_visibility="collapsed")
            c1, c2 = st.columns(2)
            if c1.button("Answer", key=f"answer_{i}"):
                if not answer.strip():
                    st.warning("Write something first, or Skip.")
                    continue
                with st.spinner("Writing your brief line..."):
                    line = claude_client.answer_to_brief_line(
                        q["question"], answer, q["note_id"], st.session_state.notes
                    )
                if line:
                    add_brief_line(line)
                q.update(status="answered", answer=answer)
                st.rerun()
            if c2.button("Skip", key=f"skip_{i}"):
                q["status"] = "skipped"
                st.rerun()
