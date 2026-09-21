"""Who&When Pro evaluation for JevTrace — P1 roadmap.

Pipeline: Who&When Pro trace -> whowhen_adapter (JevTrace state + mapped labels)
-> ONE parallel SystemOne call (standard component/category/severity/7 Nouls
+ decisive_step Choice + responsible_agent Choice) -> Who/When/Error/Joint.

Parallel questions can't see each other, so the extra benchmark questions do
not affect the standard JevTrace answers.

Usage:
  python scripts/download_whowhen.py            # one-time: text split + taxonomy
  python scripts/benchmark_whowhen.py --per-mode 6 --seed 0   # ~84 traces
  python scripts/benchmark_whowhen.py --limit 20              # quick smoke

Results append to data/whowhen_pro/jev_results.jsonl (resumable, gitignored);
summary -> data/whowhen_pro/jev_summary.json. Numbers -> docs/benchmark-results.md.
Requires JEV_API_KEY (or TYPESAFE_API_KEY). Real Jev only, no mocks.
"""

import argparse
import asyncio
import json
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
os.chdir(ROOT)  # config _find_env looks at cwd for .env

from whowhen_adapter import MODE_TO_CATEGORY, convert_record  # noqa: E402

DATA = ROOT / "data" / "whowhen_pro" / "data" / "text.jsonl"
RESULTS = ROOT / "data" / "whowhen_pro" / "jev_results.jsonl"
SUMMARY = ROOT / "data" / "whowhen_pro" / "jev_summary.json"


def load_results():
    done = {}
    if RESULTS.exists():
        for line in RESULTS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                r = json.loads(line)
                done[r["id"]] = r
    return done


def macro_f1(y_true, y_pred, labels):
    f1s = []
    for lab in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        denom = 2 * tp + fp + fn
        f1s.append(2 * tp / denom if denom else 0.0)
    return sum(f1s) / len(f1s) if f1s else 0.0


async def run_one(state, speakers, steps, key, sem):
    from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score

    from app.services.jev_service import _category_criteria, _choice_criteria

    questions = {
        "responsible_component": Choice(
            instructions="Which agent component is most responsible for the failure?",
            criteria=_choice_criteria(),
        ),
        "failure_category": Choice(
            instructions="What is the failure category of this run?",
            criteria=_category_criteria(),
        ),
        "severity": Score(
            instructions="How severe is this failure for the end user?",
            criteria=["Low", "Medium", "High", "Critical"],
        ),
        **{
            f"{c}_caused_failure": Noul(
                instructions=f"Did the {c} component cause or significantly contribute to the failure?",
                criteria={"true": f"{c} caused or contributed to failure",
                          "false": f"{c} did not cause failure"},
            )
            for c in ("planner", "retriever", "tool_router", "memory", "generator",
                      "verifier", "external_api")
        },
        "decisive_step": Choice(
            instructions="At which step did the failure become inevitable? Pick the step whose content shows the decisive error.",
            criteria={str(i + 1): f"Step {i + 1} [{s['component']}]: {s['text'][:120]}"
                      for i, s in enumerate(steps)},
        ),
    }
    if speakers:
        questions["responsible_agent"] = Choice(
            instructions="Which agent first introduced the decisive error?",
            criteria={name: f"Agent '{name}'" for name in speakers},
        )

    async with sem:
        async with AsyncTypeSafeClient(api_key=key, model="jev-latest") as client:
            result = await client.system_one(state=state, questions=questions)

    out = {
        "responsible_component": result.choices["responsible_component"].choice,
        "component_confidence": result.choices["responsible_component"].confidence,
        "failure_category": result.choices["failure_category"].choice,
        "category_confidence": result.choices["failure_category"].confidence,
        "severity": result.scores["severity"].score,
        "decisive_step": int(result.choices["decisive_step"].choice),
        "causal_graph": {c: float(result.nouls[f"{c}_caused_failure"].noul)
                         for c in ("planner", "retriever", "tool_router", "memory",
                                   "generator", "verifier", "external_api")},
        "model": result.model,
    }
    if speakers and "responsible_agent" in result.choices:
        out["responsible_agent"] = result.choices["responsible_agent"].choice
        out["agent_confidence"] = result.choices["responsible_agent"].confidence
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-mode", type=int, default=6, help="traces per error mode")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="cap total traces (0=no cap)")
    ap.add_argument("--input", default=str(DATA))
    args = ap.parse_args()

    from app.core.config import get_jev_api_key

    key = get_jev_api_key()
    if not key:
        raise RuntimeError("JEV_API_KEY/TYPESAFE_API_KEY not set — real Jev required, no mocks.")

    recs = [json.loads(l) for l in Path(args.input).read_text(encoding="utf-8").splitlines() if l.strip()]
    by_mode = defaultdict(list)
    for r in recs:
        gt = json.loads(r["ground_truth"])
        if gt.get("mode") in MODE_TO_CATEGORY:
            by_mode[gt["mode"]].append(r)

    rng = random.Random(args.seed)
    sample = []
    for mode in sorted(by_mode):
        pool = by_mode[mode][:]
        rng.shuffle(pool)
        sample.extend(pool[: args.per_mode])
    rng.shuffle(sample)
    if args.limit:
        sample = sample[: args.limit]
    print(f"modes: {len(by_mode)}, sampled: {len(sample)}")

    done = load_results()
    todo = [r for r in sample if r["id"] not in done]
    print(f"already done: {len(sample) - len(todo)}, to run: {len(todo)}")
    RESULTS.parent.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(4)
    for i, rec in enumerate(todo, 1):
        state, labels, meta = convert_record(rec)
        if not state["steps"]:
            print(f"[{i}/{len(todo)}] {meta['id']}: no steps, skipped")
            continue
        try:
            pred = await run_one(state, meta["speakers"], state["steps"], key, sem)
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}/{len(todo)}] {meta['id']}: ERROR {exc}")
            continue
        with RESULTS.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"id": meta["id"], "pred": pred,
                                "labels": labels, "meta": meta}) + "\n")
        print(f"[{i}/{len(todo)}] {meta['id']}: comp={pred['responsible_component']} "
              f"cat={pred['failure_category']} step={pred['decisive_step']} "
              f"agent={pred.get('responsible_agent')} | true={labels['category']}/{labels['step']}/{labels['agents']}")

    # ---- metrics over all sampled results ----
    by_id = {}
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            r = json.loads(line)
            by_id[r["id"]] = r
    rows = [by_id[r["id"]] for r in sample if r["id"] in by_id]

    who_t = who_c = when_t = when_c = joint_t = joint_c = 0
    yt, yp, per_mode, per_fw = [], [], Counter(), Counter()
    for r in rows:
        p, lab, meta = r["pred"], r["labels"], r["meta"]
        ok = []
        if lab["agents"]:
            who_t += 1
            hit = p.get("responsible_agent") in lab["agents"]
            who_c += hit
            ok.append(hit)
        if lab["step"] is not None:
            when_t += 1
            hit = p["decisive_step"] == lab["step"]
            when_c += hit
            ok.append(hit)
        if lab["category"]:
            yt.append(lab["category"])
            yp.append(p["failure_category"])
            hit = p["failure_category"] == lab["category"]
            ok.append(hit)
            per_mode[(lab["mode"], hit)] += 1
        per_fw[(meta["framework"], all(ok) if ok else None)] += 1
        if len(ok) == 3:
            joint_t += 1
            joint_c += all(ok)

    cats = sorted(set(yt))
    summary = {
        "n": len(rows),
        "who": {"acc": who_c / who_t if who_t else None, "n": who_t},
        "when": {"acc": when_c / when_t if when_t else None, "n": when_t},
        "error": {"acc": sum(1 for t, p in zip(yt, yp) if t == p) / len(yt) if yt else None,
                  "macro_f1": macro_f1(yt, yp, cats), "n": len(yt), "classes": cats},
        "joint": {"acc": joint_c / joint_t if joint_t else None, "n": joint_t},
        "per_mode_acc": {m: {"acc": sum(v for (mm, h), v in per_mode.items() if mm == m and h)
                             / sum(v for (mm, _), v in per_mode.items() if mm == m),
                             "n": sum(v for (mm, _), v in per_mode.items() if mm == m)}
                         for m in sorted({m for m, _ in per_mode})},
        "note": "Who on agent-labeled traces; When on step-mappable traces; Error on mapped 7 categories.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print("\n" + json.dumps(summary, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
