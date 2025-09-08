# Qwen FastAPI Proxy

This standalone server exposes Qwen models using OpenAI `/v1/completions` and `/v1/chat/completions` as well as Anthropic `/v1/messages` formats.

## Usage

1. Ensure OAuth credentials exist at `~/.qwen/oauth_creds.json`.
2. Install dependencies:
    ```bash
    pip install -e qwenfastapi
    ```
3. Optional settings:
   - `QWEN_FASTAPI_HOST` — interface and optional port to bind (default `local`, which only allows clients from private or link-local networks such as `10.0.0.0/8`, `100.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fc00::/7`, and `fe80::/10`; use an explicit IP such as `0.0.0.0` to accept any address). The server listens on port `3000` unless a different port is supplied, e.g. `0.0.0.0:8080`.
   - `QWEN_FASTAPI_API_KEY` — value clients must provide in the `X-API-Key` header. Local or private network clients are not validated against this key, but public clients must supply the correct value.
   - `QWEN_FASTAPI_CERTFILE` / `QWEN_FASTAPI_KEYFILE` — paths to TLS certificate and private key to enable HTTPS.
   - These can also be supplied on the command line with `--listen`, `--key`, `--certfile` and `--keyfile`.
4. Start the server:
    ```bash
    qwenfastapi --help
    qwenfastapi --listen 0.0.0.0:3000 --key "$QWEN_FASTAPI_API_KEY"
    # With HTTPS
    qwenfastapi --listen 0.0.0.0:3000 --certfile cert.pem --keyfile key.pem
    ```
    You can also run `python -m qwenfastapi.main`.
   The proxy speaks plain HTTP by default; use `http://` URLs unless HTTPS is configured.
5. Call the proxy:
    ```bash
    curl -H "X-API-Key: $QWEN_FASTAPI_API_KEY" \
         -H "Content-Type: application/json" \
         -d '{"model":"qwen","prompt":"hi"}' \
         http://localhost:3000/v1/completions
    ```

    Chat completions use the OpenAI format:

    ```bash
    curl -H "X-API-Key: $QWEN_FASTAPI_API_KEY" \
         -H "Content-Type: application/json" \
         -d '{"messages":[{"role":"user","content":"hi"}]}' \
         http://localhost:3000/v1/chat/completions
    ```

    If you omit the `model` field or specify an unsupported model, the proxy falls back to a default such as `qwen3-coder-plus`.

    To inspect available models:

    ```bash
    curl -H "X-API-Key: $QWEN_FASTAPI_API_KEY" \
         http://localhost:3000/v1/models
    ```
    which returns entries such as `qwen3-coder-plus` and `qwen3-coder-flash`.
