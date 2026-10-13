import json
import sys
import unittest
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from deepseek_provider import (  # noqa: E402
    DeepSeekAPIError,
    build_request,
    call_chat_completion,
    extract_content,
)


class _Response:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class DeepSeekProviderTests(unittest.TestCase):
    def test_build_request_disables_thinking_and_keeps_sampling_parameters(self):
        request = build_request(
            "secret",
            [{"role": "user", "content": "题目"}],
            model="deepseek-flash",
            temperature=0.7,
            thinking="disabled",
            max_tokens=3000,
        )

        self.assertEqual(request.full_url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "deepseek-flash")
        self.assertEqual(payload["temperature"], 0.7)
        self.assertEqual(payload["thinking"], {"type": "disabled"})

    def test_call_chat_completion_extracts_visible_content_and_usage(self):
        captured = {}

        def opener(request, timeout):
            captured["timeout"] = timeout
            captured["request"] = request
            return _Response(
                {
                    "model": "deepseek-flash",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "最终文案"},
                        }
                    ],
                    "usage": {"total_tokens": 42},
                }
            )

        result = call_chat_completion(
            "secret",
            [{"role": "user", "content": "题目"}],
            urlopen=opener,
        )

        self.assertEqual(result["content"], "最终文案")
        self.assertEqual(result["model"], "deepseek-flash")
        self.assertEqual(result["usage"]["total_tokens"], 42)
        self.assertEqual(captured["timeout"], 180)

    def test_http_failure_does_not_leak_response_body(self):
        def opener(request, timeout):
            raise HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                hdrs=None,
                fp=BytesIO(b"secret-like provider response"),
            )

        with self.assertRaises(DeepSeekAPIError) as error:
            call_chat_completion(
                "secret",
                [{"role": "user", "content": "题目"}],
                urlopen=opener,
            )

        self.assertIn("HTTP 401", str(error.exception))
        self.assertNotIn("secret-like provider response", str(error.exception))

    def test_extract_content_rejects_empty_model_output(self):
        with self.assertRaises(DeepSeekAPIError):
            extract_content({"choices": [{"message": {"content": "  "}}]})


if __name__ == "__main__":
    unittest.main()
