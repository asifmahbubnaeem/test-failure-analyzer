"""Minimal Ollama client (standard library only). Local models cost nothing per call."""

import http.client
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class Reply:
    content: str
    seconds: float
    prompt_tokens: int
    output_tokens: int


class Ollama:
    def __init__(self, model: str = "qwen3:8b", url: str = "http://localhost:11434", timeout: int = 900):
        self.model, self.url, self.timeout = model, url.rstrip("/"), timeout

    def chat(self, messages: list[dict], json_schema: dict | None = None, think: bool = False) -> Reply:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": think,
            "options": {"temperature": 0},  # same input, same answer: evals must be repeatable
        }
        if json_schema is not None:
            body["format"] = json_schema  # Ollama constrains the output to this schema
        req = urllib.request.Request(
            f"{self.url}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.load(r)
        except (urllib.error.URLError, http.client.HTTPException, OSError, json.JSONDecodeError) as e:
            # A dropped connection or a bad reply fails this one case, not the whole eval run.
            raise RuntimeError(f"Ollama call failed ({self.url}): {e}") from e
        return Reply(
            content=data.get("message", {}).get("content", ""),
            seconds=round(time.time() - t0, 2),
            prompt_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )
