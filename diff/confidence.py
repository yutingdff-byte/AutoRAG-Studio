"""Rule confidence constants for the diff engine.

Confidence values are rule scores, not statistical probabilities.
"""

EXACT_MATCH = 0.98
NORMALIZED_QUESTION_MATCH = 0.95
STRUCTURED_MATCH = 0.82
REVIEW_CANDIDATE = 0.68
NO_MATCH = 0.0

UNCHANGED = 0.96
FORMAT_ONLY_CHANGE = 0.94
UPDATED = 0.9
REVIEW_REQUIRED = 0.62


def combine(match_confidence: float, change_confidence: float) -> float:
    if match_confidence <= 0 or change_confidence <= 0:
        return 0.0
    return round(min(match_confidence, change_confidence), 4)
