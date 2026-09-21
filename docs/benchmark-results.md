# Benchmark Results — Who&When Pro (text split) × JevTrace

**Date:** 2026-09-21 · **Model:** `jev-latest` (resolved `jev-1.13.0`) · **Sample:** 84 traces
**Dataset:** [Leoxx/whowhen_pro](https://huggingface.co/datasets/Leoxx/whowhen_pro), `data/text.jsonl` (6,257 trajectories)

## Headline numbers

| Axis | Metric | Score | n |
|---|---|---|---|
| Who (Agent) | accuracy, multi-agent traces only | **0.500** | 42 |
| When (Step) | accuracy, step-mappable traces | **0.580** | 69 |
| Error | accuracy on mapped 7 categories | **0.179** | 84 |
| Error | macro-F1 over 6 observed categories | **0.105** | 84 |
| Joint (All) | all three correct | **0.091** | 33 |

Sample: stratified 6 traces × 14 error modes, `--seed 0`. One parallel SystemOne
call per trace (standard component/category/severity/7 Nouls + `decisive_step`
Choice + `responsible_agent` Choice). Real Jev, no mocks. Parallel questions
cannot see each other, so benchmark extras don't affect standard answers.

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

## Per-mode error accuracy (n=6 each)

| Mode | Acc | True category |
|---|---|---|
| R.1 hallucination | **0.833** | hallucination |
| R.3 numerical | 0.667 | hallucination |
| R.2 reasoning, R.4 misunderstanding, C.3 over-reliance | 0.333 | mixed |
| A.1, A.2, A.3, A.4, C.1, C.2, PL.1, V.1, V.2 | 0.000 | mixed |

## Per-framework (Who / When / Error)

| Framework | Who | When | Error |
|---|---|---|---|
| alfagent | —/0 | 1/8 | 0/8 |
| debate | 5/8 | 1/8 | 3/8 |
| dylan | 0/2 | 0/2 | 1/2 |
| macnet | 3/9 | —/0 | 1/9 |
| magentic-one | 8/18 | 11/18 | 2/18 |
| mathchat | 4/4 | 3/4 | 3/4 |
| metagpt | 1/1 | 1/1 | 0/1 |
| smolagents | —/0 | 23/28 | 5/34 |

## Reading the numbers

- **True hallucinations (R.1) are Jev's strength (0.833).** Grounded-text
  failure attribution is exactly what typed Noul/Choice judgments do well.
- **Strong hallucination bias.** Most predictions land on `hallucination`,
  which inflates R.1/R.3 but zeroes tool/timeout/memory/verification modes.
  `tool_failure` was never predicted in 84 calls despite 12 true cases —
  the state (`{component, status, text}`) may under-describe tool-call mechanics.
- **When (0.580) beats chance** on traces with up to 31 steps — the dynamic
  `decisive_step` Choice works, but long alfworld traces (29 steps) dilute it.
- **Who (0.500)** includes a fixed conversion gap: debate/dylan speaker names
  live inside round `turns` and were initially missed (Who was 0.381 before
  the fix). Remaining misses concentrate on magentic-one `orchestrator` vs
  `websurfer`/`coder` ambiguity — the orchestrator relays others' errors.
- Matches the benchmark paper's qualitative finding: failure attribution is
  hard, especially root-cause classification (our Error macro-F1 0.105).

## Limitations

- n=84 sample, single run, no confidence intervals — treat as baseline, not leaderboard.
- Mode→category mapping involves judgment calls (notably R.2/R.3→hallucination,
  A.3/A.4→timeout, C.1→planning_error); a different mapping shifts Error numbers.
- Text split only (Jev is text-only); image/video/GUI splits excluded.
- Production `analyze_trace` sends `{component, status}` without step text —
  these results used a richer state, so they overstate the current API path.
  Recommendation: include truncated step content in the normalizer (P2).

## Reproduce

```bash
python scripts/download_whowhen.py            # text split + taxonomy → data/ (gitignored)
python scripts/benchmark_whowhen.py --per-mode 6 --seed 0
# results: data/whowhen_pro/jev_results.jsonl (resumable), data/whowhen_pro/jev_summary.json
python scripts/benchmark_whowhen.py --limit 20   # smoke test
```

Raw predictions (84 rows) are gitignored under `data/`; this doc is the
committed record. Summary JSON schema: `{n, who:{acc,n}, when:{...},
error:{acc,macro_f1,n,classes}, joint:{...}, per_mode_acc}`.
