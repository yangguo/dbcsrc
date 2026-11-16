"""Scheduled incremental pull from the CSRC searchList endpoint.

Runs one pass per invocation and exits. Meant to be driven by host cron so the
API's multiple uvicorn workers never see the schedule. State lives in a JSON
file keyed by org and channel, and every write is atomic.

Idempotency: the watermark is the newest 链接 already committed. Each run reads
from the top until it finds that link, in windows of --max-pages, capped at
--max-fetch-pages total pages. Fetches are checked: any failed page aborts the
channel, so a partial fetch never advances the watermark. Only rows above the
watermark are committed, so a repeat run or a rerun after a crash writes
nothing new.

Exit codes:
    0  all channels succeeded
    1  at least one channel failed or hit the fetch cap after writing what it could
    2  preflight failed, nothing was written
"""

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

import pandas as pd

import web_crawler

DEFAULT_MAX_PAGES = 3
DEFAULT_MAX_FETCH_PAGES = 100

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_PREFLIGHT = 2


@dataclass
class CrawlState:
    org: str
    channel_id: str
    channel_name: str
    last_link: str = ""
    updated_at: str = ""


class CrawlStateStore:
    """JSON backed registry keyed by "<org>/<channel_id>"."""

    def __init__(self, path: str):
        self.path = path
        self._entries: dict[str, CrawlState] = {}
        self.load()

    @staticmethod
    def _key(org: str, channel_id: str) -> str:
        return f"{org}/{channel_id}"

    def load(self) -> None:
        if not os.path.exists(self.path):
            self._entries = {}
            return
        with open(self.path, encoding="utf-8") as handle:
            raw = json.load(handle)
        self._entries = {
            key: CrawlState(**value) for key, value in raw.get("channels", {}).items()
        }

    def get(self, org: str, channel_id: str, channel_name: str) -> CrawlState:
        key = self._key(org, channel_id)
        if key not in self._entries:
            self._entries[key] = CrawlState(
                org=org, channel_id=channel_id, channel_name=channel_name
            )
        return self._entries[key]

    def upsert(self, state: CrawlState) -> None:
        state.updated_at = datetime.now(timezone.utc).isoformat()
        self._entries[self._key(state.org, state.channel_id)] = state
        self.save()

    def save(self) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        payload = {
            "channels": {key: asdict(value) for key, value in self._entries.items()}
        }
        fd, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.path)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise


def _fetch_strict(org: str, start: int, end: int, ids: list[str]) -> pd.DataFrame:
    """Fetch pages, raising CsrcFetchError when any page failed."""
    return web_crawler.get_sumeventdf_backend(
        org, start, end, ids, raise_on_error=True
    )


def preflight(org: str, channel_id: str) -> bool:
    """Fetch page 1 of one known channel. Any failure means stop before writing."""
    try:
        frame = _fetch_strict(org, 1, 1, [channel_id])
    except Exception as error:
        print(f"preflight failed for {org}/{channel_id}: {error}", file=sys.stderr)
        return False
    return not frame.empty


def trim_to_new(frame: pd.DataFrame, watermark: str) -> Optional[pd.DataFrame]:
    """Keep rows above the watermark link. None means the watermark was not found."""
    if frame.empty:
        return frame if not watermark else None
    if not watermark:
        return frame
    links = frame["链接"].tolist()
    if watermark not in links:
        return None
    return frame.iloc[: links.index(watermark)].reset_index(drop=True)


def _append_unique(acc: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    """Add one page's rows, keeping the first row for each non-empty 链接."""
    if frame.empty:
        return acc
    combined = frame if acc.empty else pd.concat([acc, frame], ignore_index=True)
    links = combined["链接"].fillna("").astype(str)
    keep = (links == "") | ~links.duplicated(keep="first")
    return combined[keep].reset_index(drop=True)


def _next_watermark(frame: pd.DataFrame) -> str:
    """Return the newest non-empty link, or "" when the frame has none."""
    links = frame["链接"].fillna("").astype(str)
    non_empty = links[links != ""]
    return non_empty.iloc[0] if not non_empty.empty else ""


def _commit_count(records: object) -> int:
    return len(records) if isinstance(records, list) else 0


def pull_channel(
    org: str,
    channel: dict,
    state: CrawlState,
    max_pages: int,
    fetch: Callable[..., pd.DataFrame] = _fetch_strict,
    commit: Callable[[pd.DataFrame], object] = web_crawler.update_sumeventdf_backend,
    *,
    max_fetch_pages: int = DEFAULT_MAX_FETCH_PAGES,
) -> tuple[int, bool]:
    """Pull one channel until the watermark is found or the fetch cap is hit.

    Returns (new_record_count, succeeded).
    """
    channel_id = channel["id"]
    cap = max(max_pages, max_fetch_pages)

    if not state.last_link:
        try:
            frame = fetch(org, 1, max_pages, [channel_id])
        except Exception as error:
            print(f"pull failed for {org}/{channel_id}: {error}", file=sys.stderr)
            return 0, False
        fresh = trim_to_new(frame, "")
        if fresh.empty:
            return 0, True
        new_records = commit(fresh)
        state.last_link = _next_watermark(fresh)
        return _commit_count(new_records), True

    accumulated = pd.DataFrame()
    start = 1
    stop_reason = f"fetch cap of {cap} pages reached"
    while start <= cap:
        end = min(start + max_pages - 1, cap)
        try:
            page = fetch(org, start, end, [channel_id])
        except Exception as error:
            print(f"pull failed for {org}/{channel_id}: {error}", file=sys.stderr)
            stop_reason = "fetch failed"
            break
        page_empty = page.empty
        accumulated = _append_unique(accumulated, page)
        fresh = trim_to_new(accumulated, state.last_link)
        if fresh is not None:
            if fresh.empty:
                return 0, True
            new_records = commit(fresh)
            next_watermark = _next_watermark(fresh)
            if next_watermark:
                state.last_link = next_watermark
            return _commit_count(new_records), True
        if page_empty:
            stop_reason = "listing ended before the watermark"
            break
        start = end + 1

    new_records = commit(accumulated) if not accumulated.empty else []
    print(
        f"{org}/{channel['name']}: watermark {state.last_link!r} not found "
        f"({stop_reason})",
        file=sys.stderr,
    )
    return _commit_count(new_records), False


def run_pull(
    orgs: list[str],
    max_pages: int,
    state_path: str,
    fetch: Callable[..., pd.DataFrame] = _fetch_strict,
    commit: Callable[[pd.DataFrame], object] = web_crawler.update_sumeventdf_backend,
    preflight_check: Callable[[str, str], bool] = preflight,
    *,
    max_fetch_pages: int = DEFAULT_MAX_FETCH_PAGES,
) -> int:
    store = CrawlStateStore(state_path)
    failed: list[str] = []
    total_new = 0
    attempted = 0

    for org in orgs:
        channels = web_crawler.org2id.get(org)
        if not channels:
            print(f"unknown org: {org}", file=sys.stderr)
            failed.append(org)
            continue

        if not preflight_check(org, channels[0]["id"]):
            print(f"preflight failed for {org}, skipping", file=sys.stderr)
            failed.append(org)
            continue

        for channel in channels:
            attempted += 1
            state = store.get(org, channel["id"], channel["name"])
            new_count, ok = pull_channel(
                org,
                channel,
                state,
                max_pages,
                fetch=fetch,
                commit=commit,
                max_fetch_pages=max_fetch_pages,
            )
            store.upsert(state)
            total_new += new_count
            print(f"{org}/{channel['name']}: new={new_count} ok={ok}")
            if not ok:
                failed.append(f"{org}/{channel['name']}")

    print(f"total new records: {total_new}")
    if attempted == 0:
        return EXIT_PREFLIGHT
    return EXIT_PARTIAL if failed else EXIT_OK


COMPACT_PREFIXES = ("csrcdtlall", "csrc2analysis")


def compact_prefix(data_dir: str, prefix: str) -> tuple[int, int]:
    """Merge every shard of one prefix into a single deduped shard.

    Returns (rows_before, rows_after). Old shards move to archive/.
    Zero or one shard means nothing to do and no file is written.
    """
    import glob

    shards = sorted(glob.glob(os.path.join(data_dir, prefix + "*.csv")))
    if len(shards) <= 1:
        return 0, 0
    frames = []
    for path in shards:
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig")
            if not frame.empty:
                frames.append(frame)
        except Exception as error:
            print(f"compact: skip unreadable {path}: {error}", file=sys.stderr)
    if not frames:
        return 0, 0
    merged = pd.concat(frames, ignore_index=True)
    before = len(merged)
    if "链接" in merged.columns:
        merged = merged.drop_duplicates(subset=["链接"], keep="last")
    after = len(merged)
    archive = os.path.join(data_dir, "archive")
    os.makedirs(archive, exist_ok=True)
    merged.to_csv(
        os.path.join(data_dir, f"{prefix}{web_crawler.get_now()}.csv"),
        index=False,
        encoding="utf-8-sig",
    )
    for path in shards:
        os.replace(path, os.path.join(archive, os.path.basename(path)))
    return before, after


def compact(data_dir: Optional[str] = None) -> dict[str, tuple[int, int]]:
    """Merge detail and analysis shards. Safe to rerun: a second run is a no-op."""
    target = data_dir or web_crawler.pencsrc2
    return {prefix: compact_prefix(target, prefix) for prefix in COMPACT_PREFIXES}


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scheduled CSRC incremental pull")
    parser.add_argument(
        "--org",
        action="append",
        dest="orgs",
        help="Organization name from web_crawler.org2id. Repeatable.",
    )
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument(
        "--max-fetch-pages", type=int, default=DEFAULT_MAX_FETCH_PAGES
    )
    parser.add_argument(
        "--state-file",
        default=os.path.join(
            os.path.dirname(web_crawler.pencsrc2), "state", "crawl_state.json"
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Preflight only")
    parser.add_argument(
        "--compact", action="store_true", help="Merge CSV shards, then exit"
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    if args.compact:
        result = compact()
        for prefix, (before, after) in result.items():
            print(f"{prefix}: rows {before} -> {after}")
        return EXIT_OK
    orgs = args.orgs or ["总部"]
    if args.dry_run:
        for org in orgs:
            channels = web_crawler.org2id.get(org) or []
            if not channels or not preflight(org, channels[0]["id"]):
                return EXIT_PREFLIGHT
        print("preflight ok")
        return EXIT_OK
    return run_pull(
        orgs,
        args.max_pages,
        args.state_file,
        max_fetch_pages=args.max_fetch_pages,
    )


if __name__ == "__main__":
    sys.exit(main())
