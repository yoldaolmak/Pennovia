"""Rights-aware, paired live-model voice comparison; not a certification of authorship.

Use the same local Ollama model, topic, genre and generation constraints for
profile-guided and neutral drafts. Never use private author material.
"""
import argparse
import csv
import hashlib
import json
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from pennovia.content_types.registry import get as get_type
from pennovia.voice.analyzer import _detect_language, analyze
from pennovia.voice.generator import _require_draft, generate
from pennovia.voice.integrity import repeated_fourgram_share
if __package__:
    from .live_model import MODEL, OLLAMA, _model_digest, _download_source, select_chapters
else:
    from live_model import MODEL, OLLAMA, _model_digest, _download_source, select_chapters


MAX_TOKENS = 640  # identical model decoding budget for both arms


TURKISH_STORIES = (
    ("Velinimet", "https://tr.wikisource.org/wiki/Velinimet"),
    ("Nâdan", "https://tr.wikisource.org/wiki/N%C3%A2dan"),
    ("Tos", "https://tr.wikisource.org/wiki/Tos"),
)
TOPICS = {
    "en": (
        "Write an original fictional scene: a traveler takes shelter from rain near "
        "a market and decides whether to keep walking. Aim for 180-260 words. "
        "This is fiction; do not claim a real firsthand visit.",
        "Write an original fictional scene: an old letter is found inside a borrowed "
        "book, but its message is ambiguous. Aim for 180-260 words. "
        "This is fiction; do not invent verifiable real-world facts.",
    ),
    "tr": (
        "Özgün bir kurmaca sahne yazın: yağmurdan bir çarşı yakınında korunan "
        "yolcu yürümeye devam edip etmeyeceğine karar veriyor. 180-260 kelime "
        "hedefleyin. Gerçekte yaşanmış bir ziyaret iddia etmeyin.",
        "Özgün bir kurmaca sahne yazın: ödünç bir kitabın içinde eski bir mektup "
        "bulunuyor ama mesajı belirsiz. 180-260 kelime hedefleyin. "
        "Gerçek dünyaya ilişkin doğrulanamaz olgular uydurmayın.",
    ),
}


@dataclass(frozen=True)
class Case:
    identifier: str
    author: str
    language: str
    training: tuple[str, ...]
    held_out: str
    sources: tuple[dict, ...]


def _excerpt(text: str, words: int = 350) -> str:
    """Keep the first fixed number of whitespace tokens and paragraph rhythm."""
    spans = list(re.finditer(r"\S+", text))
    if len(spans) < words:
        raise ValueError("Public-domain writing sample is unexpectedly short")
    return text[:spans[words - 1].end()].strip()


def _wikisource_text(html: str, expected_title: str) -> str:
    """Extract story prose, excluding navigation and editorial site furniture."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.select_one("#firstHeading")
    if heading is None or heading.get_text(" ", strip=True) != expected_title:
        raise ValueError(f"Unexpected Wikisource work identity: {expected_title}")
    root = soup.select_one("#mw-content-text .mw-parser-output")
    if root is None:
        raise ValueError(f"Missing prose body in Wikisource work: {expected_title}")
    for node in root.select("table, script, style, nav, aside, .mw-editsection, .noprint, .metadata"):
        node.decompose()
    paragraphs = [node.get_text(" ", strip=True) for node in root.select("p")]
    prose = "\n\n".join(p for p in paragraphs if p)
    if len(prose.split()) < 350:
        raise ValueError(f"Too little usable work text: {expected_title}")
    return prose


def _fixed_source(url: str) -> tuple[str, str]:
    """Fetch only allowlisted benchmark pages and retain the exact source hash."""
    if url not in dict(TURKISH_STORIES).values():
        raise ValueError("Unapproved benchmark source")
    response = requests.get(url, timeout=(10, 45), headers={
        "User-Agent": "Pennovia-Quality-Benchmark/0.1 (public literary source)",
    })
    response.raise_for_status()
    raw = response.content
    if not raw or len(raw) > 2_000_000:
        raise ValueError("Unusable or oversized benchmark source")
    return raw.decode(response.encoding or "utf-8", errors="replace"), hashlib.sha256(raw).hexdigest()


def load_cases() -> list[Case]:
    english, english_hash, english_url = _download_source()
    chapters = select_chapters(english)
    twain = Case(
        "twain-en", "Mark Twain", "en",
        tuple(chapters[name] for name in ("I", "II", "IV")), chapters["III"],
        ({"url": english_url, "catalog": "https://www.gutenberg.org/ebooks/3176",
          "sha256": english_hash,
          "license": "Public domain (US); Project Gutenberg #3176",
          "train": ["I", "II", "IV"], "holdout": "III"},),
    )
    stories = []
    for title, url in TURKISH_STORIES:
        html, sha = _fixed_source(url)
        extracted = _wikisource_text(html, title)
        stories.append((title, url, _excerpt(extracted), sha))
    seyfettin = Case(
        "seyfettin-tr", "Ömer Seyfettin", "tr",
        tuple(item[2] for item in stories[:2]), stories[2][2],
        tuple({"url": item[1], "sha256": item[3],
               "license": "Public-domain original; Wikisource transcription (CC BY-SA)",
               "role": "holdout" if i == 2 else "train"}
              for i, item in enumerate(stories)),
    )
    for case in (twain, seyfettin):
        if case.held_out in "\n".join(case.training):
            raise RuntimeError(f"Training/holdout leakage in {case.identifier}")
        if any(len(doc.split()) < 300 for doc in case.training):
            raise RuntimeError(f"Insufficient training sample in {case.identifier}")
    return [twain, seyfettin]


def _neutral(topic: str, language: str) -> str:
    """Match the content-type structure, topic and model, without style metrics."""
    ctype = get_type("story")
    structure = "; ".join(ctype["structure"])
    system = (
        f"Write an original fictional {ctype['label'].lower()} in "
        f"{'Turkish' if language == 'tr' else 'English'}. "
        f"Use this structure: {structure}. "
        "Write only the text, with natural paragraphs. Do not invent quotes "
        "from real people, concrete dates, or verified firsthand encounters. "
        "Follow the user's 180-260 word target rather than padding."
    )
    with requests.Session() as session:
        session.trust_env = False
        response = session.post(
            f"{OLLAMA}/api/chat", json={
                "model": MODEL, "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": topic},
                ], "stream": False,
                "options": {"num_predict": MAX_TOKENS},
            }, timeout=300,
        )
        response.raise_for_status()
        return _require_draft(response.json()["message"]["content"], "Neutral Ollama")


def _fingerprint(text: str, language: str) -> dict[str, float]:
    p = analyze([text], language=language)
    return {key: float(getattr(p, key)) for key in (
        "avg_sentence_words", "short_sentence_rate", "long_sentence_rate",
        "first_person_rate", "question_rate", "negative_rate",
        "avg_paragraph_sentences", "semicolon_rate",
    )}


SCALES = {
    "avg_sentence_words": 12.0,
    "short_sentence_rate": 0.30,
    "long_sentence_rate": 0.30,
    "first_person_rate": 0.35,
    "question_rate": 0.25,
    "negative_rate": 0.25,
    "avg_paragraph_sentences": 4.0,
    "semicolon_rate": 8.0,
}


def heldout_distance(draft: str, held_out: str, language: str) -> float:
    """Independent descriptive distance, *not* Pennovia's own audit or a human judgment."""
    target, actual = _fingerprint(held_out, language), _fingerprint(draft, language)
    terms = [min(1.0, abs(actual[key] - target[key]) / scale)
             for key, scale in SCALES.items()]
    return round(sum(terms) / len(terms), 4)


def copied_long_span(draft: str, training: tuple[str, ...], *, size: int = 12) -> bool:
    """Detect verbatim long spans that could mean memorized rather than imitated prose."""
    tokens = re.findall(r"\b\w+\b", draft.casefold())
    if len(tokens) < size:
        return False
    source = set()
    for document in training:
        items = re.findall(r"\b\w+\b", document.casefold())
        source.update(tuple(items[i:i + size]) for i in range(len(items) - size + 1))
    return any(tuple(tokens[i:i + size]) in source for i in range(len(tokens) - size + 1))


def evaluate_pair(styled: str, neutral: str, case: Case) -> dict:
    """Record diagnostics for every pair; never count a non-comparable win."""
    styled_words, neutral_words = len(styled.split()), len(neutral.split())
    if not styled_words or not neutral_words:
        raise ValueError("Empty model output")
    ratio = styled_words / neutral_words
    comparable = 0.6 <= ratio <= 1.67
    styled_language, neutral_language = _detect_language(styled), _detect_language(neutral)
    styled_distance = heldout_distance(styled, case.held_out, case.language)
    neutral_distance = heldout_distance(neutral, case.held_out, case.language)
    styled_copy = copied_long_span(styled, case.training)
    neutral_copy = copied_long_span(neutral, case.training)
    styled_repeated, _, styled_tokens = repeated_fourgram_share(styled)
    neutral_repeated, _, neutral_tokens = repeated_fourgram_share(neutral)

    reasons = []
    if not comparable:
        reasons.append("incomparable_lengths")
    if min(styled_words, neutral_words) < 120:
        reasons.append("insufficient_output_length")
    if styled_language != case.language or neutral_language != case.language:
        reasons.append("unverified_output_language")
    if styled_copy or neutral_copy:
        reasons.append("verbatim_source_copy")
    if ((styled_tokens >= 120 and styled_repeated >= 0.45)
            or (neutral_tokens >= 120 and neutral_repeated >= 0.45)):
        reasons.append("severe_text_repetition")

    eligible = not reasons
    return {
        "styled_words": styled_words, "neutral_words": neutral_words,
        "length_ratio": round(ratio, 3), "length_comparable": comparable,
        "styled_language": styled_language, "neutral_language": neutral_language,
        "styled_heldout_distance": styled_distance,
        "neutral_heldout_distance": neutral_distance,
        "styled_better_on_descriptive_distance": (
            styled_distance < neutral_distance if eligible else None
        ),
        "styled_12gram_source_copy": styled_copy,
        "neutral_12gram_source_copy": neutral_copy,
        "styled_repeated_fourgram_share": styled_repeated,
        "neutral_repeated_fourgram_share": neutral_repeated,
        "eligible_for_style_comparison": eligible,
        "invalid_reasons": reasons,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = load_cases()
    if args.source_only:
        print(json.dumps({"cases": [case.identifier for case in cases],
                          "languages": [case.language for case in cases],
                          "source_verified": True}))
        return
    digest = _model_digest()
    report = {
        "status": "paired_exploratory_model_executed",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "local Ollama", "model": MODEL, "digest": digest,
        "max_tokens_per_arm": MAX_TOKENS,
        "method": "One model, one content type, matched topics, 2 cases x 2 topics x 2 arms. "
                  "Held-out observable stylistic distance; no blind human review performed.",
        "not_product_acceptance": True,
        "cases": [], "pairs": [],
    }
    (args.output / "blinded").mkdir(exist_ok=True)
    key = []
    reviewer_rows = []
    for case in cases:
        report["cases"].append({
            "id": case.identifier, "author": case.author, "language": case.language,
            "source_manifest": case.sources,
            "training_words": [len(text.split()) for text in case.training],
            "holdout_words": len(case.held_out.split()),
            "holdout_sha256": hashlib.sha256(case.held_out.encode()).hexdigest(),
        })
        profile = analyze(case.training, author_name=case.author, language=case.language)
        for index, topic in enumerate(TOPICS[case.language], 1):
            paired_id = f"{case.identifier}-{index}"
            styled = generate(profile, "story", topic, backend="ollama",
                              model=MODEL, max_tokens=MAX_TOKENS)
            neutral = _neutral(topic, case.language)
            metrics = evaluate_pair(styled, neutral, case)
            order = ["styled", "neutral"]
            random.Random(int(hashlib.sha256(paired_id.encode()).hexdigest(), 16)).shuffle(order)
            files = {}
            for label, arm in zip(("A", "B"), order, strict=True):
                filename = f"blinded/{paired_id}-{label}.txt"
                (args.output / filename).write_text(
                    styled if arm == "styled" else neutral, encoding="utf-8"
                )
                files[label] = filename
                key.append({"pair_id": paired_id, "arm": label, "condition": arm})
            report["pairs"].append({
                "id": paired_id, "language": case.language, "topic": topic,
                "blinded": files, "diagnostics": metrics,
            })
            reviewer_rows.append({
                "pair_id": paired_id, "language": case.language,
                "file_A": files["A"], "file_B": files["B"],
                "voice_resemblance_A_1_to_5": "",
                "voice_resemblance_B_1_to_5": "",
                "readability_A_1_to_5": "", "readability_B_1_to_5": "",
                "unsupported_claims_A": "", "unsupported_claims_B": "",
                "reviewer_id": "", "editorial_notes": "",
            })
    (args.output / "answer-key.json").write_text(
        json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output / "blind-review.csv").open("w", newline="", encoding="utf-8") as dest:
        writer = csv.DictWriter(dest, fieldnames=list(reviewer_rows[0]))
        writer.writeheader()
        writer.writerows(reviewer_rows)
    (args.output / "evidence.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": report["status"], "model": MODEL,
        "cases": [case.identifier for case in cases],
        "pairs": [{"id": pair["id"], **pair["diagnostics"]}
                  for pair in report["pairs"]],
        "blind_human_review": "not_performed",
        "product_acceptance": "not_established",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
