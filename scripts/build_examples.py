"""One-off: pull ~12 high-voted Counsel Chat Q&A pairs into data/examples.json.
Run with: uv run python scripts/build_examples.py
"""
import json
from pathlib import Path

from datasets import load_dataset

ds = load_dataset("nbertagnolli/counsel-chat", split="train")
rows = sorted(ds, key=lambda r: r.get("upvotes") or 0, reverse=True)

picked, seen_topics = [], set()
for r in rows:
    topic = r.get("topic") or ""
    q = (r.get("questionText") or "").strip()
    a = (r.get("answerText") or "").strip()
    if topic in seen_topics or not q or not a or len(a) > 1200:
        continue
    seen_topics.add(topic)
    picked.append({"topic": topic, "question": q, "answer": a})
    if len(picked) == 12:
        break

out = Path(__file__).resolve().parent.parent / "data" / "examples.json"
out.write_text(json.dumps(picked, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {len(picked)} examples to {out}")
