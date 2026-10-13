"""Small standard-library adapter for DeepSeek's OpenAI-compatible API."""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen as default_urlopen


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"
DEFAULT_TIMEOUT = 180


class DeepSeekAPIError(RuntimeError):
    """Raised when DeepSeek rejects a request or returns an invalid response."""


def build_request(
    api_key: str,
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    thinking: str = "disabled",
    max_tokens: int = 3000,
    base_url: str = DEFAULT_BASE_URL,
) -> Request:
    if not api_key.strip():
        raise DeepSeekAPIError("DEEPSEEK_API_KEY is empty")
    if thinking not in {"enabled", "disabled"}:
        raise DeepSeekAPIError("thinking must be enabled or disabled")
    if temperature < 0 or temperature > 2:
        raise DeepSeekAPIError("temperature must be between 0 and 2")
    if max_tokens <= 0:
        raise DeepSeekAPIError("max_tokens must be positive")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "thinking": {"type": thinking},
        "max_tokens": max_tokens,
        "stream": False,
    }
    # DeepSeek documents temperature as ineffective in thinking mode. Keeping
    # it out of that request makes the recorded experiment honest.
    if thinking == "disabled":
        payload["temperature"] = temperature

    return Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )


def extract_content(response: object) -> str:
    if not isinstance(response, dict):
        raise DeepSeekAPIError("response is not a JSON object")
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise DeepSeekAPIError("response contains no choices")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise DeepSeekAPIError("response contains no visible message content")
    content = message["content"].strip()
    if not content:
        raise DeepSeekAPIError("model returned empty visible content")
    return content


def call_chat_completion(
    api_key: str,
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    thinking: str = "disabled",
    max_tokens: int = 3000,
    timeout: int = DEFAULT_TIMEOUT,
    base_url: str = DEFAULT_BASE_URL,
    urlopen: Callable[..., object] = default_urlopen,
) -> dict[str, object]:
    request = build_request(
        api_key,
        messages,
        model=model,
        temperature=temperature,
        thinking=thinking,
        max_tokens=max_tokens,
        base_url=base_url,
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # type: ignore[operator]
            raw = response.read()
    except HTTPError as exc:
        raise DeepSeekAPIError(f"DeepSeek request failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise DeepSeekAPIError("DeepSeek request failed due to a network error") from exc

    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeepSeekAPIError("DeepSeek returned invalid JSON") from exc

    content = extract_content(decoded)
    choices = decoded.get("choices", []) if isinstance(decoded, dict) else []
    first_choice = choices[0] if choices and isinstance(choices[0], dict) else {}
    return {
        "content": content,
        "model": decoded.get("model") if isinstance(decoded, dict) else None,
        "usage": decoded.get("usage", {}) if isinstance(decoded, dict) else {},
        "finish_reason": first_choice.get("finish_reason"),
    }
