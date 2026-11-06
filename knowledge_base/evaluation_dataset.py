"""Reproducible evaluation dataset for AccessBridge AI.

Each case is a representative scholarship question with the expected outcome:
- which official source(s) should match
- what the verification status should be (at minimum, partial)
- whether evidence references should be produced
- what language(s) should be supported

The evaluation test (tests/integration/test_evaluation.py) runs each case
through the real workflow and checks the actual output against these
expectations. Results are reported in BUILD_STATUS.md.

Never fabricate benchmarks: these expectations are the minimum bar the system
must clear to be considered reliable for a student.
"""

EVALUATION_CASES = [
    {
        "id": "eval-aicte-pragati",
        "question": "What are the eligibility requirements and documents for the AICTE Pragati scholarship for girls?",
        "language": "en",
        "expected_source_key": "aicte-pragati",
        "expected_verification": "partial",   # offline → partial (honest)
        "expected_min_eligibility": 2,
        "expected_min_documents": 2,
        "expected_evidence": True,
        "expected_languages": ["en", "hi", "pa"],
    },
    {
        "id": "eval-aicte-saksham",
        "question": "Tell me about the AICTE Saksham scholarship for specially-abled students.",
        "language": "en",
        "expected_source_key": "aicte-saksham",
        "expected_verification": "partial",
        "expected_min_eligibility": 1,
        "expected_min_documents": 1,
        "expected_evidence": True,
        "expected_languages": ["en", "hi", "pa"],
    },
    {
        "id": "eval-chevening",
        "question": "How do I apply for the Chevening scholarship for Indian students?",
        "language": "en",
        "expected_source_key": "chevening",
        "expected_verification": "partial",
        "expected_min_eligibility": 0,   # bundled excerpt may be sparse
        "expected_min_documents": 0,
        "expected_evidence": True,       # evidence still produced for found claims
        "expected_languages": ["en"],
    },
    {
        "id": "eval-unknown",
        "question": "What is the airspeed of an unladen swallow?",
        "language": "en",
        "expected_source_key": None,     # no source should match
        "expected_verification": "unverified",
        "expected_min_eligibility": 0,
        "expected_min_documents": 0,
        "expected_evidence": False,
        "expected_languages": ["en"],
    },
    {
        "id": "eval-hindi-script",
        "question": "प्रगति छात्रवृत्ति के बारे में बताओ",   # Devanagari → language=hi
        "language": "hi",
        "expected_source_key": "aicte-pragati",
        "expected_verification": "partial",
        "expected_min_eligibility": 1,
        "expected_min_documents": 1,
        "expected_evidence": True,
        "expected_languages": ["hi"],
    },
]
