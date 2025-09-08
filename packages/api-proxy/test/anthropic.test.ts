import { describe, it, expect } from 'vitest';
import { anthropicToOpenAI, openAIToAnthropic } from '../src/anthropic.js';

describe('anthropic conversions', () => {
  it('converts anthropic request to openai format', () => {
    const req = {
      model: 'qwen',
      max_tokens: 10,
      messages: [{ role: 'user', content: 'hi' }],
    };
    const converted = anthropicToOpenAI(req);
    expect(converted).toEqual({
      model: 'qwen',
      max_tokens: 10,
      messages: [{ role: 'user', content: 'hi' }],
    });
  });

  it('converts openai response to anthropic format', () => {
    const resp = {
      id: '1',
      model: 'qwen',
      choices: [{ message: { content: 'hello' } }],
      usage: { prompt_tokens: 1, completion_tokens: 2 },
    };
    const converted = openAIToAnthropic(resp);
    expect(converted.content[0].text).toBe('hello');
    expect(converted.usage).toEqual({ input_tokens: 1, output_tokens: 2 });
  });
});
