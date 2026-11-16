"""Offline tests for the shared LLM client and model tiers."""

import importlib

import llm_client


def test_get_client_is_a_singleton():
    assert llm_client.get_client() is llm_client.get_client()


def test_client_has_bounded_timeout_and_retries():
    client = llm_client.get_client()
    assert client.timeout == 60.0
    assert client.max_retries == 3


def test_light_model_defaults_to_main_model(monkeypatch):
    monkeypatch.delenv("OPENAI_LIGHT_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "heavy-model")
    reloaded = importlib.reload(llm_client)
    try:
        assert reloaded.LIGHT_MODEL == "heavy-model"
    finally:
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        importlib.reload(llm_client)


def test_light_model_can_be_set_independently(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "heavy-model")
    monkeypatch.setenv("OPENAI_LIGHT_MODEL", "light-model")
    reloaded = importlib.reload(llm_client)
    try:
        assert reloaded.MODEL == "heavy-model"
        assert reloaded.LIGHT_MODEL == "light-model"
    finally:
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("OPENAI_LIGHT_MODEL", raising=False)
        importlib.reload(llm_client)


def test_timeout_and_retries_read_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "1")
    reloaded = importlib.reload(llm_client)
    try:
        client = reloaded.get_client()
        assert client.timeout == 5.0
        assert client.max_retries == 1
    finally:
        monkeypatch.delenv("OPENAI_TIMEOUT_SECONDS", raising=False)
        monkeypatch.delenv("OPENAI_MAX_RETRIES", raising=False)
        importlib.reload(llm_client)
