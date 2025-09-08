import http from 'node:http';
import { URL } from 'node:url';
import { QwenOAuth2Client } from '@qwen-code/qwen-code-core/qwen/qwenOAuth2.js';
import { SharedTokenManager } from '@qwen-code/qwen-code-core/qwen/sharedTokenManager.js';
import { anthropicToOpenAI, openAIToAnthropic } from './anthropic.js';

const client = new QwenOAuth2Client();
const manager = SharedTokenManager.getInstance();
const DEFAULT_ENDPOINT = 'https://dashscope.aliyuncs.com/compatible-mode/v1';

async function getAuth() {
  const creds = await manager.getValidCredentials(client);
  if (!creds.access_token) throw new Error('No access token');
  const endpoint = creds.resource_url || DEFAULT_ENDPOINT;
  return { token: creds.access_token, endpoint };
}

function readBody(req: http.IncomingMessage): Promise<any> {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => (data += chunk));
    req.on('end', () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (e) {
        reject(e);
      }
    });
    req.on('error', reject);
  });
}

async function handleRequest(req: http.IncomingMessage, res: http.ServerResponse) {
  const url = new URL(req.url || '/', 'http://localhost');
  try {
    if (req.method === 'POST' && url.pathname === '/v1/completions') {
      const body = await readBody(req);
      const { token, endpoint } = await getAuth();
      const apiResp = await fetch(`${endpoint}${url.pathname}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
      const data = await apiResp.json();
      res.writeHead(apiResp.status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(data));
      return;
    }
    if (req.method === 'POST' && url.pathname === '/v1/messages') {
      const body = anthropicToOpenAI(await readBody(req));
      const { token, endpoint } = await getAuth();
      const apiResp = await fetch(`${endpoint}/chat/completions`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
      const data = openAIToAnthropic(await apiResp.json());
      res.writeHead(apiResp.status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(data));
      return;
    }
    if (req.method === 'GET' && url.pathname === '/v1/models') {
      const { token, endpoint } = await getAuth();
      const apiResp = await fetch(`${endpoint}/models`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await apiResp.json();
      res.writeHead(apiResp.status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(data));
      return;
    }
    if (req.method === 'GET' && url.pathname.startsWith('/v1/models/')) {
      const model = url.pathname.split('/').pop();
      const { token, endpoint } = await getAuth();
      const apiResp = await fetch(`${endpoint}/models/${model}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await apiResp.json();
      res.writeHead(apiResp.status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(data));
      return;
    }
    res.writeHead(404);
    res.end();
  } catch (err) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: (err as Error).message }));
  }
}

export function start(port = 3000) {
  const server = http.createServer(handleRequest);
  server.listen(port, () => {
    console.log(`API proxy listening on port ${port}`);
  });
  return server;
}

if (process.env.NODE_ENV !== 'test') {
  start();
}
