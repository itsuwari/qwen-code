import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import type { AddressInfo } from 'node:net';

// Preserve the real fetch for making requests to our local server
const realFetch = globalThis.fetch;
const upstreamFetch = vi.hoisted(() => vi.fn());
vi.stubGlobal('fetch', (url: any, init?: any) => {
  if (typeof url === 'string' && url.startsWith('http://localhost')) {
    return realFetch(url, init);
  }
  return upstreamFetch(url, init);
});

const getCreds = vi.hoisted(() => vi.fn());
vi.mock('@qwen-code/qwen-code-core/qwen/qwenOAuth2.js', () => ({
  QwenOAuth2Client: vi.fn().mockImplementation(() => ({})),
}));
vi.mock('@qwen-code/qwen-code-core/qwen/sharedTokenManager.js', () => ({
  SharedTokenManager: { getInstance: () => ({ getValidCredentials: getCreds }) },
}));

import { start } from '../src/server.js';
import type http from 'node:http';

describe('api proxy server', () => {
  let server: http.Server;

  beforeEach(() => {
    upstreamFetch.mockReset();
    getCreds.mockReset();
  });

  afterEach(() => {
    server?.close();
  });

  it('proxies completions with auth header', async () => {
    getCreds.mockResolvedValue({ access_token: 't', resource_url: 'https://upstream' });
    upstreamFetch.mockResolvedValue({ status: 200, json: async () => ({ ok: true }) });
    server = start(0);
    const port = (server.address() as AddressInfo).port;

    const resp = await realFetch(`http://localhost:${port}/v1/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'qwen', prompt: 'hi' }),
    });

    expect(await resp.json()).toEqual({ ok: true });
    expect(upstreamFetch).toHaveBeenCalledWith(
      'https://upstream/v1/completions',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer t' }),
      }),
    );
  });

  it('returns 500 on invalid JSON', async () => {
    getCreds.mockResolvedValue({ access_token: 't', resource_url: 'https://upstream' });
    server = start(0);
    const port = (server.address() as AddressInfo).port;

    const resp = await realFetch(`http://localhost:${port}/v1/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: 'not-json',
    });

    expect(resp.status).toBe(500);
    const body = await resp.json();
    expect(body.error).toBeTruthy();
  });

  it('forwards upstream error status', async () => {
    getCreds.mockResolvedValue({ access_token: 't', resource_url: 'https://upstream' });
    upstreamFetch.mockResolvedValue({ status: 401, json: async () => ({ error: 'unauthorized' }) });
    server = start(0);
    const port = (server.address() as AddressInfo).port;

    const resp = await realFetch(`http://localhost:${port}/v1/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'qwen', prompt: 'hi' }),
    });

    expect(resp.status).toBe(401);
    expect(await resp.json()).toEqual({ error: 'unauthorized' });
  });

  it('responds with 500 when auth missing', async () => {
    getCreds.mockResolvedValue({});
    server = start(0);
    const port = (server.address() as AddressInfo).port;

    const resp = await realFetch(`http://localhost:${port}/v1/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'qwen', prompt: 'hi' }),
    });

    expect(resp.status).toBe(500);
    const body = await resp.json();
    expect(body.error).toContain('No access token');
    expect(upstreamFetch).not.toHaveBeenCalled();
  });
});
