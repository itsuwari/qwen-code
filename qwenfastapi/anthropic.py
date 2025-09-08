from typing import Any, Dict, List

# Define types for clarity
AnthropicMessage = Dict[str, str]
AnthropicRequest = Dict[str, Any]


def anthropic_to_openai(req: AnthropicRequest) -> Dict[str, Any]:
    """Convert an Anthropic-style messages request to OpenAI chat format."""
    return {
        "model": req.get("model"),
        "max_tokens": req.get("max_tokens"),
        "messages": [
            {"role": m.get("role"), "content": m.get("content")}
            for m in req.get("messages", [])
        ],
    }


def openai_to_anthropic(resp: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an OpenAI chat completion response to Anthropic message format."""
    message = resp.get("choices", [{}])[0].get("message", {})
    text = message.get("content", "")
    usage = resp.get("usage")
    anth_usage = (
        {
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
        }
        if usage
        else None
    )
    result = {
        "id": resp.get("id"),
        "type": "message",
        "role": "assistant",
        "model": resp.get("model"),
        "content": [{"type": "text", "text": text}],
    }
    if anth_usage:
        result["usage"] = anth_usage
    return result
