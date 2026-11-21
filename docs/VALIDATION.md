# Validation limits

Pennovia measures **selected features of writing style**. Scores are uncalibrated; they do not verify authorship, lived experience or factual accuracy.

## What is tested

- Corpus reading, English/Turkish analysis, profile JSON compatibility, scoring and exports.
- Synthetic end-to-end CLI and Studio flows: analysis → model-shaped response → review → TXT/HTML/PDF and simulated WordPress draft.
- Errors such as blank provider replies and unusable inputs.

Offline tests use synthetic responses. They verify adapter behavior, **not** live model connectivity, publishing, writing quality or fidelity to a real author's style.

## Real-model validation

The separate [Live Model & Alpha Release](../.github/workflows/live-model-release.yml) workflow runs an **actual local Ollama model**, without provider keys. It downloads original chapters of Mark Twain's [*The Innocents Abroad*](https://www.gutenberg.org/ebooks/3176), builds a profile from chapters I, II and IV, and holds out chapter III. It generates two drafts through Pennovia plus an independent neutral control using the same model; the report includes source hash, model digest, word counts, heuristic results and real TXT/HTML/PDF exports.

The workflow stores the exact drafts and report as downloadable GitHub Actions artifacts. No claim of calibrated voice fidelity or factual correctness follows from this limited case. The bundled demo corpus is illustrative and is **not** used as an authenticated Twain sample in this experiment.

### Published v0.2.0 evidence

The [7 November 2026 release run](https://github.com/yoldaolmak/Pennovia/actions/runs/42406098002) completed real Ollama inference with `qwen2.5:1.5b` and archived the drafts, original-source SHA-256, model digest and TXT/HTML/PDF exports.

| Output | Words | Heuristic audit |
| --- | ---: | ---: |
| Profile-guided draft 1 | 814 | 77/100 |
| Profile-guided draft 2 | 672 | 68/100 |
| Neutral control | — | 83/100 |

The neutral control scored higher. This verifies execution, **not** an advantage in writer-style fidelity. The tagged [alpha release](https://github.com/yoldaolmak/Pennovia/releases/tag/v0.2.0) was published only after the separate live-model job, six main-branch CI checks and package-build verification succeeded.

## Paired bilingual author-voice experiment (quality acceptance)

`validation/paired_voice.py` extends the actual local Ollama run, with no cloud keys or mock model responses. It compares two original-author cases, in English and Turkish, with separate training and held-out writing:

- Mark Twain: chapters I, II and IV of *The Innocents Abroad* for training; chapter III held out. The original Project Gutenberg source or its validated public GITenberg mirror is hashed, and the exact downloaded URL is recorded.
- Ömer Seyfettin: Wikisource originals *Velinimet* and *Nâdan* for training, *Tos* held out; each remote source's byte hash and reuse basis are recorded.

For each case, two fictional story prompts are run twice with the same local model and genre: once with Pennovia's voice profile, once with a neutral control. Independent *descriptive* held-out distances compare eight observable stylistic features without using the product's own `audit()` or `score()` functions. Output-language and word-count comparability are reported, and exact 12-word source spans are flagged. This diagnostic is **not calibrated author recognition** or editorial quality.

The archived `pennovia-paired-voice-evidence` artifact contains the actual outputs under randomized A/B filenames, a separate answer key, source hashes and a blank blind-review form. A reviewer must score voice resemblance, readability and unsupported claims **without first looking at the answer key**. The form being generated does not mean anyone completed an independent review. No superiority or full product acceptance claim may be made without sufficient paired outcomes, independent judgment and failure-case analysis.

## Editorial output integrity

An `audit().passed()` result now also rejects recognisable unfinished factual placeholders (for example `[Taxi Fare]`, `[Attraction1]` or `____`) even if the voice heuristic would exceed 70/100. This is an intentional, high-confidence warning gate, **not** a comprehensive factual verifier. Automatic scoring cannot establish that transportation times, prices, sources or claimed firsthand experiences are true. The author must verify such claims and approve drafts before publication.

## How to interpret a score

Audit PASS requires **70/100, at least 200 words, no recognised unresolved placeholders, and no confidently detected language mismatch**. For an explicitly Turkish or English profile, a sufficiently long draft confidently classified as the other language fails review. Ambiguous language evidence does not trigger this gate; it is not a multilingual content certification. It compares sentence rhythm, first-person rate, questions, transitions, paragraph structure and common AI clichés. Different writers can receive similar scores.

Turkish negation detection covers only listed forms, not every inflected verb. Vocabulary richness uses 500-token windows; recurring phrases do not cross document boundaries. These are descriptive signals, not identity tests.

## Editorial review

Compare the draft with the source writing. Check rhythm, point of view and recurring expressions. Verify facts, quotes and claimed experiences separately.

Pennovia guides drafts; it does **not** identify authors or guarantee voice fidelity. A large authorship-identification benchmark is outside the product's current scope.
