# CI performance and verified quality boundary

Updated: 21 November 2026.

## Goal

Make the **existing GitHub Actions CI** faster and cheaper by reusing downloads and avoiding unbounded CPU-only generation. Do not add runners or a replacement execution architecture, remove test coverage, weaken security, or equate green CI with product acceptance.

## Permanent changes

- **Python** — setup-python's pip wheel cache, keyed to `pyproject.toml`, is used for Python 3.10, 3.11, 3.12, package/CLI, Chromium smoke and model validation. The redundant pip self-upgrade is removed.
- **Browser** — the Playwright Chromium cache is keyed to the *installed Playwright version*. New GitHub runners always set up their system dependencies; only a missing browser binary needs a fresh download. Desktop/mobile actual Chromium tests and screenshot artifacts remain.
- **Local model** — reuse the exact local `qwen2.5:1.5b` model blobs when present, pull on a miss and assert the model can be opened. Real provider inference still runs, and `model_digest` is captured. Cache state is not model-quality evidence.
- **Legacy model smoke** — actual styled and neutral Ollama calls have a matched `900` predicted-token ceiling. Previous unbounded generations could stall until Requests' 300s timeout on CPU-only runners. This change makes the experiment a bounded integration smoke, **not** a demonstration that full-length travel guides are editorially complete.
- **Cancel obsolete PR heads** — existing per-PR concurrency remains; main's exact-head runs are never canceled by newer PR commits.
- **Existing quality gates** — three Python-version tests with Ruff and coverage threshold, wheel install, container CLI, actual Studio browser, and real-model workflow are preserved. This optimization does not disable or silently skip any of them.

## Evidence and timing

Reference main CI `44906774667` (six checks, success) completed in roughly **54 seconds** wall time. First cache PR CI `44907381229` completed its six checks successfully in **58 seconds** while building the caches from cold state. **No speedup percentage is established by these two observations.** Inspect subsequent warm-cache runs separately; downloading/caching binaries may be slower the first time.

The first pre-budget real-model PR run `44907381175` failed with a genuine Ollama request timeout in its old unbounded three-call smoke phase. Its failure is preserved as evidence; the bounded follow-up must pass real model inference and be independently checked before merge.

GitHub cache visibility is branch/ref scoped. Model caches first populated on a PR ref are **not automatically a shared default-branch warm cache**. After a qualifying main-branch live-model run (or an explicitly dispatched workflow), later PRs can reuse the relevant main cache. A cold-cache run must remain correct.

To make this reliable without another runner, `.github/workflows/seed-model-cache.yml` runs **once when the workflow itself is added/changed on main**, or when explicitly dispatched against `main`. It uses the existing GitHub-hosted runner to install the Ollama CLI, pull or verify the exact `qwen2.5:1.5b` tag and seed the **same** versioned model cache key used by live-model PR jobs. It does not generate content, change any publication permissions, reduce product CI checks or assert model quality. Verify an actual cache hit in a subsequent PR before claiming model download savings. On cache-key changes, update this workflow and the live-model key together and re-prime main.

## Acceptance beyond CI

- `main` still needs enforced required checks/branch protection: issue #46. GitHub's connected tool does not provide repository-admin mutation for that setting.
- Independently reviewed author-voice superiority: issue #45; this is not proven by current four-pair exploration.
- Source-grounded factual and firsthand-claim verification: issue #48.
- Authorized non-production WordPress and Google Drive write/readback: issue #49.
- Model completion/incoherence detection: issue #52, addressed in a separate capability PR and **not** deemed solved by timing optimization.

Do not mark full product acceptance simply because the optimized jobs run faster or are green.
