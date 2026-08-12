from facts.chunker import build_fact_chunks


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


def test_oversized_block_is_marked_but_not_split():
    block = "超大政策段落" * 200
    chunks = build_fact_chunks(block, target_chars=100, max_chars=300)

    assert len(chunks) == 1
    assert chunks[0].oversized is True
    assert block in chunks[0].text


def test_chunk_order_is_stable():
    material = "标题\n\n第一段内容。\n\n第二段内容。\n\n第三段内容。"

    chunks = build_fact_chunks(material, target_chars=20, max_chars=100)

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert "第一段" in chunks[0].text
