"""Curated, official knowledge base for AccessBridge AI.

Each entry is a real, publicly available scholarship / educational opportunity
page. The retriever prefers these official sources and only falls back to a
generic web fetch if no curated entry matches.

Adding a new source here is the supported way to extend AccessBridge's
coverage — the Research Agent will cite it with the real URL and retrieval
timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OfficialSource:
    key: str
    name: str               # human-readable name
    publisher: str          # official body
    url: str                # canonical URL the agent retrieves
    region: str             # IN | UK | US | EU | GLOBAL ...
    tags: tuple[str, ...]   # keywords that help match a student question
    official: bool = True


SOURCES: tuple[OfficialSource, ...] = (
    OfficialSource(
        key="aicte-pragati",
        name="AICTE Pragati Scholarship for Girls",
        publisher="All India Council for Technical Education (AICTE), Govt. of India",
        url="https://www.aicte-india.org/sites/default/files/policy/Pragati.pdf",
        region="IN",
        tags=("pragati", "aicte", "girl", "female", "engineering", "diploma", "scholarship", "india",
              "प्रगति", "छात्रवृत्ति", "ਪ੍ਰਗਤੀ"),  # bilingual: Hindi + Punjabi
    ),
    OfficialSource(
        key="aicte-saksham",
        name="AICTE Saksham Scholarship for Specially-Abled Students",
        publisher="All India Council for Technical Education (AICTE), Govt. of India",
        url="https://www.aicte-india.org/sites/default/files/policy/Saksham.pdf",
        region="IN",
        tags=("saksham", "aicte", "disability", "specially-abled", "scholarship", "india",
              "सक्षम", "ਸਕਸ਼ਮ"),
    ),
    OfficialSource(
        key="national-scholarship-portal",
        name="National Scholarship Portal (NSP)",
        publisher="Government of India, Ministry of Education",
        url="https://scholarships.gov.in/",
        region="IN",
        tags=("nsp", "national scholarship", "india", "portal", "pre-matric", "post-matric", "central", "state"),
    ),
    OfficialSource(
        key="ugc-isir",
        name="UGC ISHAN UDAY Special Scholarship for North Eastern Region",
        publisher="University Grants Commission (UGC), Govt. of India",
        url="https://www.ugc.gov.in/scholarshipschemes",
        region="IN",
        tags=("ugc", "ishan uday", "north east", "scholarship", "india", "college", "university"),
    ),
    OfficialSource(
        key="post-matric-sc",
        name="Post-Matric Scholarship for SC Students",
        publisher="Ministry of Social Justice & Empowerment, Govt. of India",
        url="https://socialjustice.gov.in/scholarship-schemes",
        region="IN",
        tags=("post-matric", "sc", "scheduled caste", "scholarship", "india", "social justice"),
    ),
    OfficialSource(
        key="post-matric-obc",
        name="Post-Matric Scholarship for OBC Students",
        publisher="Ministry of Social Justice & Empowerment, Govt. of India",
        url="https://socialjustice.gov.in/scholarship-schemes",
        region="IN",
        tags=("post-matric", "obc", "backward class", "scholarship", "india"),
    ),
    OfficialSource(
        key="chevening",
        name="Chevening Scholarships (UK, for Indian students)",
        publisher="UK Government / FCDO",
        url="https://www.chevening.org/scholarships/",
        region="UK",
        tags=("chevening", "uk", "masters", "international", "india", "scholarship"),
    ),
    OfficialSource(
        key="commonwealth",
        name="Commonwealth Scholarships (UK)",
        publisher="Commonwealth Scholarship Commission",
        url="https://cscuk.fcdo.gov.uk/scholarships/",
        region="UK",
        tags=("commonwealth", "uk", "masters", "phd", "international", "scholarship"),
    ),
    OfficialSource(
        key="fulbright",
        name="Fulbright-Nehru Master's Fellowships (US, for Indians)",
        publisher="USIEF / Fulbright",
        url="https://www.usief.org.in/Fellowships-for-Indian-Citizens.aspx",
        region="US",
        tags=("fulbright", "nehru", "us", "masters", "international", "india", "scholarship"),
    ),
    OfficialSource(
        key="swami-vivekananda",
        name="Swami Vivekananda Merit-cum-Means Scholarship (West Bengal)",
        publisher="Government of West Bengal",
        url="https://svmcm.wbhed.gov.in/",
        region="IN-WB",
        tags=("swami vivekananda", "west bengal", "merit", "means", "scholarship", "india"),
    ),
)


import re as _re


def match(query: str) -> list[OfficialSource]:
    """Return official sources whose tags appear in the query, best match first.

    Uses word-boundary matching so short tags like "sc" do not match inside
    "scholarship" — a genuine bug that would rank the wrong source first.
    """
    q = (query or "").lower()
    if not q:
        return []
    scored: list[tuple[int, OfficialSource]] = []
    for s in SOURCES:
        score = 0
        for t in s.tags:
            # Word-boundary match via lookarounds — handles Unicode scripts
            # (Devanagari, Gurmukhi) correctly, unlike \b which breaks on
            # combining marks like the virama (halant).
            if _re.search(r"(?<!\w)" + _re.escape(t) + r"(?!\w)", q):
                score += 1
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored]
