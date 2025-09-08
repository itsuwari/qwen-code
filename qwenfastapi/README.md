# Qwen FastAPI Proxy

This standalone server exposes Qwen models using both OpenAI `/v1/completions` and Anthropic `/v1/messages` formats.

## Usage

1. Ensure OAuth credentials exist at `~/.qwen/oauth_creds.json`.
2. Install dependencies:
    ```bash
    pip install -e qwenfastapi
    ```
3. Optional settings:
   - `QWEN_FASTAPI_HOST` — interface to bind (default `local`, which only allows clients from private or link-local networks such as `10.0.0.0/8`, `100.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fc00::/7`, and `fe80::/10`; use an explicit IP such as `0.0.0.0` to accept any address).
   - `QWEN_FASTAPI_API_KEY` — value clients must provide in the `X-API-Key` header.
   - These can also be supplied on the command line with `--listen` and `--key`.
4. Start the server:
    ```bash
    qwenfastapi --help
    qwenfastapi --listen local --key "$QWEN_FASTAPI_API_KEY"
    ```
    You can also run `python -m qwenfastapi.main`.
5. Call the proxy:
    ```bash
    curl -H "X-API-Key: $QWEN_FASTAPI_API_KEY" \
         -H "Content-Type: application/json" \
         -d '{"model":"qwen","prompt":"hi"}' \
         http://localhost:3000/v1/completions
    ```
