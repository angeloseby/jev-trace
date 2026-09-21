# Roadmap — JevTrace pending items

Saved 2026-09-21. Source of truth for what remains after `v0.1.0` (`62adb51`).

## P0 — Publish

- [x] **PyPI upload** — done 2026-09-21. `jev-trace 0.1.0` live at
  https://pypi.org/project/jev-trace/0.1.0/ (`twine check` passed, `twine upload` succeeded).
  Install: `pip install jev-trace` / `pip install jev-trace[langchain]`.

## P1 — Research

- [x] **Who&When Pro evaluation** — done 2026-09-21. Text split (6,257 traces)
  downloaded; tiers n=84/280/400 → Who up to 0.613 / When up to 0.580 /
  Error acc up to 0.328 (macro-F1 0.208 after criteria-v2 ablation) /
  Joint up to 0.168. Per-framework table + Wilson CIs in `docs/benchmark-results.md`.
  Raw predictions gitignored under `data/whowhen_pro/`.
- [ ] **Full 6,257-text sweep** — harness is resumable (`--per-mode 27` max-balanced
  or add `--full`); ~2.6–3.5h overnight. Optional before any leaderboard claim.

## P2 — Product

- [ ] **Replay engine (stretch)** — counterfactual validation per `project-plan.md`:
  `Failed Trace → Replace Step 14 → Replay Agent → Success?` No endpoint or model exists yet.
- [ ] **Prod infra** — `infra/terraform/main.tf` and `infra/k8s/deployment.yaml`
  are placeholders. Only `docker-compose.yml` is deployable today.

## P3 — Maintenance

- [ ] **Version bump** — all packages at `0.1.0`. Next change: bump to `0.1.1`,
  rebuild `packages/tracer/dist/*`, `git tag v0.1.1`, push.

## Done (verified green before this file)

- 5 ponytail-audit shrinks, `pytest` 9 passed, `docker compose config` 0,
  dashboard `npm run build` 9/9, `twine check` passed, tagged `v0.1.0`.
