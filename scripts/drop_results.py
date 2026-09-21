"""Drop results for frameworks needing re-run (adapter fix), keep the rest."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "whowhen_pro" / "jev_results.jsonl"
drop_fw = set(sys.argv[1:]) or {"debate", "dylan"}

rows = [json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]
kept = [r for r in rows if r["meta"]["framework"] not in drop_fw]
dropped = len(rows) - len(kept)
RESULTS.write_text("\n".join(json.dumps(r) for r in kept) + ("\n" if kept else ""), encoding="utf-8")
print(f"dropped {dropped}, kept {len(kept)}")
