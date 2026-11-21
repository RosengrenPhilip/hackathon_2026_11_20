# Project: Pre-visit companion (hackathon, deadline 17:30)

## What it is
A Streamlit web app that helps psychiatry patients put their feelings into words before a visit. Pitch: "Others summarize what patients say. We help patients say it."
Demo user: Sara, 24, first psychiatry visit, struggles to explain how she feels.

## The app (two columns)
- LEFT, Notes: an editable list of journal entries (date + text, "Add note" button). Store in st.session_state so edits persist while the app runs. Each entry has an ID (E1, E2...).
- RIGHT, Brief: a one-page visit brief that grows as she answers questions. Written in first person, in her voice. The first section is always "What I want from today"; other sections appear only if her notes support them.

## Flow
1. User clicks "Reflect on my week". Claude reads ALL current notes and returns 3 personal questions as JSON. Each question must refer to a specific note. Send previously asked questions so they never repeat. Vary the angle (body, situations, people, changes, goals).
2. Each question has Answer / Skip. When she answers, Claude turns the answer into one brief line with source IDs (e.g. ["E2"]). She can approve, edit or remove each line.
3. Word finder: if an answer is vague ("idk, just off"), show "Help me find the words": 6 feeling words (from data/feelings.txt, the Feelings Wheel), body area and duration chips (st.pills). Claude then writes one rephrasing ONLY from what she picked; she accepts, edits or rejects. Never add symptoms she didn't pick or write.
4. Receipts: clicking a brief line highlights its source notes on the left. A line with no source is flagged red.
5. Safety: on every new note or answer, run a crisis check (self-harm, hopelessness, plans). If triggered, show a banner with 1177 and 112 right away, and flag the line for the clinician. This is not therapy and never diagnoses.

## Claude API
- anthropic Python SDK, model "claude-sonnet-5-5". Key from st.secrets["ANTHROPIC_API_KEY"] (.streamlit/secrets.toml, gitignored; see secrets.toml.example).
- Call Claude only on button clicks or saves, never per keystroke. Show st.spinner while waiting.
- All calls go through claude_client.py (`_call_json` helper: structured JSON output + safe fallback, errors go to st.session_state["last_error"]).
- Prompts live in prompts/*.txt, not in code. Few-shot style examples: data/examples.json (Counsel Chat, regenerate with `uv run python scripts/build_examples.py`).

## Structure
app.py            # layout, state, wiring
claude_client.py  # get_questions, answer_to_brief_line, wordfinder_options, rephrase, crisis_check
questions.py      # question cards UI
wordfinder.py     # word finder UI
safety.py         # crisis banner
prompts/          # questions.txt, brief_line.txt, wordfinder.txt, safety.txt
data/             # sara.json (demo notes, preloaded), feelings.txt, examples.json

## Constraints
- Python + uv. Run: `uv run streamlit run app.py`. `datasets` is a dev-only dependency.
- Deploy on Streamlit Community Cloud with app.py in root. requirements.txt is generated: `uv export --no-dev --no-hashes -o requirements.txt` (re-run after `uv add`).
- Keep it simple and demo-stable. Preload Sara's notes so the demo works with one click.
- Commit small and often.
