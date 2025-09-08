# Qwen FastAPI Proxy

This standalone server exposes Qwen models using both OpenAI `/v1/completions` and Anthropic `/v1/messages` formats.

## Usage

1. Ensure OAuth credentials exist at `~/.qwen/oauth_creds.json`.
2. Install dependencies:
    ```bash
    pip install -e qwenfastapi
    ```
3. Optional settings:
   - `QWEN_FASTAPI_HOST` — interface to bind (default `127.0.0.1`; use `0.0.0.0` to listen on all addresses).
   - `QWEN_FASTAPI_API_KEY` — value clients must provide in the `X-API-Key` header.
4. Start the server:
    ```bash
    qwenfastapi
    ```
    You can also run `python -m qwenfastapi.main`.
5. Call the proxy:
    ```bash
    curl -H "X-API-Key: $QWEN_FASTAPI_API_KEY" \
         -H "Content-Type: application/json" \
         -d '{"model":"qwen","prompt":"hi"}' \
         http://localhost:3000/v1/completions
    ```
