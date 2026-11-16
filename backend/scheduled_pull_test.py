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


def test_backlog_larger_than_window_fetches_until_watermark(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    store = scheduled_pull.CrawlStateStore(store_path)
    state = store.get("总部", "channel-1", "")
    state.last_link = "a"
    store.upsert(state)

    all_links = ["n1", "n2", "n3", "n4", "n5", "n6", "a", "b"]

    def fetch(org, start, end, ids):
        return make_frame(all_links[: end * 2])

    code = scheduled_pull.run_pull(
        ["总部"],
        max_pages=2,
        state_path=store_path,
        fetch=fetch,
        commit=commit,
        preflight_check=lambda *_: True,
    )

    assert code == scheduled_pull.EXIT_OK
    assert commit.batches == [["n1", "n2", "n3", "n4", "n5", "n6"]]
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == "n1"


def test_backlog_beyond_cap_does_not_advance_watermark(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    store = scheduled_pull.CrawlStateStore(store_path)
    state = store.get("总部", "channel-1", "")
    state.last_link = "a"
    store.upsert(state)

    calls = {"count": 0}

    def fetch(org, start, end, ids):
        calls["count"] += 1
        if calls["count"] > 200:
            pytest.fail("fetch did not stop; no backlog cap")
        return make_frame(["n1", "n2", "n3", "n4"])

    code = scheduled_pull.run_pull(
        ["总部"],
        max_pages=2,
        state_path=store_path,
        fetch=fetch,
        commit=commit,
        preflight_check=lambda *_: True,
        max_fetch_pages=6,
    )

    assert calls["count"] == 3
    assert code == scheduled_pull.EXIT_PARTIAL
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == "a"


def make_pull_state(store_path: str, watermark: str) -> None:
    store = scheduled_pull.CrawlStateStore(store_path)
    state = store.get("总部", "channel-1", "")
    state.last_link = watermark
    store.upsert(state)


def test_partial_fetch_mid_catchup_keeps_watermark(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    make_pull_state(store_path, "a")
    calls = {"count": 0}

    def fetch(org, start, end, ids):
        calls["count"] += 1
        if calls["count"] == 1:
            return make_frame(["n1", "n2"])
        raise web_crawler.CsrcFetchError("总部", ["url-page-2"])

    code = scheduled_pull.run_pull(
        ["总部"],
        max_pages=1,
        state_path=store_path,
        fetch=fetch,
        commit=commit,
        preflight_check=lambda *_: True,
        max_fetch_pages=4,
    )

    assert code == scheduled_pull.EXIT_PARTIAL
    assert commit.batches == [["n1", "n2"]]
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == "a"


def test_partial_fetch_on_first_chunk_commits_nothing(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    make_pull_state(store_path, "a")

    def fetch(*_):
        raise web_crawler.CsrcFetchError("总部", ["url-page-1"])

    code = scheduled_pull.run_pull(
        ["总部"],
        2,
        store_path,
        fetch=fetch,
        commit=commit,
        preflight_check=lambda *_: True,
    )

    assert code == scheduled_pull.EXIT_PARTIAL
    assert commit.batches == []
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == "a"


def test_first_run_partial_fetch_commits_nothing(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")

    def fetch(*_):
        raise web_crawler.CsrcFetchError("总部", ["url-page-1"])

    code = scheduled_pull.run_pull(
        ["总部"],
        2,
        store_path,
        fetch=fetch,
        commit=commit,
        preflight_check=lambda *_: True,
    )

    assert code == scheduled_pull.EXIT_PARTIAL
    assert commit.batches == []
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == ""


def test_watermark_at_top_does_not_commit(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    make_pull_state(store_path, "a")
    calls = {"count": 0}

    def fetch(*_):
        calls["count"] += 1
        return make_frame(["a", "b"])

    code = scheduled_pull.run_pull(
        ["总部"],
        2,
        store_path,
        fetch=fetch,
        commit=commit,
        preflight_check=lambda *_: True,
    )

    assert code == scheduled_pull.EXIT_OK
    assert calls["count"] == 1
    assert commit.batches == []
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == "a"


def test_empty_feed_with_existing_watermark_fails_without_commit(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    make_pull_state(store_path, "a")

    code = scheduled_pull.run_pull(
        ["总部"],
        2,
        store_path,
        fetch=lambda *_: make_frame([]),
        commit=commit,
        preflight_check=lambda *_: True,
    )

    assert code == scheduled_pull.EXIT_PARTIAL
    assert commit.batches == []
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == "a"


def test_cap_never_below_window(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    make_pull_state(store_path, "a")
    ends = []

    def fetch(org, start, end, ids):
        ends.append(end)
        return make_frame(["n1"])

    code = scheduled_pull.run_pull(
        ["总部"],
        5,
        store_path,
        fetch=fetch,
        commit=commit,
        preflight_check=lambda *_: True,
        max_fetch_pages=3,
    )

    assert ends == [5]
    assert code == scheduled_pull.EXIT_PARTIAL
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == "a"


def test_trim_to_new_contract():
    frame = make_frame(["n1", "b", "c"])

    assert scheduled_pull.trim_to_new(frame, "") is frame
    assert scheduled_pull.trim_to_new(frame, "n1").empty
    assert scheduled_pull.trim_to_new(frame, "a") is None


def test_empty_links_are_kept_and_do_not_become_the_watermark(tmp_path):
    commit = FakeCommit()
    store_path = str(tmp_path / "crawl_state.json")
    make_pull_state(store_path, "a")

    code = scheduled_pull.run_pull(
        ["总部"],
        2,
        store_path,
        fetch=lambda *_: make_frame(["", "", "a", "b"]),
        commit=commit,
        preflight_check=lambda *_: True,
    )

    assert code == scheduled_pull.EXIT_OK
    assert commit.batches == [["", ""]]
    state = scheduled_pull.CrawlStateStore(store_path).get("总部", "channel-1", "")
    assert state.last_link == "a"


def test_dry_run_returns_2_when_network_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduled_pull, "preflight", lambda *_: False)

    code = scheduled_pull.main(
        ["--org", "总部", "--dry-run", "--state-file", str(tmp_path / "s.json")]
    )

    assert code == scheduled_pull.EXIT_PREFLIGHT


def write_shard(directory, name: str, links: list[str], tag: str) -> None:
    frame = make_frame(links)
    frame["内容"] = tag
    frame.to_csv(os.path.join(str(directory), name), index=False, encoding="utf-8-sig")


def test_compact_merges_shards_and_keeps_latest(tmp_path):
    data_dir = tmp_path / "csrc2"
    data_dir.mkdir()
    write_shard(data_dir, "csrcdtlall20260101000000.csv", ["a", "b"], "old")
    write_shard(data_dir, "csrcdtlall20260201000000.csv", ["b", "c"], "new")

    result = scheduled_pull.compact(str(data_dir))

    assert result["csrcdtlall"] == (4, 3)
    assert result["csrc2analysis"] == (0, 0)
    remaining = list(data_dir.glob("csrcdtlall*.csv"))
    assert len(remaining) == 1
    merged = pd.read_csv(remaining[0], encoding="utf-8-sig")
    assert merged["链接"].tolist() == ["a", "b", "c"]
    assert merged[merged["链接"] == "b"]["内容"].iloc[0] == "new"
    archived = sorted((data_dir / "archive").glob("*.csv"))
    assert [path.name for path in archived] == [
        "csrcdtlall20260101000000.csv",
        "csrcdtlall20260201000000.csv",
    ]


def test_compact_second_run_is_noop(tmp_path):
    data_dir = tmp_path / "csrc2"
    data_dir.mkdir()
    write_shard(data_dir, "csrcdtlall20260101000000.csv", ["a"], "old")
    write_shard(data_dir, "csrcdtlall20260201000000.csv", ["b"], "new")

    scheduled_pull.compact(str(data_dir))
    before = sorted(path.name for path in data_dir.glob("*.csv"))
    result = scheduled_pull.compact(str(data_dir))

    assert result == {"csrcdtlall": (0, 0), "csrc2analysis": (0, 0)}
    assert sorted(path.name for path in data_dir.glob("*.csv")) == before


def test_compact_empty_dir_is_noop(tmp_path):
    assert scheduled_pull.compact(str(tmp_path)) == {
        "csrcdtlall": (0, 0),
        "csrc2analysis": (0, 0),
    }


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


def test_real_commit_writes_analysis_once_per_link(tmp_path, monkeypatch):
    data_dir = tmp_path / "csrc2"
    data_dir.mkdir()
    monkeypatch.setattr(web_crawler, "pencsrc2", str(data_dir))
    timestamps = iter(
        ["20260101000000", "20260101000001", "20260101000002", "20260101000003"]
    )
    monkeypatch.setattr(web_crawler, "get_now", lambda: next(timestamps))

    web_crawler.update_sumeventdf_backend(make_frame(["a", "b"]))
    web_crawler.update_sumeventdf_backend(make_frame(["b", "c"]))

    detail = pd.concat(
        [
            pd.read_csv(path, encoding="utf-8-sig")
            for path in sorted(data_dir.glob("csrcdtlall*.csv"))
        ],
        ignore_index=True,
    )
    analysis = pd.concat(
        [
            pd.read_csv(path, encoding="utf-8-sig")
            for path in sorted(data_dir.glob("csrc2analysis*.csv"))
        ],
        ignore_index=True,
    )
    assert detail["链接"].tolist() == ["a", "b", "c"]
    assert analysis["链接"].tolist() == ["a", "b", "c"]
