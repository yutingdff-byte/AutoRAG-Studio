from diff.normalizer import normalize_answer_text, normalize_question_text


def test_question_normalizer_handles_spacing_and_punctuation():
    assert normalize_question_text(" 阿维塔 06 的价格是多少？ ") == normalize_question_text("阿维塔06价格多少")


def test_answer_normalizer_keeps_equal_yuan_formats_equal():
    assert normalize_answer_text("249,800元") == normalize_answer_text("249800 元")


def test_answer_normalizer_does_not_merge_different_prices():
    assert normalize_answer_text("24.98万元") != normalize_answer_text("23.98万元")
