# Benchmark Results — Who&When Pro (text split) × JevTrace

**Date:** 2026-09-21 · **Model:** `jev-latest` (resolved `jev-1.13.0`)
**Dataset:** [Leoxx/whowhen_pro](https://huggingface.co/datasets/Leoxx/whowhen_pro), `data/text.jsonl` (6,257 trajectories)

## Headline numbers (all tiers)

| Tier | n | Who (95% CI) | When (95% CI) | Error acc / macro-F1 | Joint (95% CI) |
|---|---|---|---|---|---|
| Baseline: 6/mode, seed 0 | 84 | 0.500 (42) | 0.580 (69) | 0.179 / 0.105 | 0.091 (33) |
| Tier 1: 20/mode, seed 0 | 280 | **0.574** (0.492–0.653, 141) | **0.542** (0.479–0.605, 236) | **0.171 / 0.096** | **0.124** (0.075–0.197, 113) |
| Tier 2: 50/framework, seed 0 | 400 | **0.613** (0.557–0.667, 300) | **0.445** (0.394–0.498, 348) | **0.328 / 0.143** | **0.168** (0.127–0.219, 250) |
| Ablation criteria-v2 (same 84) | 84 | 0.524 (42) | 0.580 (69) | **0.238 / 0.208** | 0.121 (33) |

CIs are Wilson 95%. Tier 1 reuses the baseline 84 (same seed → superset, resumable).
Tier 2 composition differs (uniform per-framework), so cross-tier deltas partly
reflect difficulty mix, not just scale — see per-framework table.

One parallel SystemOne call per trace (standard component/category/severity/7
Nouls + `decisive_step` Choice + `responsible_agent` Choice). Real Jev, no
mocks. Parallel questions cannot see each other, so benchmark extras don't
affect standard answers.

## Per-framework (Tier 2, n=50 each)

| Framework | Who | When | Error | Joint |
|---|---|---|---|---|
| alfagent | —/0 | 0.64 | 0.22 | — |
| debate | 0.42 | 0.06 | 0.38 | 0.00 |
| dylan | 0.42 | 0.06 | 0.48 | 0.02 |
| macnet | 0.86 | —/0 | 0.28 | — |
| magentic-one | 0.74 | 0.68 | 0.38 | 0.26 |
| mathchat | 1.00 | 0.80 | 0.64 | 0.56 |
| metagpt | 0.24 | 0.12 | 0.04 | 0.00 |
| smolagents | —/0 | 0.77 | 0.20 | — |

Patterns: grounded QA (`mathchat`) is Jev's home turf; round-format debate/dylan
traces defeat step localization (0.06); code-heavy `metagpt` defeats everything
(0.04); single-agent frameworks contribute no Who labels by design.

## Per-mode error accuracy (baseline n=6 each; ablation in parens)

| Mode | Baseline | criteria-v2 | True category |
|---|---|---|---|
| R.1 hallucination | **0.833** | 0.500 | hallucination |
| R.3 numerical | 0.667 | 0.333 | hallucination |
| R.2 reasoning, R.4 misunderstanding, C.3 over-reliance | 0.333 | 0.333 / 0.333 / **0.667** | mixed |
| A.4 looping | 0.000 | **1.000** | timeout |
| A.2 format | 0.000 | 0.167 | tool_failure |
| A.1, A.3, C.1, C.2, PL.1, V.1, V.2 | 0.000 | 0.000 | mixed |

## Ablation: taxonomy-grounded criteria (paired, same 84 ids)

Rewrote `_category_criteria()` with contrastive, taxonomy-grounded descriptions
(hallucination requires the claim ABSENT from observations; tool_failure requires
a concrete failed call; timeout covers premature/looping termination) plus an
orchestrator-relay note in the component question. Re-ran the identical sample
(`--experiment criteria-v2`):

| Metric | Baseline | criteria-v2 | Δ |
|---|---|---|---|
| Who | 0.500 | 0.524 | +0.024 |
| When | 0.580 | 0.580 | ±0 (step question unchanged, as expected) |
| Error acc | 0.179 | **0.238** | +0.059 (+33% relative) |
| Error macro-F1 | 0.105 | **0.208** | **~2×** |
| Joint | 0.091 | 0.121 | +0.030 |

Prediction mix shifted: `timeout` 0.5% → 30% of predictions (A.4: 0→1.0),
`hallucination` 54% → 45% (R.1 recall 0.83→0.50 — the price of de-biasing).
`tool_failure` still rarely predicted (2.4%) — next target.

## Method (see `scripts/whowhen_adapter.py`)

**Trajectory → JevTrace state.** `user` → task text; `action` → `tool_router`
(`generator` if final answer); `agent`/`agent_id` → component by role map
(orchestrator→planner, coder→generator, websurfer→retriever, critic→verifier…);
`planning`/`round` → planner; `final_answer` → generator. All statuses
`"success"` — no label leakage. Content truncated (task 1500 / step 600 chars).

**Ground-truth mapping.** Who&When step labels are framework-specific:
`int` action numbers (alfagent/smolagents), `"round.position"` strings
(magentic-one), `round` (debate/dylan), `stage` (metagpt/macnet), sometimes
`None`. Mapped to our 1-based step index; unmappable traces (5.4%: macnet
round-only labels, smolagents step-0, out-of-range steps) are excluded from
When and reported as coverage, not failures.

**Error-mode mapping** (14 text-split modes → 7 JevTrace categories):

| Modes | Category |
|---|---|
| R.1, R.2, R.3 | hallucination |
| R.4, PL.1, C.1 | planning_error |
| A.1, A.2 | tool_failure |
| A.3, A.4 | timeout |
| V.1, C.2 | memory_failure |
| V.2, C.3 | verification_failure |

## Reading the numbers

- **True hallucinations (R.1) are Jev's strength (0.83 baseline).** Grounded-text
  failure attribution is exactly what typed Noul/Choice judgments do well.
- **Hallucination bias is real but fixable.** Baseline predicted `hallucination`
  in 68/84 calls and never `tool_failure` (12 true cases). Taxonomy-grounded
  criteria doubled macro-F1 (0.105→0.208) — prompt engineering moves these
  numbers more than anything else, matching the TypeSafe skill guidance.
- **When (~0.5–0.6) beats chance** on traces with up to 31 steps — the dynamic
  `decisive_step` Choice works, except round-format debate/dylan (0.06).
- **Who (~0.5–0.6)** includes a fixed conversion gap: debate/dylan speaker names
  live inside round `turns` and were initially missed (Who was 0.381 before
  the fix). Remaining misses concentrate on magentic-one `orchestrator` vs
  `websurfer`/`coder` ambiguity — the orchestrator relays others' errors.
- Matches the benchmark paper's qualitative finding: failure attribution is
  hard, especially root-cause classification.

## Limitations

- Tier 2 (n=400) is the largest run; full 6,257-text sweep not yet run
  (~2.6–3.5h, resumable — see commands below). No confidence intervals on
  per-mode cells (n=6–20).
- Mode→category mapping involves judgment calls (notably R.2/R.3→hallucination,
  A.3/A.4→timeout, C.1→planning_error); a different mapping shifts Error numbers.
- Text split only (Jev is text-only); image/video/GUI splits excluded.
- ~~Production `analyze_trace` sent `{component, status}` without step text~~ —
  **fixed**: normalizer now sends `{component, status, text, latency_ms}`
  (`jev_trace_parser/normalizer.py`), so prod matches benchmark conditions.

## Reproduce

```bash
python scripts/download_whowhen.py            # text split + taxonomy → data/ (gitignored)
python scripts/benchmark_whowhen.py --per-mode 6 --seed 0        # 84, baseline
python scripts/benchmark_whowhen.py --per-mode 20 --seed 0       # 280, reuses 84
python scripts/benchmark_whowhen.py --per-framework 50 --seed 0 # 400, per-FW table
python scripts/benchmark_whowhen.py --per-mode 6 --seed 0 --experiment criteria-v2  # ablation
# results: data/whowhen_pro/jev_results[_<exp>].jsonl (resumable), jev_summary[_<exp>].json
```

Raw predictions are gitignored under `data/`; this doc is the committed record.
Summary JSON schema: `{n, experiment, who:{acc,low,high,n}, when:{...},
error:{acc,macro_f1,n,classes}, joint:{...}, per_mode_acc, per_framework}`.
