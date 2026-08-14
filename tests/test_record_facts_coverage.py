from evaluation.record_facts_coverage import (
    evaluate_record_coverage,
    extract_price_values,
    map_facts_to_records,
)


def _record(index, series, vehicle, trim, price):
    return {
        "record_index": index,
        "series": series,
        "vehicle_name": vehicle,
        "trim": trim,
        "price": price,
        "cash": "\u73b0\u91d1\u4f18\u60e0",
        "trade_in": "\u7f6e\u6362\u8865\u8d34",
        "finance": "\u91d1\u878d\u514d\u606f",
        "benefit": "\u6743\u76ca",
        "activity": "\u6d3b\u52a8",
    }


def test_price_normalizes_yuan_and_wan_units():
    assert 199800 in extract_price_values("199800")
    assert 199800 in extract_price_values("19.98\u4e07")
    assert 199800 in extract_price_values("19.98\u4e07\u5143")


def test_record_id_batch_context_can_recover_single_record_price():
    records = [_record(28, "\u5411\u5f80E8 PHEV", "\u5411\u5f80E8 Max\u7248", "\u5411\u5f80E8 \u4e2d\u914d", "199800")]
    facts = [
        {
            "fact_id": "F001",
            "category": "\u4ef7\u683c",
            "content": "\u5382\u5546\u6307\u5bfc\u4ef7\u662f19.98\u4e07\u5143",
        }
    ]

    mapping = map_facts_to_records(records, facts, candidate_record_ids=["VR028"])
    coverage = evaluate_record_coverage(records, mapping)

    assert coverage["price"]["covered"] == 1
    assert mapping["VR028"] == facts


def test_record_id_batch_context_can_recover_unique_price_in_batch():
    records = [
        _record(10, "\u5411\u5f80S9\u4e7e\u5d11", "Ultra\uff08\u9009\u88c56\u5ea7\uff09", "\u5411\u5f80S9-\u9ad8\u914d", "259900"),
        _record(11, "\u5411\u5f80M8", "25\u6b3e\u5411\u5f80M8", "\u5411\u5f80M8", "329900"),
    ]
    facts = [
        {
            "fact_id": "F001",
            "category": "\u4ef7\u683c",
            "content": "\u5382\u5546\u6307\u5bfc\u4ef7\u4e3a259900\u5143\u3002",
        }
    ]

    mapping = map_facts_to_records(records, facts, candidate_record_ids=["VR010", "VR011"])
    coverage = evaluate_record_coverage(records, mapping)

    assert mapping["VR010"] == facts
    assert mapping["VR011"] == []
    assert coverage["price"]["covered"] == 1


def test_duplicate_price_in_batch_is_not_guessed():
    records = [
        _record(1, "\u4f20\u797aGS3", "\u52b2\u667a\u7248", "GS3-\u9ad8\u914d", "99800"),
        _record(2, "26\u6b3e\u4f20\u797aM6", "\u7cbe\u82f1\u7248", "M6-\u4f4e\u914d", "99800"),
    ]
    facts = [
        {
            "fact_id": "F001",
            "category": "\u4ef7\u683c",
            "content": "\u5382\u5546\u6307\u5bfc\u4ef7\u4e3a99800\u5143\u3002",
        }
    ]

    mapping = map_facts_to_records(records, facts, candidate_record_ids=["VR001", "VR002"])

    assert mapping["VR001"] == []
    assert mapping["VR002"] == []


def test_missing_price_is_not_falsely_completed():
    records = [_record(28, "\u5411\u5f80E8 PHEV", "\u5411\u5f80E8 Max\u7248", "\u5411\u5f80E8 \u4e2d\u914d", "199800")]
    facts = [
        {
            "fact_id": "F001",
            "category": "\u914d\u7f6e",
            "content": "\u5411\u5f80E8 Max\u7248\u652f\u6301\u8212\u9002\u5ea7\u8231",
        }
    ]

    mapping = map_facts_to_records(records, facts, candidate_record_ids=["VR028"])
    coverage = evaluate_record_coverage(records, mapping)

    assert coverage["vehicle"]["covered"] == 1
    assert coverage["price"]["covered"] == 0


def test_similar_model_names_do_not_cross_record_without_identity_match():
    records = [
        _record(40, "\u4f20\u797aGS4", "\u4f20\u797aGS4 Pro\u7248", "GS4-\u4e2d\u914d", "92800"),
        _record(41, "\u4f20\u797aGS4", "\u4f20\u797aGS4 Max\u7248", "GS4-\u9ad8\u914d", "100800"),
    ]
    facts = [
        {
            "fact_id": "F001",
            "category": "\u4ef7\u683c",
            "content": "\u4f20\u797aGS4 Max\u7248\u7684\u6307\u5bfc\u4ef7\u4e3a10.08\u4e07\u5143",
        }
    ]

    mapping = map_facts_to_records(records, facts)
    coverage = evaluate_record_coverage(records, mapping)

    assert mapping["VR040"] == []
    assert mapping["VR041"] == facts
    assert coverage["price"]["covered"] == 1


def test_mapping_does_not_modify_fact_schema():
    records = [_record(1, "\u4f20\u797aGS3", "2026\u6b3e \u52b2\u4eab\u7248", "GS3-\u4e2d\u914d", "89800")]
    fact = {
        "fact_id": "F001",
        "category": "\u4ef7\u683c",
        "content": "2026\u6b3e \u52b2\u4eab\u7248\u6307\u5bfc\u4ef78.98\u4e07\u5143",
    }

    map_facts_to_records(records, [fact], candidate_record_ids=["VR001"])

    assert set(fact) == {"fact_id", "category", "content"}
