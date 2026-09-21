"""Who&When Pro evaluation for JevTrace — P1 roadmap.

Pipeline: Who&When Pro trace -> whowhen_adapter (JevTrace state + mapped labels)
-> ONE parallel SystemOne call (standard component/category/severity/7 Nouls
+ decisive_step Choice + responsible_agent Choice) -> Who/When/Error/Joint.

Parallel questions can't see each other, so the extra benchmark questions do
not affect the standard JevTrace answers.

Usage:
  python scripts/download_whowhen.py            # one-time: text split + taxonomy
  python scripts/benchmark_whowhen.py --per-mode 6 --seed 0   # ~84 traces
  python scripts/benchmark_whowhen.py --per-mode 20 --seed 0  # ~280 traces
  python scripts/benchmark_whowhen.py --per-framework 50 --seed 0  # 400, per-FW table
  python scripts/benchmark_whowhen.py --limit 2 --experiment smoke  # smoke (own files)

Results append to data/whowhen_pro/jev_results[_<experiment>].jsonl (resumable,
gitignored); summary -> jev_summary[_<experiment>].json. Numbers -> docs/benchmark-results.md.
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
RESULTS_DIR = ROOT / "data" / "whowhen_pro"


def results_paths(experiment):
    suffix = f"_{experiment}" if experiment and experiment != "baseline" else ""
    return (RESULTS_DIR / f"jev_results{suffix}.jsonl",
            RESULTS_DIR / f"jev_summary{suffix}.json")


def load_results(path):
    done = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
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


def wilson(hits, n, z=1.96):
    """Wilson 95% CI half-width for binomial accuracy."""
    if not n:
        return None
    p = hits / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5 / denom
    return {"acc": p, "low": max(0.0, center - half), "high": min(1.0, center + half), "n": n}


def _acc_wilson(pairs):
    hits = sum(1 for h in pairs if h)
    return wilson(hits, len(pairs))


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

    last_exc = None
    for attempt in range(4):
        try:
            async with sem:
                async with AsyncTypeSafeClient(api_key=key, model="jev-latest") as client:
                    result = await client.system_one(state=state, questions=questions)
            break
        except Exception as exc:  # noqa: BLE001 — transient 503/429 get retried
            last_exc = exc
            await asyncio.sleep(5 * (attempt + 1))
    else:
        raise last_exc

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
    ap.add_argument("--per-mode", type=int, default=0, help="traces per error mode (0=off)")
    ap.add_argument("--per-framework", type=int, default=0, help="traces per framework (0=off)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="cap total traces (0=no cap)")
    ap.add_argument("--input", default=str(DATA))
    ap.add_argument("--experiment", default="baseline", help="results namespace (baseline, criteria-v2, ...)")
    args = ap.parse_args()
    if not args.per_mode and not args.per_framework:
        args.per_mode = 6  # default preserves original behavior

    RESULTS, SUMMARY = results_paths(args.experiment)

    from app.core.config import get_jev_api_key

    key = get_jev_api_key()
    if not key:
        raise RuntimeError("JEV_API_KEY/TYPESAFE_API_KEY not set — real Jev required, no mocks.")

    recs = [json.loads(l) for l in Path(args.input).read_text(encoding="utf-8").splitlines() if l.strip()]
    recs = [r for r in recs if json.loads(r["ground_truth"]).get("mode") in MODE_TO_CATEGORY]

    rng = random.Random(args.seed)
    sample = []
    if args.per_framework:
        by_fw = defaultdict(list)
        for r in recs:
            by_fw[r["framework"]].append(r)
        for fw in sorted(by_fw):
            pool = by_fw[fw][:]
            rng.shuffle(pool)
            sample.extend(pool[: args.per_framework])
        print(f"frameworks: {len(by_fw)}, sampled: {len(sample)}")
    else:
        by_mode = defaultdict(list)
        for r in recs:
            by_mode[json.loads(r["ground_truth"])["mode"]].append(r)
        for mode in sorted(by_mode):
            pool = by_mode[mode][:]
            rng.shuffle(pool)
            sample.extend(pool[: args.per_mode])
        print(f"modes: {len(by_mode)}, sampled: {len(sample)}")
    rng.shuffle(sample)
    if args.limit:
        sample = sample[: args.limit]

    done = load_results(RESULTS)
    todo = [r for r in sample if r["id"] not in done]
    print(f"experiment: {args.experiment}, already done: {len(sample) - len(todo)}, to run: {len(todo)}")
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

    who_all, when_all, joint_all = [], [], []
    yt, yp, per_mode = [], [], Counter()
    fw_stats = defaultdict(lambda: {"who": [], "when": [], "err_t": [], "err_p": [], "joint": []})
    for r in rows:
        p, lab, meta = r["pred"], r["labels"], r["meta"]
        fw = fw_stats[meta["framework"]]
        ok = []
        if lab["agents"]:
            hit = p.get("responsible_agent") in lab["agents"]
            who_all.append(hit)
            fw["who"].append(hit)
            ok.append(hit)
        if lab["step"] is not None:
            hit = p["decisive_step"] == lab["step"]
            when_all.append(hit)
            fw["when"].append(hit)
            ok.append(hit)
        if lab["category"]:
            yt.append(lab["category"])
            yp.append(p["failure_category"])
            fw["err_t"].append(lab["category"])
            fw["err_p"].append(p["failure_category"])
            hit = p["failure_category"] == lab["category"]
            ok.append(hit)
            per_mode[(lab["mode"], hit)] += 1
        if len(ok) == 3:
            joint_all.append(all(ok))
            fw["joint"].append(all(ok))

    cats = sorted(set(yt))
    summary = {
        "n": len(rows),
        "experiment": args.experiment,
        "who": _acc_wilson(who_all),
        "when": _acc_wilson(when_all),
        "error": {"acc": sum(1 for t, p in zip(yt, yp) if t == p) / len(yt) if yt else None,
                  "macro_f1": macro_f1(yt, yp, cats), "n": len(yt), "classes": cats},
        "joint": _acc_wilson(joint_all),
        "per_mode_acc": {m: {"acc": sum(v for (mm, h), v in per_mode.items() if mm == m and h)
                             / sum(v for (mm, _), v in per_mode.items() if mm == m),
                             "n": sum(v for (mm, _), v in per_mode.items() if mm == m)}
                         for m in sorted({m for m, _ in per_mode})},
        "per_framework": {fw: {"n": len(f["who"]) + len(f["when"]),
                               "who": _acc_wilson(f["who"]), "when": _acc_wilson(f["when"]),
                               "error": {"acc": sum(1 for t, p in zip(f["err_t"], f["err_p"]) if t == p) / len(f["err_t"]) if f["err_t"] else None, "n": len(f["err_t"])},
                               "joint": _acc_wilson(f["joint"])}
                          for fw, f in sorted(fw_stats.items())},
        "note": "Who on agent-labeled traces; When on step-mappable traces; Error on mapped 7 categories.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print("\n" + json.dumps(summary, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
