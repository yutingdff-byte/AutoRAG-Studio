from facts.chunker import build_fact_chunks


def _plain_bodies(chunks):
    return "\n".join(
        "\n".join(chunk.source_blocks)
        for chunk in chunks
    )


def test_small_document_keeps_single_chunk():
    chunks = build_fact_chunks("哈弗H6\n\n车长4703毫米。", target_chars=1000, max_chars=1200)

    assert len(chunks) == 1
    assert "哈弗H6" in chunks[0].text
    assert "车长4703毫米" in chunks[0].text


def test_chunker_does_not_split_normal_paragraph():
    paragraph = "2026年6月1日至6月30日期间购买哈弗H6L，可享现金优惠14000元，叠加置换补贴。"
    material = f"哈弗H6L\n\n{paragraph}\n\n金融权益\n\n支持3年0息。"

    chunks = build_fact_chunks(material, target_chars=45, max_chars=200)

    assert any(paragraph in chunk.text for chunk in chunks)


def test_heading_context_is_inherited():
    material = "猛龙PLUS\n\n现金权益\n\n现金礼最高14000元。\n\n金融权益\n\n首付低至20%。"

    chunks = build_fact_chunks(material, target_chars=28, max_chars=200)

    assert len(chunks) >= 2
    assert any("【上下文" in chunk.text for chunk in chunks[1:])
    assert any("猛龙PLUS" in chunk.context_header for chunk in chunks[1:])


def test_image_block_kept_whole():
    image_block = "【内嵌图片 1/1：policy_image_001.png】\n" + ("图片识别内容" * 30)
    material = f"【Word正文】\n\n少量文字\n\n{image_block}\n\n结束"

    chunks = build_fact_chunks(material, target_chars=80, max_chars=1000)

    assert any(image_block in chunk.text for chunk in chunks)


def test_oversized_block_is_safely_split_by_lines():
    block = "\n".join(
        f"政策条目{i}：现金礼{i}000元。"
        for i in range(300)
    )
    chunks = build_fact_chunks(block, target_chars=100, max_chars=300)

    assert len(chunks) > 1
    assert all(chunk.oversized is False for chunk in chunks)
    assert all(len(chunk.text) <= 300 for chunk in chunks)
    merged = _plain_bodies(chunks)
    assert "政策条目0" in merged
    assert "政策条目299" in merged


def test_oversized_json_records_stay_whole():
    records = []
    for i in range(80):
        records.append(
            "\n".join(
                [
                    "{",
                    f'"车系": "哈弗H{i}",',
                    f'"问题": "哈弗H{i}金融政策",',
                    f'"答案": "至高{i}000元权益"',
                    "}",
                ]
            )
        )
    block = "\n".join(records)
    chunks = build_fact_chunks(block, target_chars=500, max_chars=700)

    assert len(chunks) > 1
    assert all(chunk.oversized is False for chunk in chunks)
    assert all(len(chunk.text) <= 700 for chunk in chunks)
    for record in records:
        assert record in _plain_bodies(chunks)


def test_long_single_unit_falls_back_to_sentence_boundaries():
    unit = "车型A政策：" + ("现金优惠1000元；" * 900)
    chunks = build_fact_chunks(unit, target_chars=1000, max_chars=1200)

    assert len(chunks) > 1
    assert all(chunk.oversized is False for chunk in chunks)
    assert all(len(chunk.text) <= 1200 for chunk in chunks)


def test_oversized_model_context_is_inherited():
    material = "哈弗猛龙PLUS\n" + "\n".join(
        f"权益条目{i}：现金优惠{i}000元。"
        for i in range(200)
    )
    chunks = build_fact_chunks(material, target_chars=300, max_chars=500)

    assert len(chunks) > 1
    assert any("哈弗猛龙PLUS" in chunk.context_header for chunk in chunks[1:])


def test_chunk_order_is_stable():
    material = "标题\n\n第一段内容。\n\n第二段内容。\n\n第三段内容。"

    chunks = build_fact_chunks(material, target_chars=20, max_chars=100)

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert "第一段" in chunks[0].text
