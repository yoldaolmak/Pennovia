"""Content type registry — structural templates per genre."""

CONTENT_TYPES = {
    "travel_blog": {
        "label": "Travel Blog",
        "structure": [
            "Opening — a concrete sense of place or relevant question",
            "Why this place?",
            "What to see and do",
            "Practical notes",
            "Closing note / recommendation",
        ],
        "tone": "follow the author's observed point of view; clear and practical",
        "length": "800-1500 words",
    },
    "travel_guide": {
        "label": "Travel Guide",
        "structure": [
            "Overview",
            "How to get there",
            "When to go",
            "What to see",
            "Where to stay and eat",
            "Practical information",
        ],
        "tone": "authoritative, advisory, information-first",
        "length": "1500-3000 words",
    },
    "magazine": {
        "label": "Magazine Article",
        "structure": [
            "Engaging opening grounded in the supplied material",
            "Subject / thesis",
            "In-depth narrative",
            "Attributable perspectives (only if supplied)",
            "Closing",
        ],
        "tone": "narrative, layered, draws the reader in",
        "length": "1200-2500 words",
    },
    "news": {
        "label": "News",
        "structure": [
            "Lead (who/what/when/where/why/how)",
            "Context",
            "Details",
            "Attributable sources (only if supplied)",
            "Background",
        ],
        "tone": "objective, plain, direct",
        "length": "400-800 words",
    },
    "story": {
        "label": "Story",
        "structure": [
            "Setting the scene",
            "Character / conflict",
            "Development",
            "Turning point",
            "Resolution",
        ],
        "tone": "narrative, vivid, emotional",
        "length": "1000-3000 words",
    },
    "column": {
        "label": "Column",
        "structure": [
            "Trigger event / observation",
            "The writer's take",
            "Argument / example",
            "Conclusion / call to action",
        ],
        "tone": "opinionated, provocative, original",
        "length": "500-900 words",
    },
}


def list_types() -> dict:
    return {k: v["label"] for k, v in CONTENT_TYPES.items()}


def get(content_type: str) -> dict:
    return CONTENT_TYPES.get(content_type, CONTENT_TYPES["travel_blog"])


# Author-facing presentation terms for Turkish writing. These remain part of
# the *same* content-type registry, not a second generation engine. Language
# never alters evidence requirements or the author's editorial authority.
_TR_PRESENTATION = {
    "travel_blog": {
        "label": "Gezi Yazısı",
        "structure": [
            "Somut bir giriş veya yerinde bir soru",
            "Bu yer neden önemli?",
            "Görülecek ve yapılacaklar",
            "Karar vermeyi kolaylaştıran pratik bilgiler",
            "Kısa kapanış değerlendirmesi",
        ],
        "tone": "Yazarın gözlenen anlatımını izle; açık, somut ve yararlı ol",
        "length": "800-1500 kelime",
    },
    "travel_guide": {
        "label": "Gezi Rehberi",
        "structure": [
            "Genel bakış",
            "Ulaşım (yalnızca kanıtlı bilgi varsa)",
            "Ne zaman gidilir? (yalnızca kanıtlı bilgi varsa)",
            "Görülecek yerler (yalnızca kanıtlı bilgi varsa)",
            "Konaklama ve yemek (yalnızca kanıtlı bilgi varsa)",
            "Pratik bilgiler",
        ],
        "tone": "Açık, yönlendirici ve bilgi öncelikli; doğrulanmamış ayrıntı uydurma",
        "length": "1500-3000 kelime",
    },
    "magazine": {
        "label": "Dergi Yazısı",
        "structure": [
            "Verilen malzemeye dayanan ilgi çekici giriş",
            "Konu veya temel fikir",
            "Ayrıntılı anlatı",
            "Yalnızca sağlanmışsa atıflı görüşler",
            "Kapanış",
        ],
        "tone": "Anlatı ağırlıklı, katmanlı ve yazarın gözlenen sesine bağlı",
        "length": "1200-2500 kelime",
    },
    "news": {
        "label": "Haber",
        "structure": [
            "Kim, ne, nerede, ne zaman, neden, nasıl?",
            "Bağlam",
            "Ayrıntılar",
            "Yalnızca sağlanmışsa atıflı kaynaklar",
            "Arka plan",
        ],
        "tone": "Açık, doğrudan, tarafsız ve kaynakla sınırlı",
        "length": "400-800 kelime",
    },
    "story": {
        "label": "Öykü",
        "structure": [
            "Sahnenin kurulması",
            "Kişi veya çatışma",
            "Gelişme",
            "Dönüm noktası",
            "Sonuç",
        ],
        "tone": "Yazarın gözlenen anlatı ritmini izle; sahici, doğal ve akıcı ol",
        "length": "1000-3000 kelime",
    },
    "column": {
        "label": "Köşe Yazısı",
        "structure": [
            "Çıkış noktası veya gözlem",
            "Yazarın değerlendirmesi",
            "Gerekçe veya örnek",
            "Sonuç veya çağrı",
        ],
        "tone": "Yazarın gözlenen tavrına bağlı, somut ve özgün",
        "length": "500-900 kelime",
    },
}


def get_localized(content_type: str, language: str) -> dict:
    """Return a new, language-appropriate view without mutating the registry."""
    key = content_type if content_type in CONTENT_TYPES else "travel_blog"
    base = get(key)
    return {**base, **_TR_PRESENTATION[key]} if language == "tr" else base
