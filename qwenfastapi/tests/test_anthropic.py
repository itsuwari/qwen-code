import pytest
from qwenfastapi.anthropic import anthropic_to_openai, openai_to_anthropic


def test_anthropic_to_openai():
    req = {
        "model": "qwen",
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "hi"}],
    }
    converted = anthropic_to_openai(req)
    assert converted == {
        "model": "qwen",
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "hi"}],
    }


def test_openai_to_anthropic():
    resp = {
        "id": "1",
        "model": "qwen",
        "choices": [{"message": {"content": "hello"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2},
    }
    converted = openai_to_anthropic(resp)
    assert converted["content"][0]["text"] == "hello"
    assert converted["usage"] == {"input_tokens": 1, "output_tokens": 2}
