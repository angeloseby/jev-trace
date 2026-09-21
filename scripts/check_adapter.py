"""Validate adapter: conversion stats over full text split (no API calls)."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from whowhen_adapter import convert_record

recs = [json.loads(l) for l in Path("data/whowhen_pro/data/text.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
print("total:", len(recs))
who = when = joint = 0
step_lens = []
unmapped_modes = Counter()
unmapped_steps = Counter()
comp_dist = Counter()
for r in recs:
    state, labels, meta = convert_record(r)
    step_lens.append(len(state["steps"]))
    for s in state["steps"]:
        comp_dist[s["component"]] += 1
    if labels["agents"]:
        who += 1
    if labels["step"] is not None:
        when += 1
    else:
        gt = json.loads(r["ground_truth"])
        unmapped_steps[(r["framework"], str(gt.get("step")), str(gt.get("round")), str(gt.get("stage")))] += 1
    if not labels["category"]:
        unmapped_modes[gt.get("mode")] += 1
    if labels["agents"] and labels["step"] is not None and labels["category"]:
        joint += 1
import statistics
print(f"who-labeled: {who}, when-mappable: {when}, joint-eligible: {joint}")
print("steps/trace: min/median/max:", min(step_lens), statistics.median(step_lens), max(step_lens))
print("component dist:", dict(comp_dist))
print("unmapped modes:", dict(unmapped_modes))
print("unmapped step formats (top):", dict(sorted(unmapped_steps.items(), key=lambda x: -x[1])[:12]))
