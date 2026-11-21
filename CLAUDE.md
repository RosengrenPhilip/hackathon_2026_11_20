# Project: Inwords, pre-visit journal (hackathon, deadline 17:30)

## What it is
A Streamlit journal app that helps psychiatry patients put their feelings into words before a visit.
Pitch: "Others summarize what patients say. We help patients say it."
Demo user: Sara, 24, first psychiatry visit, struggles to explain how she feels.
Main feature: detect vagueness in journal entries and gently help her be more specific.

## Flow
1. Journal entry: she writes about her day and clicks "Save entry".
   - Claude checks for vagueness ("idk, just off", "weird", "bad day").
   - Not vague: save the entry for that day. Done.
   - Vague: highlight the vague phrases. Offer (optional) "Help me find the words" (gentle "what fits best for you?" feeling-word chips from data/feelings.txt) and "Mark where in my body" (body area + duration chips). She can always "Save as is".
   - After she answers: save her ORIGINAL words + her answers + a one-sentence clarification shown underneath. The clarification uses ONLY what she picked; never add feelings or symptoms she didn't pick or write.
   - Writing again on the same day adds to that day (several entries per date, shown together).
2. Calendar: small month calendar in the top corner. Green = day has an entry, gray = no entry, purple = psychiatrist appointment (data/appointments.json). Future days are locked. Clicking a day opens that day's entries (with clarifications).
3. Summary: "Summarize week" (default the last 7 days, or a chosen period) -> short running-text summary.
   - Built from her ORIGINAL text + her answers, NOT from the clarification sentence.
   - Every sentence shows which entry IDs it came from; clicking a source opens that day and highlights the entry.
- No safety/crisis feature: it was deliberately dropped. Don't add one.
- Not therapy, never diagnoses.

## Claude API
- anthropic Python SDK, model "claude-sonnet-5-5". Key from st.secrets["ANTHROPIC_API_KEY"] (.streamlit/secrets.toml, gitignored; see secrets.toml.example).
- Optional APP_PASSWORD secret gates the whole app (auth.py). Unset = no gate.
- Call Claude only on button clicks, never per keystroke. Show st.spinner while waiting.
- All calls go through claude_client.py: use the `_call_json(system, user, schema)` helper (structured JSON output, returns None on any failure; errors go to st.session_state["last_error"]).
- Every Claude feature has a non-Claude fallback so the demo never breaks.
- Prompts live in prompts/*.txt, not in code. data/examples.json has Counsel Chat examples for a warm tone (`_examples_block()`).

## Structure
| File | Owner | What |
|---|---|---|
| app.py | C | page layout, day view, entry box; calls the other modules |
| calendar_view.py | C | small green/gray/purple month calendar |
| questionnaire.py | C | popup wizard (3 steps, one tap each, Skip per step) for new vague entries and for re-answering saved ones (Edit → Change answers); uses A's pending contract, BODY/DURATION, claude_client.clarify |
| entries.py | C | entry storage in session_state (add_entry, for_day, between, by_id) |
| auth.py | C | password gate |
| data/sara.json | C | demo entries (`days_ago` so dates stay current) |
| data/appointments.json | C | appointments (`days_from_now`) |
| .streamlit/config.toml | C | theme/colors (create if needed) |
| vagueness.py | A | handle_new_entry + render_pending: detection, highlight, chips, save |
| prompts/vagueness.txt, prompts/clarify.txt | A | prompts |
| summary.py | B | render_summary: period picker, summary text, clickable sources |
| prompts/summary.txt | B | prompt |
| claude_client.py | shared | "PERSON A" section (detect_vagueness, clarify), "PERSON B" section (summarize) |

Entry format (entries.py): {"id": "E3", "date": "YYYY-MM-DD", "text", "answers": {"feelings", "body", "duration"} | None, "clarification": str | None}
Shared session_state: entries, selected_day, cal_month, highlight, pending, summary, last_error.

## Team ownership (IMPORTANT for Claude Code)
Three people work in parallel on separate branches. If it isn't clear which person the user is, ask before editing.
| Person | Branch | May edit |
|---|---|---|
| A | feature/vagueness | vagueness.py, prompts/vagueness.txt, prompts/clarify.txt, "PERSON A" section of claude_client.py |
| B | feature/summary | summary.py, prompts/summary.txt, "PERSON B" section of claude_client.py |
| C | feature/gui | app.py, calendar_view.py, questionnaire.py, entries.py, auth.py, data/sara.json, .streamlit/config.toml |
Rules:
- NEVER edit another person's files or claude_client.py sections. If a change is needed there, tell the user what to ask the owner for.
- Each module's docstring is its contract (function signatures + session_state format). Don't change a contract without the team agreeing.
- Work only on your own branch; merge to main via Pull Request. main is what Streamlit Cloud deploys, so it must always run.
- Guardrail: copy .claude/team/person-X.json to .claude/settings.local.json; it denies edits to other people's files.

## Constraints
- Python + uv. Run: `uv run streamlit run app.py`. `datasets` is a dev-only dependency.
- Deploy on Streamlit Community Cloud with app.py in root. requirements.txt is generated: `uv export --no-dev --no-hashes -o requirements.txt` (re-run after `uv add`).
- Keep it simple and demo-stable. Sara's entries are preloaded so the demo works immediately.
- Commit small and often.
