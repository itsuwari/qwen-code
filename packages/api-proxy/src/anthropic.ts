export interface AnthropicMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AnthropicRequest {
  model: string;
  max_tokens?: number;
  messages: AnthropicMessage[];
}

/** Convert an Anthropic messages request to OpenAI chat completion format */
export function anthropicToOpenAI(req: AnthropicRequest): any {
  return {
    model: req.model,
    max_tokens: req.max_tokens,
    messages: req.messages.map((m) => ({ role: m.role, content: m.content })),
  };
}

/** Convert an OpenAI chat completion response to Anthropic message format */
export function openAIToAnthropic(resp: any): any {
  const text = resp?.choices?.[0]?.message?.content ?? '';
  const usage = resp?.usage
    ? {
        input_tokens: resp.usage.prompt_tokens,
        output_tokens: resp.usage.completion_tokens,
      }
    : undefined;
  return {
    id: resp.id,
    type: 'message',
    role: 'assistant',
    model: resp.model,
    content: [{ type: 'text', text }],
    usage,
  };
}
