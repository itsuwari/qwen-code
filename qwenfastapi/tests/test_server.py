import json
import asyncio
from fastapi.testclient import TestClient
import httpx
import respx
import pytest

from qwenfastapi import main


@pytest.fixture
def client(monkeypatch):
    # default credentials
    monkeypatch.setattr(main, "get_credentials", lambda: ("t", "https://upstream"))
    monkeypatch.setenv("QWEN_FASTAPI_API_KEY", "pw")
    monkeypatch.setattr(main, "API_KEY", "pw")
    monkeypatch.setattr(main, "LOCAL_ONLY", False)
    client = TestClient(main.app)
    client.headers.update({"X-API-Key": "pw"})
    return client

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
    monkeypatch.setattr(main, "get_credentials", lambda: (_ for _ in ()).throw(ValueError("No access token")))
    monkeypatch.setenv("QWEN_FASTAPI_API_KEY", "pw")
    monkeypatch.setattr(main, "API_KEY", "pw")
    monkeypatch.setattr(main, "LOCAL_ONLY", False)
    client = TestClient(main.app)
    client.headers.update({"X-API-Key": "pw"})
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
    resp = client.get("/v1/models")
    data = resp.json()["data"]
    ids = {m["id"] for m in data}
    assert {"qwen3-coder-plus", "qwen3-coder-flash"} <= ids


def test_gets_model_detail(client):
    resp = client.get("/v1/models/qwen3-coder-plus")
    assert resp.json()["id"] == "qwen3-coder-plus"


def test_rejects_invalid_api_key(monkeypatch):
    async def run():
        transport = httpx.ASGITransport(app=main.app, client=("203.0.113.5", 123))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.post(
                "/v1/completions", json={"model": "qwen", "prompt": "hi"}, headers={"X-API-Key": "bad"}
            )

    monkeypatch.setattr(main, "get_credentials", lambda: ("t", "https://upstream"))
    monkeypatch.setenv("QWEN_FASTAPI_API_KEY", "pw")
    monkeypatch.setattr(main, "API_KEY", "pw")
    monkeypatch.setattr(main, "LOCAL_ONLY", False)
    resp = asyncio.run(run())
    assert resp.status_code == 401


def test_local_bypasses_api_key(monkeypatch):
    async def fake_forward(method, url, token, json_body=None):
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(main, "get_credentials", lambda: ("t", "https://upstream"))
    monkeypatch.setattr(main, "forward", fake_forward)
    monkeypatch.setattr(main, "API_KEY", "pw")
    monkeypatch.setattr(main, "LOCAL_ONLY", False)
    client = TestClient(main.app)
    resp = client.post("/v1/completions", json={"prompt": "hi"})
    assert resp.status_code == 200


def test_chat_completions_falls_back(client):
    with respx.mock(assert_all_called=True) as respx_mock:
        def check_request(request):
            data = json.loads(request.content.decode())
            assert data["model"] == "qwen3-coder-plus"
            return httpx.Response(200, json={"ok": True})

        respx_mock.post("https://upstream/chat/completions").mock(side_effect=check_request)
        resp = client.post(
            "/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]}
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


def test_main_accepts_cli_arguments(monkeypatch):
    import sys
    import types

    called: dict[str, str | int | None] = {}

    def fake_run(app, host, port, **kwargs):
        called["host"] = host
        called["port"] = port
        called["ssl_certfile"] = kwargs.get("ssl_certfile")
        called["ssl_keyfile"] = kwargs.get("ssl_keyfile")

    fake_uvicorn = types.SimpleNamespace(run=fake_run)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--key",
            "cli",
            "--listen",
            "0.0.0.0:1234",
            "--certfile",
            "cert.pem",
            "--keyfile",
            "key.pem",
        ],
    )
    monkeypatch.setattr(main, "API_KEY", None)
    monkeypatch.setattr(main, "LISTEN", "local")
    monkeypatch.setattr(main, "LISTEN_ENV", "local")
    monkeypatch.setattr(main, "PORT", 3000)
    monkeypatch.setattr(main, "LOCAL_ONLY", True)
    monkeypatch.setattr(main, "CERTFILE", None)
    monkeypatch.setattr(main, "KEYFILE", None)

    main.main()

    assert main.API_KEY == "cli"
    assert called["host"] == "0.0.0.0"
    assert called["port"] == 1234
    assert called["ssl_certfile"] == "cert.pem"
    assert called["ssl_keyfile"] == "key.pem"
    assert main.LOCAL_ONLY is False


def test_main_defaults_to_local(monkeypatch):
    import sys
    import types

    called: dict[str, str | int | None] = {}

    def fake_run(app, host, port, **kwargs):
        called["host"] = host
        called["port"] = port
        called["ssl_certfile"] = kwargs.get("ssl_certfile")
        called["ssl_keyfile"] = kwargs.get("ssl_keyfile")

    fake_uvicorn = types.SimpleNamespace(run=fake_run)
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setattr(main, "API_KEY", None)
    monkeypatch.setattr(main, "LISTEN", "local")
    monkeypatch.setattr(main, "LISTEN_ENV", "local")
    monkeypatch.setattr(main, "PORT", 3000)
    monkeypatch.setattr(main, "LOCAL_ONLY", False)
    monkeypatch.setattr(main, "CERTFILE", None)
    monkeypatch.setattr(main, "KEYFILE", None)

    main.main()

    assert called["host"] == "0.0.0.0"
    assert called["port"] == 3000
    assert called["ssl_certfile"] is None
    assert called["ssl_keyfile"] is None
    assert main.LOCAL_ONLY is True


def test_allows_private_client(monkeypatch):
    async def fake_forward(method, url, token, json_body=None):
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(main, "get_credentials", lambda: ("t", "https://upstream"))
    monkeypatch.setattr(main, "forward", fake_forward)
    monkeypatch.setattr(main, "API_KEY", None)
    monkeypatch.setattr(main, "LOCAL_ONLY", True)

    async def run():
        transport = httpx.ASGITransport(app=main.app, client=("10.1.2.3", 123))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.post("/v1/completions", json={"model": "qwen", "prompt": "hi"})

    resp = asyncio.run(run())
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_rejects_public_client(monkeypatch):
    async def fake_forward(method, url, token, json_body=None):
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(main, "get_credentials", lambda: ("t", "https://upstream"))
    monkeypatch.setattr(main, "forward", fake_forward)
    monkeypatch.setattr(main, "API_KEY", None)
    monkeypatch.setattr(main, "LOCAL_ONLY", True)

    async def run():
        transport = httpx.ASGITransport(app=main.app, client=("203.0.113.5", 123))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.post("/v1/completions", json={"model": "qwen", "prompt": "hi"})

    resp = asyncio.run(run())
    assert resp.status_code == 403


def test_is_local_address_ranges():
    # IPv4 loopback and private networks
    assert main.is_local_address("127.0.0.1")
    assert main.is_local_address("10.0.0.1")
    assert main.is_local_address("100.64.0.1")
    assert main.is_local_address("172.16.0.1")
    assert main.is_local_address("192.168.0.1")
    assert main.is_local_address("169.254.1.1")
    # IPv6 loopback, private, and link-local
    assert main.is_local_address("::1")
    assert main.is_local_address("fc00::1")
    assert main.is_local_address("fe80::1")
    # Public addresses should be rejected
    assert not main.is_local_address("8.8.8.8")
    assert not main.is_local_address("2001:4860:4860::8888")


def test_get_credentials_adds_https(monkeypatch, tmp_path):
    creds_dir = tmp_path / ".qwen"
    creds_dir.mkdir()
    (creds_dir / "oauth_creds.json").write_text(
        json.dumps({"access_token": "t", "resource_url": "upstream"})
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    token, endpoint = main.get_credentials()
    assert token == "t"
    assert endpoint == "https://upstream"
