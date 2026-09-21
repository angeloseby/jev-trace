# Roadmap — JevTrace pending items

Saved 2026-09-21. Source of truth for what remains after `v0.1.0` (`62adb51`).

## P0 — Publish

- [x] **PyPI upload** — done 2026-09-21. `jev-trace 0.1.0` live at
  https://pypi.org/project/jev-trace/0.1.0/ (`twine check` passed, `twine upload` succeeded).
  Install: `pip install jev-trace` / `pip install jev-trace[langchain]`.

## P1 — Research

- [ ] **Who&When Pro evaluation** — `scripts/benchmark_whowhen.py` harness exists,
  but the 12k-trajectory dataset was never downloaded. Download dataset, run
  benchmark, publish Who/When/Error-F1/Joint numbers to `docs/benchmark-results.md`.

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
