"""Offline tests for idempotent Mongo writes. No live MongoDB."""

import pandas as pd
import pytest

import main


class FakeCollection:
    def __init__(self, existing: dict[str, dict] | None = None):
        self.documents = dict(existing or {})
        self.indexes: list[tuple] = []
        self.operations = []

    def bulk_write(self, operations, ordered=True):
        self.operations.extend(operations)
        for operation in operations:
            key = operation._filter["链接"]
            self.documents[key] = operation._doc["$set"]
        return None

    def create_index(self, keys, unique=False, name=None):
        if unique and len(self.documents) > len(set(self.documents)):
            raise RuntimeError("duplicate key")
        self.indexes.append((keys, unique, name))
        return name


@pytest.fixture
def frame():
    return pd.DataFrame(
        {
            "链接": ["https://a", "https://b"],
            "名称": ["甲", "乙"],
            "机构": ["总部", "总部"],
        }
    )


def test_insert_online_data_upserts_by_link(monkeypatch, frame):
    collection = FakeCollection()
    monkeypatch.setattr(main, "get_collection", lambda *_: collection)

    assert main.insert_online_data(frame) is True
    assert set(collection.documents) == {"https://a", "https://b"}
    assert collection.operations[0]._upsert is True


def test_repeat_write_does_not_grow_collection(monkeypatch, frame):
    collection = FakeCollection()
    monkeypatch.setattr(main, "get_collection", lambda *_: collection)

    main.insert_online_data(frame)
    main.insert_online_data(frame)

    assert len(collection.documents) == 2


def test_missing_link_column_is_rejected(monkeypatch):
    collection = FakeCollection()
    monkeypatch.setattr(main, "get_collection", lambda *_: collection)

    assert main.insert_online_data(pd.DataFrame({"名称": ["甲"]})) is False


def test_ensure_online_index_creates_unique_index(monkeypatch):
    collection = FakeCollection()
    monkeypatch.setattr(main, "get_collection", lambda *_: collection)

    assert main.ensure_online_index() == "unique"
    assert collection.indexes == [("链接", True, "uniq_link")]


def test_ensure_online_index_falls_back_on_duplicates(monkeypatch):
    collection = FakeCollection()
    collection.documents = {"a": {}, "b": {}}
    collection.create_index = lambda keys, unique=False, name=None: (
        (_ for _ in ()).throw(RuntimeError("duplicate key"))
        if unique
        else collection.indexes.append((keys, unique, name))
    )
    monkeypatch.setattr(main, "get_collection", lambda *_: collection)

    assert main.ensure_online_index() == "non-unique"
    assert collection.indexes == [("链接", False, "idx_link")]
