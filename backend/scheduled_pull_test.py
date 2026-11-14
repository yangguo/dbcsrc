"""Offline tests for scheduled_pull. No network and no real CSRC data."""

import os

import pandas as pd
import pytest

import scheduled_pull
import web_crawler

COLUMNS = ["名称", "文号", "发文日期", "序列号", "链接", "内容", "机构"]


def make_frame(links: list[str], org: str = "总部") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "名称": [f"案例{index}" for index in range(len(links))],
            "文号": [f"文号{index}" for index in range(len(links))],
            "发文日期": ["2026-11-01"] * len(links),
            "序列号": [str(index) for index in range(len(links))],
            "链接": links,
            "内容": ["正文"] * len(links),
            "机构": [org] * len(links),
        },
        columns=COLUMNS,
    )


class FakeCommit:
    """Stands in for update_sumeventdf_backend and records what it saw."""

    def __init__(self):
        self.batches: list[list[str]] = []

    def __call__(self, frame: pd.DataFrame) -> list:
        self.batches.append(frame["链接"].tolist())
        return frame.to_dict("records")


@pytest.fixture(autouse=True)
def single_channel_registry(monkeypatch):
    registry = {"总部": [{"id": "channel-1", "name": "行政处罚决定"}]}
    monkeypatch.setattr(web_crawler, "org2id", registry)
    return registry


def test_first_run_commits_all_and_sets_watermark(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "state" / "crawl_state.json")

    code = scheduled_pull.run_pull(
        ["总部"],
        max_pages=2,
        state_path=store_path,
        fetch=lambda *_: make_frame(["a", "b", "c"]),
        commit=commit,
        preflight_check=lambda *_: True,
    )

    assert code == scheduled_pull.EXIT_OK
    assert commit.batches[0][:3] == ["a", "b", "c"]
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == "a"


def test_second_run_with_same_data_writes_nothing(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    args = dict(
        fetch=lambda *_: make_frame(["a", "b", "c"]),
        commit=commit,
        preflight_check=lambda *_: True,
    )

    scheduled_pull.run_pull(["总部"], 2, store_path, **args)
    code = scheduled_pull.run_pull(["总部"], 2, store_path, **args)

    assert code == scheduled_pull.EXIT_OK
    assert len(commit.batches) == 1


def test_new_rows_above_watermark_are_committed(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    frames = iter([make_frame(["a", "b"]), make_frame(["n", "m", "a", "b"])])

    scheduled_pull.run_pull(
        ["总部"], 2, store_path, fetch=lambda *_: next(frames),
        commit=commit, preflight_check=lambda *_: True,
    )
    scheduled_pull.run_pull(
        ["总部"], 2, store_path, fetch=lambda *_: make_frame(["n", "m", "a", "b"]),
        commit=commit, preflight_check=lambda *_: True,
    )

    assert commit.batches[1] == ["n", "m"]


def test_preflight_failure_exits_2_and_writes_nothing(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")

    code = scheduled_pull.run_pull(
        ["总部"],
        2,
        store_path,
        fetch=lambda *_: pytest.fail("fetch must not run"),
        commit=commit,
        preflight_check=lambda *_: False,
    )

    assert code == scheduled_pull.EXIT_PREFLIGHT
    assert commit.batches == []
    assert not os.path.exists(store_path)


def test_channel_failure_exits_1(tmp_path):
    def boom(*_):
        raise ConnectionError("connection reset")

    code = scheduled_pull.run_pull(
        ["总部"],
        2,
        str(tmp_path / "crawl_state.json"),
        fetch=boom,
        commit=FakeCommit(),
        preflight_check=lambda *_: True,
    )

    assert code == scheduled_pull.EXIT_PARTIAL


def test_dry_run_returns_2_when_network_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduled_pull, "preflight", lambda *_: False)

    code = scheduled_pull.main(
        ["--org", "总部", "--dry-run", "--state-file", str(tmp_path / "s.json")]
    )

    assert code == scheduled_pull.EXIT_PREFLIGHT


def test_real_commit_dedupes_against_existing_csv(tmp_path, monkeypatch):
    """Exercises web_crawler.save and the 链接 diff, not just the fake commit."""
    data_dir = tmp_path / "csrc2"
    data_dir.mkdir()
    monkeypatch.setattr(web_crawler, "pencsrc2", str(data_dir))
    monkeypatch.setattr(web_crawler, "get_csrc2detail", lambda: pd.DataFrame())
    monkeypatch.setattr(web_crawler, "get_csrc2analysis", lambda: pd.DataFrame())

    web_crawler.update_sumeventdf_backend(make_frame(["a", "b"]))

    written = list(data_dir.glob("csrcdtlall*.csv"))
    assert len(written) == 1
    assert pd.read_csv(written[0], encoding="utf-8-sig")["链接"].tolist() == ["a", "b"]
