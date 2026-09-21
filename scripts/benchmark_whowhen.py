"""Who&When / Who&When Pro benchmark harness — Phase 5/6.

Expects a JSONL with 12k+ labeled trajectories. Each line:
  {"trace": {"task": "...", "steps": [{"component": "retriever", "status": "success"}, ...]}, "labels": {"responsible_component": "retriever", "failure_step": 2, "failure_category": "retrieval_error"}}
Run: python scripts/benchmark_whowhen.py --input data/whowhen_pro.jsonl

Computes Who/When/Error F1/Joint Accuracy per project-plan.md:1196.
Uses Jev via app/services/jev_service.analyze_trace (real Jev required).
"""

import argparse
import json
import asyncio
from collections import Counter

COMPONENTS = ["planner", "retriever", "tool_router", "memory", "generator", "verifier", "external_api"]


def _eval(pred: dict, label: dict):
    who = pred["responsible_component"] == label.get("responsible_component")
    when = pred.get("failure_step") == label.get("failure_step")
    err = pred["failure_category"] == label.get("failure_category")
    joint = who and when and err
    return who, when, err, joint


async def run_one(trace: dict):
    from app.services.jev_service import analyze_trace

    return await analyze_trace(trace)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSONL with {trace, labels}")
    parser.add_argument("--limit", type=int, default=100, help="max examples to evaluate")
    args = parser.parse_args()

    who_c = when_c = err_c = joint_c = 0
    total = 0
    per_cat = Counter()

    import pathlib
    path = pathlib.Path(args.input)
    if not path.exists():
        print(f"Dataset not found: {path}. Place Who&When Pro JSONL there (see https://github.com/ag2ai/whowhen_pro)")
        return

    lines = path.read_text().splitlines()[: args.limit]
    for line in lines:
        ex = json.loads(line)
        pred = await run_one(ex["trace"])
        labels = ex.get("labels", {})
        who, when, err, joint = _eval(pred, labels)
        who_c += who
        when_c += when
        err_c += err
        joint_c += joint
        total += 1
        per_cat[pred["failure_category"]] += 1
        print(f"{total}: Who={who} When={when} Err={err} Joint={joint} pred={pred['responsible_component']}/{pred['failure_category']} label={labels}")

    print(f"\nEvaluated {total}")
    if total:
        print(f"Who Accuracy:  {who_c/total:.3f}")
        print(f"When Accuracy: {when_c/total:.3f}")
        print(f"Error F1 (acc proxy): {err_c/total:.3f}")
        print(f"Joint Accuracy: {joint_c/total:.3f}")
        print(f"Predicted categories: {dict(per_cat)}")


if __name__ == "__main__":
    asyncio.run(main())
