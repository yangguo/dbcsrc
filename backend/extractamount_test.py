"""Offline tests for the amount extraction contract. No network, no LLM calls."""

import extractamount


def fake_llm(entity_map):
    """Stand-in for nlp_input. Keys match by substring so cut text still hits."""

    def call(schema, chunks):
        key = schema[0]
        entities = []
        for marker, found in entity_map.items():
            if marker in chunks[0]:
                entities = found
                break
        return [{key: entities} for _ in chunks]

    return call


def test_entities_without_offsets_still_produce_amounts(monkeypatch):
    text = "本局决定，对甲处以罚款30万元。"
    monkeypatch.setattr(extractamount, "nlp_input", fake_llm({"罚款30万元": ["30万元"]}))

    assert extractamount.extract_money([text], flag=1) == [300000.0]


def test_entity_missing_from_chunk_is_ignored(monkeypatch):
    text = "本局决定，对甲处以罚款30万元。"
    monkeypatch.setattr(
        extractamount, "nlp_input", fake_llm({"罚款30万元": ["30万元", "99万元"]})
    )

    assert extractamount.extract_money([text], flag=1) == [300000.0]


def test_llm_failure_returns_zero_not_exception(monkeypatch):
    def boom(schema, chunks):
        raise RuntimeError("gateway down")

    monkeypatch.setattr(extractamount, "nlp_input", boom)

    assert extractamount.extract_money(["本局决定，罚款30万元。"], flag=1) == [0]


def test_empty_entities_return_zero(monkeypatch):
    text = "本局决定，对甲予以警告。"
    monkeypatch.setattr(extractamount, "nlp_input", fake_llm({text: []}))

    assert extractamount.extract_money([text], flag=1) == [0]


def test_nlp_input_returns_one_entry_per_chunk(monkeypatch):
    class FakeResponse:
        def __init__(self, content):
            self.choices = [type("Choice", (), {"message": type("Msg", (), {"content": content})()})()]

    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return FakeResponse('{"罚款": ["30万元"]}')

    monkeypatch.setattr(extractamount.client.chat.completions, "create", fake_create)

    result = extractamount.nlp_input(["罚款"], ["第一块", "第二块"])

    assert result == [{"罚款": ["30万元"]}, {"罚款": ["30万元"]}]
    assert len(calls) == 2
    assert calls[0]["response_format"] == {"type": "json_object"}
