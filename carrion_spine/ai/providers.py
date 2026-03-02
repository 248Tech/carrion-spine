"""Pluggable LLM providers (stdlib only). AI never applies changes; output goes through same pipeline as human edits."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Protocol


class LLMProvider(Protocol):
    """Protocol for AI suggest providers. Patch = unified diff only; full = file content only."""

    async def generate_patch(
        self,
        instruction: str,
        baseline_content: str,
        filename: str,
        temperature: float,
        max_output_bytes: int,
    ) -> str:
        ...

    async def generate_full(
        self,
        instruction: str,
        baseline_content: str,
        filename: str,
        temperature: float,
        max_output_bytes: int,
    ) -> str:
        ...


def _do_http_post(url: str, headers: dict[str, str], body: bytes) -> bytes:
    """Sync HTTP POST using urllib (run in thread from async)."""
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _parse_chat_completion_response(raw: bytes) -> str:
    """Extract first choice message content from OpenAI-style chat completion JSON."""
    data = json.loads(raw.decode("utf-8"))
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("No choices in response")
    msg = choices[0].get("message") or {}
    content = msg.get("content") or ""
    return content.strip()


class OpenAIProvider:
    """OpenAI-compatible API (stdlib only). TODO: production error handling, retries."""

    def __init__(self, api_key_env: str = "OPENAI_API_KEY", model: str = "gpt-4o-mini") -> None:
        self.api_key_env = api_key_env
        self.model = model
        self._url = "https://api.openai.com/v1/chat/completions"

    async def generate_patch(
        self,
        instruction: str,
        baseline_content: str,
        filename: str,
        temperature: float,
        max_output_bytes: int,
    ) -> str:
        import asyncio
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ValueError(f"Missing {self.api_key_env}")
        system = (
            "You output ONLY a valid unified diff for a single file. "
            "No markdown, no explanation, no other text. Start with --- and +++ lines."
        )
        user = f"File: {filename}\n\nCurrent content:\n{baseline_content}\n\nInstruction: {instruction}"
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": min(4096, max_output_bytes // 4),
        }).encode("utf-8")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, lambda: _do_http_post(self._url, headers, body))
        return _parse_chat_completion_response(raw)

    async def generate_full(
        self,
        instruction: str,
        baseline_content: str,
        filename: str,
        temperature: float,
        max_output_bytes: int,
    ) -> str:
        import asyncio
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ValueError(f"Missing {self.api_key_env}")
        system = (
            "You output ONLY the complete file content. No markdown fences, no commentary, no explanation."
        )
        user = f"File: {filename}\n\nCurrent content:\n{baseline_content}\n\nInstruction: {instruction}"
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": min(4096, max_output_bytes // 4),
        }).encode("utf-8")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, lambda: _do_http_post(self._url, headers, body))
        return _parse_chat_completion_response(raw)


class LocalHTTPProvider:
    """Local HTTP chat completion endpoint (e.g. Ollama). Stdlib only."""

    def __init__(self, url: str, model: str = "llama3.1") -> None:
        self.url = url.rstrip("/")
        self.model = model

    async def generate_patch(
        self,
        instruction: str,
        baseline_content: str,
        filename: str,
        temperature: float,
        max_output_bytes: int,
    ) -> str:
        import asyncio
        system = (
            "You output ONLY a valid unified diff for a single file. "
            "No markdown, no explanation. Start with --- and +++ lines."
        )
        user = f"File: {filename}\n\nCurrent content:\n{baseline_content}\n\nInstruction: {instruction}"
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "stream": False,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None, lambda: _do_http_post(self.url, headers, body)
        )
        return _parse_chat_completion_response(raw)

    async def generate_full(
        self,
        instruction: str,
        baseline_content: str,
        filename: str,
        temperature: float,
        max_output_bytes: int,
    ) -> str:
        import asyncio
        system = "You output ONLY the complete file content. No markdown, no commentary."
        user = f"File: {filename}\n\nCurrent content:\n{baseline_content}\n\nInstruction: {instruction}"
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "stream": False,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None, lambda: _do_http_post(self.url, headers, body)
        )
        return _parse_chat_completion_response(raw)


def get_provider(ai_config: "AIConfig") -> LLMProvider:
    """Build the configured LLM provider. allow_external is enforced in config load."""
    from ..config_loader import AIConfig
    if ai_config.provider == "openai":
        return OpenAIProvider(
            api_key_env=ai_config.openai_api_key_env,
            model=ai_config.openai_model,
        )
    return LocalHTTPProvider(
        url=ai_config.local_http_url,
        model=ai_config.local_http_model,
    )
