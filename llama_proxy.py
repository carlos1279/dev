import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import requests

HOST = os.getenv("LlamaProxy_HOST", "127.0.0.1")
PORT = int(os.getenv("LlamaProxy_PORT", "4000"))
API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
API_KEY = os.getenv("GROQ_API_KEY", "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")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))


def _safe_int(value: Any, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


class ProxyHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rdo if False else self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON")

    def _to_openai_messages(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if isinstance(body.get("system"), str) and body.get("system"):
            messages.append({"role": "system", "content": body["system"]})

        for msg in body.get("messages", []) or []:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        parts.append(part)
                content = "\n".join(p for p in parts if p)
            messages.append({"role": role, "content": content})
        return messages

    def _forward_to_groq(self, body: dict[str, Any]) -> requests.Response:
        model = body.get("model") or DEFAULT_MODEL
        requested = body.get("max_tokens") or body.get("max_completion_tokens") or body.get("max_output_tokens") or MAX_TOKENS
        capped = min(_safe_int(requested, MAX_TOKENS), MAX_TOKENS)
        payload = {
            "model": model,
            "messages": self._to_openai_messages(body),
            "max_tokens": capped,
            "temperature": body.get("temperature", 0.7),
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        return requests.post(f"{API_BASE.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=60)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/health"}:
            self._send_json(200, {"status": "ok", "model": DEFAULT_MODEL})
        elif self.path == "/v1/models":
            self._send_json(200, {
                "data": [{"id": DEFAULT_MODEL, "object": "model", "created": 0, "owned_by": "groq"}],
                "object": "list",
            })
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            body = self._read_json()
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        if self.path in {"/chat/completions", "/v1/chat/completions"}:
            try:
                response = self._forward_to_groq(body)
                response.raise_for_status()
                self._send_json(response.status_code, response.json())
            except requests.RequestException as exc:
                self._send_json(502, {"error": str(exc)})
            return

        if self.path == "/v1/messages":
            try:
                response = self._forward_to_groq(body)
                response.raise_for_status()
                data = response.json()
                choice = data.get("choices", [{}])[0].get("message", {})
                content = choice.get("content", "") or ""
                self._send_json(200, {
                    "id": data.get("id", "msg_local"),
                    "type": "message",
                    "role": "assistant",
                    "model": body.get("model") or DEFAULT_MODEL,
                    "content": [{"type": "text", "text": content}],
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "output_tokens": data.get("usage", {}).get("completion_tokens", 0),
                    },
                })
            except requests.RequestException as exc:
                self._send_json(502, {"error": str(exc)})
            return

        self._send_json(404, {"error": "Not found"})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ProxyHandler)
    print(f"Llama proxy listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
