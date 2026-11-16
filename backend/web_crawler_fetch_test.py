"""Offline tests for checked CSRC page fetches. No network."""

import json

import pytest
import requests

import web_crawler

BASE_URL = "http://example.test/page="


def page_url(pageno: int) -> str:
    return f"{BASE_URL}{pageno}"


def item(link: str) -> dict:
    return {
        "subTitle": f"案例{link}",
        "url": link,
        "publishedTimeStr": "2026-11-01",
        "contentHtml": "正文",
        "domainMetaList": [
            {
                "resultList": [
                    {"key": "wh", "value": "文号"},
                    {"key": "syh", "value": "1"},
                ]
            }
        ],
    }


def payload(*links: str) -> dict:
    return {"data": {"results": [item(link) for link in links]}}


class FakeResponse:
    def __init__(self, body: bytes):
        self.content = body
        self.status_code = 200

    def raise_for_status(self):
        return None


def json_response(body: dict) -> FakeResponse:
    return FakeResponse(json.dumps(body).encode())


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(
        web_crawler,
        "get_url_backend",
        lambda orgname, selected_ids=None: [BASE_URL],
    )
    monkeypatch.setattr(web_crawler.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(web_crawler.random, "randint", lambda low, high: 1)
    monkeypatch.setattr(web_crawler, "savedf_backend", lambda frame, basename: None)


def test_strict_fetch_raises_after_page_request_failure(monkeypatch):
    def fake_get(url, **kwargs):
        if url == page_url(2):
            raise requests.exceptions.ConnectionError("down")
        return json_response(payload("one"))

    monkeypatch.setattr(web_crawler.requests, "get", fake_get)

    with pytest.raises(web_crawler.CsrcFetchError) as excinfo:
        web_crawler.get_sumeventdf_backend(
            "总部", 1, 2, ["channel-1"], raise_on_error=True
        )

    assert excinfo.value.orgname == "总部"
    assert excinfo.value.failed_urls == (page_url(2),)


def test_non_strict_fetch_returns_partial_rows(monkeypatch, capsys):
    def fake_get(url, **kwargs):
        if url == page_url(2):
            raise requests.exceptions.ConnectionError("down")
        return json_response(payload("one"))

    monkeypatch.setattr(web_crawler.requests, "get", fake_get)

    frame = web_crawler.get_sumeventdf_backend("总部", 1, 2, ["channel-1"])

    assert frame["链接"].tolist() == ["one"]
    assert capsys.readouterr().err.count(page_url(2)) == 1


def test_strict_fetch_raises_on_json_parse_failure(monkeypatch):
    monkeypatch.setattr(
        web_crawler.requests,
        "get",
        lambda url, **kwargs: FakeResponse(b"not json"),
    )

    with pytest.raises(web_crawler.CsrcFetchError) as excinfo:
        web_crawler.get_sumeventdf_backend(
            "总部", 1, 1, ["channel-1"], raise_on_error=True
        )

    assert excinfo.value.failed_urls == (page_url(1),)


def test_strict_fetch_returns_all_rows_when_pages_succeed(monkeypatch):
    responses = {page_url(1): ["one"], page_url(2): ["two"]}
    monkeypatch.setattr(
        web_crawler.requests,
        "get",
        lambda url, **kwargs: json_response(payload(*responses[url])),
    )

    frame = web_crawler.get_sumeventdf_backend(
        "总部", 1, 2, ["channel-1"], raise_on_error=True
    )

    assert frame["链接"].tolist() == ["one", "two"]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"data": {}},
        {"data": {"results": {}}},
    ],
)
def test_malformed_page_shape_is_a_failure(monkeypatch, body):
    monkeypatch.setattr(
        web_crawler.requests, "get", lambda url, **kwargs: json_response(body)
    )

    with pytest.raises(web_crawler.CsrcFetchError) as excinfo:
        web_crawler.get_sumeventdf_backend(
            "总部", 1, 1, ["channel-1"], raise_on_error=True
        )

    assert excinfo.value.failed_urls == (page_url(1),)


def test_empty_results_page_is_not_an_error(monkeypatch):
    monkeypatch.setattr(
        web_crawler.requests, "get", lambda url, **kwargs: json_response(payload())
    )

    frame = web_crawler.get_sumeventdf_backend(
        "总部", 1, 1, ["channel-1"], raise_on_error=True
    )

    assert frame.empty


def test_failed_page_does_not_parse_previous_response(monkeypatch, capsys):
    def fake_get(url, **kwargs):
        if url == page_url(2):
            raise requests.exceptions.HTTPError("blocked")
        links = {page_url(1): ["one"], page_url(3): ["three"]}
        return json_response(payload(*links[url]))

    monkeypatch.setattr(web_crawler.requests, "get", fake_get)

    frame = web_crawler.get_sumeventdf_backend("总部", 1, 3, ["channel-1"])

    assert frame["链接"].tolist() == ["one", "three"]
    assert capsys.readouterr().err.count(page_url(2)) == 1


def test_selective_delegates_non_strict(monkeypatch):
    def fake_get(url, **kwargs):
        if url == page_url(2):
            raise requests.exceptions.ConnectionError("down")
        return json_response(payload("one"))

    monkeypatch.setattr(web_crawler.requests, "get", fake_get)

    frame = web_crawler.get_sumeventdf_backend_selective(
        "总部", 1, 2, ["channel-1"]
    )

    assert frame["链接"].tolist() == ["one"]


def test_selective_delegates_strict(monkeypatch):
    def fake_get(url, **kwargs):
        if url == page_url(2):
            raise requests.exceptions.ConnectionError("down")
        return json_response(payload("one"))

    monkeypatch.setattr(web_crawler.requests, "get", fake_get)

    with pytest.raises(web_crawler.CsrcFetchError):
        web_crawler.get_sumeventdf_backend_selective(
            "总部", 1, 2, ["channel-1"], raise_on_error=True
        )
