# Pennovia product-quality acceptance: evidence and decision

Date: 21 November 2026. Scope: Core, CLI, Studio, publishing boundaries and real-model author-voice capability.

**Decision: FULL PRODUCT ACCEPTANCE NOT GRANTED.** This is an evidence-based release decision, not an assertion that the existing software is unusable.

## Latest exact-head checkpoint — final 21 November review

- Latest reviewed main: `24f756d3d567efcee882f2cd46ff681106b5aa76`, after PRs [#54](https://github.com/yoldaolmak/Pennovia/pull/54) (persistent runner caches and bounded real-model smoke), [#57](https://github.com/yoldaolmak/Pennovia/pull/57) (default-branch cache seeding), and [#56](https://github.com/yoldaolmak/Pennovia/pull/56) (actual Ollama completion receipts, Studio/CLI warning and comparable experiment).
- Its [postmerge exact-head CI run #44909365422](https://github.com/yoldaolmak/Pennovia/actions/runs/44909365422) succeeded: all 6 jobs (Python 3.10/3.11/3.12 + Ruff, real Chromium Studio, wheel installation, container smoke); Python 3.11 reported **315 passed, 2 skipped, 84.36% coverage**. Static correctness passed. No open PR remained at this checkpoint.
- Main's [model cache seed run #44909214193](https://github.com/yoldaolmak/Pennovia/actions/runs/44909214193) completed and saved `Linux-pennovia-ollama-qwen25-15b-v1`. Versioned Chromium and pip caches also produced verified cache hits. These are real cache operation receipts, **not** a measured end-to-end speedup. Historical main CI was approximately 54 seconds; latest main CI approximately 57 seconds. Avoid a percentage speedup claim.
- The [actual local-model run #44908822086](https://github.com/yoldaolmak/Pennovia/actions/runs/44908822086) was successful as a workflow and recorded genuine model `done`, `done_reason` and token usage for each arm. **All 4 Pennovia-guided drafts stopped at the 640-token limit (`done_reason=length`)**, so **0/4 paired cases were eligible** for a superiority claim. Earlier favorable style-distance numbers do not constitute acceptable writer-voice results.
- The earlier native-Turkish prompt pilot [PR #53](https://github.com/yoldaolmak/Pennovia/pull/53) was **closed without merging** after real outputs remained incoherent or repetitive; do not call it an accepted product capability.
- Branch protection remains absent (`main.protected=false`). GitHub's connected application can inspect but cannot administer required-check rules; passing CI is therefore **not technically merge-enforced**.

**Overall product decision: NOT ACCEPTED.** The CI/pipeline and objective detection improvements passed their engineering checks. Pennovia has **not** demonstrated reliable author-voice fidelity or publishable Turkish prose, source-grounded factual accuracy, independently verified remote export outcomes, or enforceable branch governance. Do not turn this explicit failure into an acceptance badge.

## Verified delivery baseline

- Main at the start of this review: `84d53ca53c3f33e73b04bef20ba546de7a252800`.
- Its six ordinary CI jobs completed successfully on the exact main commit.
- PR #47 merged the rights-cleared paired live-model evaluation, the source mirror provenance and the unresolved-placeholder fail gate.
- PR #50 merged confident output-language mismatch detection.
- The real-model workflow [#44904596907](https://github.com/yoldaolmak/Pennovia/actions/runs/44904596907) completed, with an archived `pennovia-paired-voice-evidence` artifact containing the real outputs, model digest, source hashes, randomized drafts and blank review sheet.
- The model was local Ollama `qwen2.5:1.5b`. No paid provider is represented as tested.

## What the experimental outputs show

The published paired benchmark ran two English and two Turkish comparisons. A smaller **held-out style-distance score** is descriptively closer to the held-out sample, but is neither a calibrated authorship score nor evidence of readable, accurate prose.

| Case | Pennovia distance | Neutral distance | Word-length ratio | Evidence interpretation |
| --- | ---: | ---: | ---: | --- |
| Twain EN #1 | 0.3839 | 0.4320 | 1.196 | Descriptive Pennovia advantage; both outputs English |
| Twain EN #2 | 0.4273 | 0.4609 | 1.385 | Descriptive Pennovia advantage; both outputs English |
| Seyfettin TR #1 | 0.3634 | 0.3061 | 4.174 | **Invalid comparison:** neutral 69 words, Pennovia 288; Pennovia text loops |
| Seyfettin TR #2 | 0.4030 | 0.4207 | 2.269 | **Invalid comparison:** Pennovia generated English instead of Turkish; neutral loops |

Both English pairs are eligible on language and length, but they are **not** blinded editorial endorsements. Both Turkish pairs are invalid for product superiority inference; counting TR #2 as a style win would be misleading. No original-source 12-gram copying was found in these four pairs. This limited check does not prove noncopying or rights compliance generally.

In the archived prose, the Turkish drafts also contain repeated food/travel phrases and broken syntax. Our inspection is *not blinded*, so it cannot replace the independent A/B review. The benchmark's old numeric win indicator must never override comparison validity; the follow-up quality code makes invalid outcomes explicitly ineligible.

## Repeated-model findings and failed localization hypothesis

The first table is **one stochastic run**, not a replicated superiority result. Later independent actual-model trials using the same `qwen2.5:1.5b` family contradicted a stable Pennovia advantage:

- [Run #44906224404](https://github.com/yoldaolmak/Pennovia/actions/runs/44906224404), accepted in merged [PR #51](https://github.com/yoldaolmak/Pennovia/pull/51): Twain EN #1 neutral closer; Twain EN #2 Pennovia closer; Seyfettin TR #1 invalid for severe repetition and length; Seyfettin TR #2 structurally eligible but neutral closer. The Turkish texts contained broken or incomplete prose even when structurally eligible.
- [Run #44906957205](https://github.com/yoldaolmak/Pennovia/actions/runs/44906957205), [PR #53](https://github.com/yoldaolmak/Pennovia/pull/53) **closed without merge**: native Turkish genre labels and a Turkish language reminder did not establish usable, coherent Turkish writing. Twain EN #1 neutral closer, Twain EN #2 invalid for a 12-word source-copy span, Seyfettin TR #1 invalid for severe repetition (four-gram share 0.485), Seyfettin TR #2 had a lower Pennovia style-distance but still contained substantial semantic and grammatical failures. The source-copy in an unchanged English arm is an observed stochastic failure, not proof that Turkish localization caused it.

Thus neither **2/2 English improvement**, nor **reliable Turkish drafting**, nor overall human editorial quality is established. PR #51's quality integrity screen remains merged to main at `2b668aaf957e13e42d73ebb50acc6164d058b371`, whose postmerge [CI #44906774667](https://github.com/yoldaolmak/Pennovia/actions/runs/44906774667) passed all six jobs. Prompt-only localization was intentionally rejected rather than shipped on a green CI result. Both runs keep downloadable source hashes, real model outputs and blank blinded-review sheets; *no blind editorial review was performed*.

## New quality safety work

- Recognizable unresolved factual markers fail an otherwise high scoring review; a high number cannot certify a finished travel guide.
- Strong wrong-language evidence fails review for a known-language author profile.
- Severe four-word-sequence looping fails review for a sufficiently long text when the source author profile does not itself exhibit an intentionally tiny vocabulary. Moderately formulaic output receives a visible review note. This structural screen is conservative and **cannot certify semantic coherence**.
- Paired results now retain raw distances but cannot report a numeric win if either arm is too short, very uneven in length, in the wrong/unknown language, a severe repetition loop or an exact long-span copy.

## Remaining hard acceptance conditions

1. **Author voice, #45:** obtain a sufficiently powered bilingual, multilingual-genre experiment; include actual blind human reviewer judgments and adverse cases. The 2/2 English observation from the first run did not reproduce consistently and does not establish product superiority.
2. **Grounded claims, #48:** explicit factual and firsthand-evidence inputs, claim-level source/readback checks, a safe editorial review surface, and fail-closed publication behavior for unverified claims. A clean stylistic audit is not factual verification.
3. **Repository enforcement, #46:** main is not protected and no required exact-head checks/ruleset is configured. Existing CI is successful but advisory until governance changes are made.
4. **Real remote exports, #49:** WordPress and Google Drive need authorized *non-production* creation/readback proof, including indeterminate-network-outcome tests. Mock tests cannot certify a remote write.
5. **Generation completion and coherence, #52:** The objective model receipt and cutoff handling are merged; authentic testing proved 4/4 guided texts ended at the token limit. Independent semantic readability and natural Turkish still need credible evidence, with stronger permitted local modeling or an explicit feature limitation.
5. **Completion and fluency, #52:** preserve real model finish metadata, detect token-limited fragments and independently evaluate semantic coherence and natural Turkish. A mechanically eligible style comparison cannot certify a complete or readable draft.

**Release interpretation:** The author can inspect/edit drafts and must retain editorial authority. Neither an offline test run, a numeric style score, nor this limited local-model trial authorizes unattended publication or a full-product-quality claim.
