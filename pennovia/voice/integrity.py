"""Conservative structural warnings for visibly degenerate model output.

Not a fluency or originality classifier. Works across English and Turkish
without depending on particular prohibited words.
"""
import re
from collections import Counter


def repeated_fourgram_share(text: str) -> tuple[float, int, int]:
    """Return (share of four-grams repeated 3+ times, max occurrence, token count).

    A high share indicates repeated *word sequences*, not just recurring
    vocabulary or names. Require a substantial sample before using the metric
    for a blocking review decision.
    """
    words = re.findall(r"[^\W\d_]+", text.casefold().replace("i\u0307", "i"), re.UNICODE)
    if len(words) < 4:
        return 0.0, 0, len(words)
    spans = Counter(zip(words[:-3], words[1:-2], words[2:-1], words[3:], strict=True))
    repeated = sum(count for count in spans.values() if count >= 3)
    return round(repeated / (len(words) - 3), 3), max(spans.values()), len(words)
