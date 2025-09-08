import json
from fastapi.testclient import TestClient
import httpx
import respx
import pytest

from qwenfastapi import main


@pytest.fixture
def client(monkeypatch):
    # default credentials
    monkeypatch.setattr(main, "get_credentials", lambda: ("t", "https://upstream"))
    return TestClient(main.app)


def test_proxies_completions_with_auth_header(client):
    with respx.mock(assert_all_called=True) as respx_mock:
        route = respx_mock.post("https://upstream/v1/completions").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        resp = client.post("/v1/completions", json={"model": "qwen", "prompt": "hi"})
        assert resp.json() == {"ok": True}
        assert route.called
        assert route.calls[0].request.headers["Authorization"] == "Bearer t"


def test_returns_500_on_invalid_json(client):
    resp = client.post("/v1/completions", data="not-json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 500
    assert "detail" in resp.json()


def test_forwards_upstream_error_status(client):
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post("https://upstream/v1/completions").mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )
        resp = client.post("/v1/completions", json={"model": "qwen", "prompt": "hi"})
        assert resp.status_code == 401
        assert resp.json() == {"error": "unauthorized"}


def test_responds_500_when_auth_missing(monkeypatch):
    def raise_no_access_token():
        raise ValueError("No access token")
    monkeypatch.setattr(main, "get_credentials", raise_no_access_token)
    client = TestClient(main.app)
    with respx.mock(assert_all_called=False):
        resp = client.post("/v1/completions", json={"model": "qwen", "prompt": "hi"})
        assert resp.status_code == 500


def test_proxies_messages_and_converts_response(client):
    with respx.mock(assert_all_called=True) as respx_mock:
        def check_request(request):
            data = json.loads(request.content.decode())
            assert data["messages"][0]["content"] == "hi"
            return httpx.Response(
                200,
                json={
                    "id": "1",
                    "model": "qwen",
                    "choices": [{"message": {"content": "hello"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 2},
                },
            )
        respx_mock.post("https://upstream/chat/completions").mock(side_effect=check_request)
        resp = client.post(
            "/v1/messages",
            json={"model": "qwen", "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]},
        )
        body = resp.json()
        assert body["content"][0]["text"] == "hello"
        assert body["usage"] == {"input_tokens": 1, "output_tokens": 2}


def test_lists_models(client):
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get("https://upstream/models").mock(
            return_value=httpx.Response(200, json={"data": ["qwen"]})
        )
        resp = client.get("/v1/models")
        assert resp.json() == {"data": ["qwen"]}


def test_gets_model_detail(client):
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get("https://upstream/models/qwen").mock(
            return_value=httpx.Response(200, json={"id": "qwen", "context_length": 8192})
        )
        resp = client.get("/v1/models/qwen")
        assert resp.json()["id"] == "qwen"
