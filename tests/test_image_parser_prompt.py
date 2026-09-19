from parser.image_parser import IMAGE_PARSE_PROMPT


def test_image_prompt_requires_exact_cargo_capacity_binding():
    assert "后备箱" in IMAGE_PARSE_PROMPT
    assert "行李箱" in IMAGE_PARSE_PROMPT
    assert "储物空间" in IMAGE_PARSE_PROMPT
    assert "容积" in IMAGE_PARSE_PROMPT
    assert "参数名称-数值/范围-单位-条件" in IMAGE_PARSE_PROMPT
    assert "不得改写成单一容积" in IMAGE_PARSE_PROMPT
    assert "未放倒容积" in IMAGE_PARSE_PROMPT
    assert "自行估算值" in IMAGE_PARSE_PROMPT


def test_image_prompt_requires_uncertain_when_cargo_numbers_are_unclear():
    assert "座椅放倒" in IMAGE_PARSE_PROMPT
    assert "数字说明不清晰" in IMAGE_PARSE_PROMPT
    assert "【图片内容无法确认】" in IMAGE_PARSE_PROMPT
    assert "不得根据图片画面" in IMAGE_PARSE_PROMPT
    assert "相邻配置表" in IMAGE_PARSE_PROMPT
