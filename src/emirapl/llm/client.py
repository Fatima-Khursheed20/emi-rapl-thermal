"""LLM provider setup.

All hosted providers are reached through the OpenAI-compatible chat API, so the
same code path serves Gemini (free tier), Groq (free tier), a local Ollama
server, or OpenAI. A `scripted` client returns deterministic expert-rule answers
from the structured context; it is used for offline tests/CI and as a sanity
check of the pipeline, never reported as an LLM result.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass

from ..contracts import LLMCallRecord

PROVIDERS = {
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "key_env": "GEMINI_API_KEY",
               "default_model": "gemini-2.5-flash", "min_interval_s": 6.5},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "key_env": "GROQ_API_KEY",
             "default_model": "llama-3.1-8b-instant", "min_interval_s": 2.1},
    "ollama": {"base_url": "http://localhost:11434/v1", "key_env": None,
               "default_model": "qwen2.5:7b", "min_interval_s": 0.0},
    "openai": {"base_url": None, "key_env": "OPENAI_API_KEY",
               "default_model": "gpt-4.1-mini", "min_interval_s": 0.0},
}


@dataclass
class LLMResponse:
    text: str
    record: LLMCallRecord


def extract_json(text: str) -> dict:
    """Parse the first JSON object in a model reply (tolerates code fences / prose)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start, depth = text.find("{"), 0
    if start < 0:
        raise ValueError("no JSON object in reply")
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unterminated JSON object in reply")


class LLMClient:
    """Thin OpenAI-compatible client with rate limiting, retries and token accounting."""

    def __init__(self, provider: str, model: str | None = None, temperature: float = 0.2,
                 max_retries: int = 5, min_interval_s: float | None = None, max_tokens: int = 1024):
        from openai import OpenAI  # imported lazily so the scripted client needs no network deps

        cfg = PROVIDERS[provider]
        key = os.environ.get(cfg["key_env"], "") if cfg["key_env"] else "ollama"
        if cfg["key_env"] and not key:
            raise RuntimeError(f"{cfg['key_env']} is not set (see .env.example)")
        self.provider = provider
        self.model = model or cfg["default_model"]
        self.temperature = temperature
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.min_interval_s = cfg["min_interval_s"] if min_interval_s is None else min_interval_s
        self._client = OpenAI(api_key=key, base_url=cfg["base_url"]) if cfg["base_url"] else OpenAI(api_key=key)
        self._last_call = 0.0

    @property
    def name(self) -> str:
        return f"{self.provider}:{self.model}"

    def complete(self, agent: str, messages: list[dict], context: dict | None = None) -> LLMResponse:
        wait = self.min_interval_s - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        err = None
        for attempt in range(self.max_retries):
            t0 = time.time()
            try:
                resp = self._client.chat.completions.create(
                    model=self.model, messages=messages, temperature=self.temperature,
                    max_tokens=self.max_tokens, response_format={"type": "json_object"})
                self._last_call = time.time()
                usage = getattr(resp, "usage", None)
                rec = LLMCallRecord(agent=agent, model=self.name, latency_s=round(self._last_call - t0, 3),
                                    tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
                                    tokens_out=getattr(usage, "completion_tokens", 0) or 0)
                return LLMResponse(resp.choices[0].message.content or "", rec)
            except Exception as e:  # rate limits / transient errors: exponential backoff
                err = str(e)
                self._last_call = time.time()
                time.sleep(min(60.0, 2.0 * 2 ** attempt))
        rec = LLMCallRecord(agent=agent, model=self.name, latency_s=0.0, ok=False, error=err)
        return LLMResponse("", rec)


class ScriptedLLM:
    """Deterministic stand-in that answers from the structured context (offline tests/CI).

    It encodes simple expert rules with *nominal* fault magnitudes, i.e. what a
    reasonable engineer would propose without knowing the true fault size.
    """

    name = "scripted:rules"

    def complete(self, agent: str, messages: list[dict], context: dict | None = None) -> LLMResponse:
        from ..baselines.rules import rule_action, rule_mode

        ctx = context or {}
        t0 = time.time()
        if agent == "planner":
            out = {"target_mode": rule_mode(ctx["fault_report"], ctx["snapshot"]).value,
                   "rationale": "scripted rule"}
        else:
            act = rule_action(ctx["fault_report"], ctx["snapshot"], ctx.get("mode"), ctx.get("feedback"))
            out = json.loads(act.model_dump_json())
        text = json.dumps(out)
        rec = LLMCallRecord(agent=agent, model=self.name, latency_s=round(time.time() - t0, 4),
                            tokens_in=sum(len(m["content"]) for m in messages) // 4, tokens_out=len(text) // 4)
        return LLMResponse(text, rec)


def make_llm(provider: str, model: str | None = None, **kw):
    if provider == "scripted":
        return ScriptedLLM()
    return LLMClient(provider, model, **kw)
