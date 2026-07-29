from diff.models import ChangeType, DiffRunResult, DetectedUpdateScope, MatchMethod, ReviewReason


def test_diff_enums_are_stable_strings():
    assert ChangeType.ADDED.value == "ADDED"
    assert ChangeType.UPDATED.value == "UPDATED"
    assert ChangeType.UNCHANGED.value == "UNCHANGED"
    assert ChangeType.REVIEW_REQUIRED.value == "REVIEW_REQUIRED"
    assert MatchMethod.STRUCTURED.value == "STRUCTURED"
    assert ReviewReason.POSSIBLE_DEPRECATED.value == "POSSIBLE_DEPRECATED"


def test_diff_run_result_defaults():
    result = DiffRunResult(
        results=[],
        detected_scope=DetectedUpdateScope(),
    )

    assert result.total_count == 0
    assert result.added_count == 0
    assert result.detected_scope.models == []
