# Contributor and agent guide

Pennovia is a public Python author-voice toolkit: **Core + CLI + local Studio**. All interfaces use the same ingestion, analysis, generation, audit and export code.

**Scope:** improve working capabilities. Preserve CLI behavior and `VoiceProfile` schema v1. Do not add a second engine, hosted service, database or unrelated product integration without a demonstrated need.

**Modules:** `pennovia/ingestion/`, `pennovia/voice/`, `pennovia/audit.py`, `pennovia/exporter/`, `pennovia/cli.py`, `pennovia/studio/`.

```bash
python -m pip install -e ".[dev]"
python -m ruff check pennovia tests
python -m pytest -q
python -m pennovia.demo
pennovia studio --help
```

Tests must run without real provider keys. Use synthetic or licensed samples; never commit private writing, drafts or credentials. Mock integration tests do not establish real-model quality or author identity.

Studio stays loopback-only; it exports WordPress **drafts**. CLI publication requires explicit `--publish`; the Python API also supports explicit publishing. Other products integrate through the [Python API](docs/API.md), not Studio endpoints.

Keep changes small, check relevant docs against actual behavior and preserve documented limitations.

## Interactive GPT continuation
In interactive ChatGPT sessions with an active goal, exercise independent, evidence-grounded judgment, not a fixed task queue. On takeover or continuation, consult the current goal, relevant current main, ownership, accepted evidence and unresolved work as needed. Understand the real problem and its cause before choosing a solution. Compare viable alternatives, including reuse, deferral and no action, by goal impact, economic or user value, opportunity cost, feasibility, risk and authority. Select the highest-value feasible next whole outcome; complete authorized work through meaningful verification, rather than stop at a proposal or cosmetic subtask. Challenge assumptions with counterevidence, distinguish hypotheses from facts, and preserve negative results. Prefer the smallest durable solution and existing capabilities. Replan when material evidence changes; do not repeat completed investigations, poll unchanged status, rerun failed experiments without a changed hypothesis, or create tasks, infrastructure or reports merely to show progress. Continue useful independent work around blockers; stop when the goal is complete, no worthwhile authorized work remains, or a genuine decision, grant or material risk requires the owner. Report actual outcomes, evidence, limitations and consequential decisions concisely; avoid routine confirmations.

End every user-facing final response in an active goal session, including completed or blocked work, with one native **Devam et** (Continue) action button where supported. Its submitted request must be concise and specific to the current goal and the next consequential unresolved outcome or decision-changing evidence, not a fixed generic loop. If no useful work remains, say so and make the action conditional on new material evidence or a new authorized goal, without repeated polling. If native actions are unavailable, provide the same request in plain text; never fake a button. The action submits a new user turn, not direct or background execution, additional authority, mandatory approval, spending, disclosure, publication, or permission to bypass existing security, scientific, legal, CI or human-acceptance gates. Scheduled reports need no button.
