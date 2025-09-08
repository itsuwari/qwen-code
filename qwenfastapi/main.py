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
LISTEN = os.getenv("QWEN_FASTAPI_HOST", "local")
LOCAL_ONLY = LISTEN == "local"
HOST = "0.0.0.0" if LOCAL_ONLY else LISTEN

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
async def list_models(_=Depends(verify_api_key)) -> Response:
    try:
        token, endpoint = get_credentials()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    resp = await forward("GET", f"{endpoint}/models", token)
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@app.get("/v1/models/{model}")
async def get_model(model: str, _=Depends(verify_api_key)) -> Response:
    try:
        token, endpoint = get_credentials()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    resp = await forward("GET", f"{endpoint}/models/{model}", token)
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")

def main() -> None:
    import argparse
    import uvicorn

    global API_KEY, HOST, LOCAL_ONLY, LISTEN

    parser = argparse.ArgumentParser(description="Run the Qwen FastAPI proxy server")
    parser.add_argument(
        "--key",
        help="API key clients must supply in the X-API-Key header. Overrides QWEN_FASTAPI_API_KEY",
    )
    parser.add_argument(
        "--listen",
        default=LISTEN,
        help="IP address to listen on. Use 'local' to only allow private network clients.",
    )
    args = parser.parse_args()
    if args.key:
        API_KEY = args.key
    LISTEN = args.listen
    LOCAL_ONLY = LISTEN == "local"
    HOST = "0.0.0.0" if LOCAL_ONLY else LISTEN

    uvicorn.run(app, host=HOST, port=3000)


if __name__ == "__main__":
    main()
