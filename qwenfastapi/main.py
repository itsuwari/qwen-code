from fastapi import Depends, FastAPI, HTTPException, Request, Response
import httpx
import os
import json
import ipaddress
from typing import Any
from .anthropic import anthropic_to_openai, openai_to_anthropic

DEFAULT_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1"

app = FastAPI()

API_KEY = os.getenv("QWEN_FASTAPI_API_KEY")
LISTEN_ENV = os.getenv("QWEN_FASTAPI_HOST", "local")
PORT = 3000
LISTEN = LISTEN_ENV
if ":" in LISTEN_ENV:
    try:
        LISTEN, port_str = LISTEN_ENV.rsplit(":", 1)
        PORT = int(port_str)
    except ValueError:
        pass
LOCAL_ONLY = LISTEN == "local"
HOST = "0.0.0.0" if LOCAL_ONLY else LISTEN
CERTFILE = os.getenv("QWEN_FASTAPI_CERTFILE")
KEYFILE = os.getenv("QWEN_FASTAPI_KEYFILE")

# Available Qwen models exposed by the proxy
MODELS = {
    "qwen3-coder-plus": {"id": "qwen3-coder-plus", "object": "model"},
    "qwen3-coder-flash": {"id": "qwen3-coder-flash", "object": "model"},
}

def is_local_address(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if addr.version == 4:
        nets = [
            ipaddress.ip_network("127.0.0.0/8"),
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("100.64.0.0/10"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("169.254.0.0/16"),
        ]
    else:
        nets = [
            ipaddress.ip_network("::1/128"),
            ipaddress.ip_network("fc00::/7"),
            ipaddress.ip_network("fe80::/10"),
        ]
    return any(addr in net for net in nets)


async def verify_api_key(req: Request) -> None:
    if LOCAL_ONLY and not is_local_address(req.client.host):
        raise HTTPException(status_code=403, detail="forbidden")
    if API_KEY and req.headers.get("X-API-Key") != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


def get_credentials() -> tuple[str, str]:
    """Read OAuth credentials from the standard qwen location."""
    path = os.path.join(os.path.expanduser("~"), ".qwen", "oauth_creds.json")
    with open(path) as f:
        data = json.load(f)
    token = data.get("access_token")
    if not token:
        raise ValueError("No access token")
    endpoint = data.get("resource_url") or DEFAULT_ENDPOINT
    return token, endpoint


async def forward(method: str, url: str, token: str, json_body: Any | None = None) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, json=json_body, headers=headers)
    return resp


@app.post("/v1/completions")
async def completions(req: Request, _=Depends(verify_api_key)) -> Response:
    try:
        body = await req.json()
    except Exception as e:  # JSON decode error
        raise HTTPException(status_code=500, detail=str(e))
    try:
        token, endpoint = get_credentials()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    upstream_resp = await forward("POST", f"{endpoint}/v1/completions", token, body)
    return Response(content=upstream_resp.content, status_code=upstream_resp.status_code, media_type="application/json")


@app.post("/v1/messages")
async def messages(req: Request, _=Depends(verify_api_key)) -> Response:
    try:
        original = await req.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        body = anthropic_to_openai(original)
        token, endpoint = get_credentials()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    upstream_resp = await forward("POST", f"{endpoint}/chat/completions", token, body)
    data = openai_to_anthropic(upstream_resp.json())
    return Response(content=json.dumps(data), status_code=upstream_resp.status_code, media_type="application/json")

@app.get("/v1/models")
async def list_models(_=Depends(verify_api_key)) -> dict:
    """Return the set of Qwen models available via the proxy."""
    return {"data": list(MODELS.values()), "object": "list"}


@app.get("/v1/models/{model}")
async def get_model(model: str, _=Depends(verify_api_key)) -> dict:
    info = MODELS.get(model)
    if not info:
        raise HTTPException(status_code=404, detail="model not found")
    return info

def main() -> None:
    import argparse
    import uvicorn

    global API_KEY, HOST, LOCAL_ONLY, LISTEN, PORT, CERTFILE, KEYFILE

    parser = argparse.ArgumentParser(description="Run the Qwen FastAPI proxy server")
    parser.add_argument(
        "--key",
        help="API key clients must supply in the X-API-Key header. Overrides QWEN_FASTAPI_API_KEY",
    )
    parser.add_argument(
        "--listen",
        default=LISTEN_ENV,
        help="IP address to listen on, optionally with :port. Use 'local' to only allow private network clients.",
    )
    parser.add_argument("--certfile", help="Path to TLS certificate file to enable HTTPS")
    parser.add_argument("--keyfile", help="Path to TLS private key file to enable HTTPS")
    args = parser.parse_args()
    if args.key:
        API_KEY = args.key
    listen_arg = args.listen
    port = PORT
    if ":" in listen_arg:
        try:
            listen_arg, port_str = listen_arg.rsplit(":", 1)
            port = int(port_str)
        except ValueError:
            parser.error(f"Invalid port in --listen: {port_str}")
    LISTEN = listen_arg
    PORT = port
    LOCAL_ONLY = LISTEN == "local"
    HOST = "0.0.0.0" if LOCAL_ONLY else LISTEN

    certfile = args.certfile or CERTFILE
    keyfile = args.keyfile or KEYFILE
    if certfile or keyfile:
        if not (certfile and keyfile):
            parser.error("--certfile and --keyfile must be provided together")
    CERTFILE = certfile
    KEYFILE = keyfile

    uvicorn.run(app, host=HOST, port=PORT, ssl_certfile=CERTFILE, ssl_keyfile=KEYFILE)


if __name__ == "__main__":
    main()
