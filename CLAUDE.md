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

## Claude API
- anthropic Python SDK, model "claude-sonnet-5-5". Key from st.secrets["ANTHROPIC_API_KEY"] (.streamlit/secrets.toml, gitignored; see secrets.toml.example).
- Optional APP_PASSWORD secret gates the whole app (auth.py) so a public link can't spend credits. Unset = no gate.
- Call Claude only on button clicks or saves, never per keystroke. Show st.spinner while waiting.
- All calls go through claude_client.py (`_call_json` helper: structured JSON output + safe fallback, errors go to st.session_state["last_error"]).
- Prompts live in prompts/*.txt, not in code. Few-shot style examples: data/examples.json (Counsel Chat, regenerate with `uv run python scripts/build_examples.py`).

## Structure
app.py            # layout, state, wiring (DONE - shared, don't edit without asking the team)
auth.py           # password gate (DONE)
claude_client.py  # all Claude calls; one section per person (see below)
questions.py      # A: question cards, Answer/Skip -> brief line
wordfinder.py     # B: "Help me find the words"
brief.py          # A: brief panel, approve/edit/remove, receipts
prompts/          # questions.txt (done), brief_line.txt (A), wordfinder.txt (B)
data/             # sara.json (demo notes, preloaded), feelings.txt, examples.json

## Team ownership (IMPORTANT for Claude Code)
Three people work in parallel on separate branches. Before editing, ask the user which person they are if it isn't clear.
| Person | Branch | May edit |
|---|---|---|
| A | feature/questions | questions.py, brief.py, prompts/brief_line.txt, "PERSON A" section of claude_client.py |
| B | feature/wordfinder | wordfinder.py, prompts/wordfinder.txt, "PERSON B" section of claude_client.py |
| C | (no code) | Pitch, demo script, testing the live app. Doesn't edit code. |
No safety/crisis feature: it was deliberately dropped. Don't add one.
Rules:
- NEVER edit another person's files or claude_client.py sections. If a change is needed there, tell the user what to ask the owner for.
- Don't edit app.py or auth.py. The wiring is done; each module's docstring describes its contract (function signature + session_state format). Don't change a contract without the team agreeing.
- Brief lines (brief.py, owned by A): approve / edit / remove, click = highlight sources.
- Data shared via st.session_state: notes, questions, asked, brief, highlight, last_error. Formats are in the module docstrings.
- Work only on your own branch; merge to main via Pull Request. main is what Streamlit Cloud deploys, so it must always run.
- Guardrail: copy .claude/team/person-X.json to .claude/settings.local.json; it denies edits to other people's files.

## Constraints
- Python + uv. Run: `uv run streamlit run app.py`. `datasets` is a dev-only dependency.
- Deploy on Streamlit Community Cloud with app.py in root. requirements.txt is generated: `uv export --no-dev --no-hashes -o requirements.txt` (re-run after `uv add`).
- Keep it simple and demo-stable. Preload Sara's notes so the demo works with one click.
- Commit small and often.
