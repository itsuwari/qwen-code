# API Proxy

A standalone HTTP server that reuses Qwen OAuth credentials to expose the Qwen API using familiar OpenAI and Anthropic formats.

## Authentication

The proxy reads the OAuth token produced by the Qwen Code CLI. After logging in with the CLI, credentials are stored in `~/.qwen/oauth_creds.json` and automatically refreshed when needed.

## Usage

1. **Install dependencies**
   ```bash
   npm install
   ```
2. **Start the server**
   ```bash
   cd packages/api-proxy
   npm start
   ```
3. **Call the endpoints**
   - OpenAI-compatible:
     ```bash
     curl http://localhost:3000/v1/completions -H 'Content-Type: application/json' \
       -d '{"model":"qwen-max","prompt":"hi"}'
     ```
   - Anthropic-compatible:
     ```bash
     curl http://localhost:3000/v1/messages -H 'Content-Type: application/json' \
       -d '{"model":"qwen-max","messages":[{"role":"user","content":"hi"}]}'
     ```

Model metadata is available at `/v1/models` and `/v1/models/{id}`.

## Notes
- The proxy runs independently from the main Qwen Code application.
- It simply forwards requests using the stored OAuth token; no API keys are required.
