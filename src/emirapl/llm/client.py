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
from math import isfinite

from ..contracts import LLMCallRecord

PROVIDERS = {
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "key_env": "GEMINI_API_KEY",
               "default_model": "gemini-flash-latest", "min_interval_s": 6.5},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "key_env": "GROQ_API_KEY",
             "default_model": "openai/gpt-oss-20b", "min_interval_s": 1.0, "tpm_budget": 7200},
    "ollama": {"base_url": "http://localhost:11434/v1", "key_env": None,
               "default_model": "qwen2.5:7b", "min_interval_s": 0.0},
    "openai": {"base_url": None, "key_env": "OPENAI_API_KEY",
               "default_model": "gpt-4.1-mini", "min_interval_s": 0.0},
}


class ProviderError(RuntimeError):
    """An infrastructure or configuration error prevents a valid live episode."""


class QuotaExhausted(ProviderError):
    """The provider's daily quota is used up; the evaluation run must stop and be resumed later."""


@dataclass
class LLMResponse:
    text: str
    record: LLMCallRecord


def extract_json(text: str) -> dict:
    """Accept one complete top-level object, optionally wrapped in prose or a fence."""
    def unique_pairs(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("duplicate key in model JSON")
        return result

    def reject_constant(value):
        raise ValueError(f"non-finite JSON constant {value}")

    start = re.search(r"[\[{]", text)
    if start is None or start.group() != "{":
        raise ValueError("expected a top-level JSON object")
    decoder = json.JSONDecoder(object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    value, end = decoder.raw_decode(text, start.start())
    if re.search(r"[\[{]", text[end:]):
        raise ValueError("unexpected additional JSON in reply")
    return value


def _error_details(error):
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        body = body.get("error", body)
    return body if isinstance(body, dict) else {}


def _retry_delay(error, attempt):
    response = getattr(error, "response", None)
    header = response.headers.get("retry-after") if response is not None else None
    try:
        seconds = float(header)
        if isfinite(seconds) and seconds >= 0:
            return seconds
    except (TypeError, ValueError):
        pass
    return min(60., 2. ** attempt)


class LLMClient:
    """Thin OpenAI-compatible client with rate limiting, retries and token accounting."""

    def __init__(self, provider: str, model: str | None = None, temperature: float = 0.2,
                 max_retries: int = 7, min_interval_s: float | None = None, max_tokens: int = 2048,
                 reasoning_effort: str | None = "low"):
        from openai import OpenAI  # imported lazily so the scripted client needs no network deps

        cfg = PROVIDERS[provider]
        key = os.environ.get(cfg["key_env"], "").strip() if cfg["key_env"] else "ollama"
        if cfg["key_env"] and (not key or key.lower() in {"your_key", "your_key_here", "paste_your_key_here"}):
            raise ProviderError(f"Set {cfg['key_env']} in .env before running {provider}.")
        self.provider = provider
        self.model = model or cfg["default_model"]
        self.temperature = temperature
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.min_interval_s = cfg["min_interval_s"] if min_interval_s is None else min_interval_s
        self.tpm_budget = cfg.get("tpm_budget")
        # reasoning models (gpt-oss) spend output tokens on hidden reasoning; "low" keeps calls cheap
        self.extra_body = {"reasoning_effort": reasoning_effort} if reasoning_effort and "gpt-oss" in self.model else {}
        if provider == "groq":
            self.extra_body["max_completion_tokens"] = self.max_tokens
        # bounded timeout and no hidden SDK retries: a hung request must not stall an evaluation run
        kw = {"timeout": 90.0, "max_retries": 0}
        self._client = OpenAI(api_key=key, base_url=cfg["base_url"], **kw) if cfg["base_url"] else OpenAI(api_key=key, **kw)
        self._last_call = 0.0
        self._usage: list[tuple[float, int]] = []  # (time, tokens) for the tokens-per-minute budget

    @property
    def name(self) -> str:
        return f"{self.provider}:{self.model}"

    def _pace(self, messages: list[dict]) -> None:
        wait = self.min_interval_s - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        if not self.tpm_budget:
            return
        est = sum(len(m["content"]) for m in messages) // 3 + 600  # prompt + typical completion
        while True:
            now = time.monotonic()
            self._usage = [(t, n) for t, n in self._usage if now - t < 60.0]
            if not self._usage or sum(n for _, n in self._usage) + est <= self.tpm_budget:
                return
            time.sleep(min(5.0, 60.0 - (now - self._usage[0][0]) + 0.5))

    def complete(self, agent: str, messages: list[dict], context: dict | None = None) -> LLMResponse:
        from openai import APIConnectionError, APIStatusError

        started = time.monotonic()
        api_seconds = 0.0
        json_mode = True
        for attempt in range(1, self.max_retries + 1):
            self._pace(messages)
            kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
            if self.provider != "groq":
                kwargs["max_tokens"] = self.max_tokens
            if self.extra_body:
                kwargs["extra_body"] = self.extra_body
            t0 = time.monotonic()
            try:
                resp = self._client.chat.completions.create(
                    model=self.model, messages=messages, temperature=self.temperature,
                    **kwargs)
            except (APIStatusError, APIConnectionError) as error:
                self._last_call = time.monotonic()
                api_seconds += self._last_call - t0
                status = getattr(error, "status_code", None)
                details = _error_details(error)
                code = str(details.get("code") or getattr(error, "code", "")).lower()
                message = str(details.get("message", "")).lower()
                if status == 429 and (code == "insufficient_quota" or
                                      any(word in message for word in ("per day", "daily", "(tpd)", "(rpd)"))):
                    raise QuotaExhausted(f"{self.name}: daily or account quota reached. Resume after quota resets.") from None
                if status == 400 and (code == "json_validate_failed" or
                                      (json_mode and "response_format" in message and "json" in message)):
                    if json_mode and attempt < self.max_retries:
                        json_mode = False
                        continue
                    return LLMResponse("", LLMCallRecord(
                        agent=agent, model=self.name, latency_s=round(self._last_call - started, 3),
                        api_attempts=attempt, api_latency_s=round(api_seconds, 3),
                        ok=False, error="provider rejected generated JSON"))
                transient = status is None or status in (408, 409, 429, 498) or status >= 500
                label = f"HTTP {status}" if status is not None else "connection or timeout error"
                if not transient:
                    raise ProviderError(f"{self.name}: {label}. Check the key, model access and request settings.") from None
                delay = _retry_delay(error, attempt)
                if attempt == self.max_retries or delay > 120:
                    raise ProviderError(f"{self.name}: {label} after {attempt} attempt(s). Resume when the API is available.") from None
                time.sleep(delay)
                continue
            self._last_call = time.monotonic()
            api_seconds += self._last_call - t0
            if not getattr(resp, "choices", None):
                raise ProviderError(f"{self.name}: the API returned no choices. Resume when the API is available.")
            choice = resp.choices[0]
            usage = getattr(resp, "usage", None)
            tokens_in = getattr(usage, "prompt_tokens", None)
            tokens_out = getattr(usage, "completion_tokens", None)
            usage_reported = all(type(value) is int and value >= 0 for value in (tokens_in, tokens_out))
            finish = getattr(choice, "finish_reason", None)
            content = getattr(choice.message, "content", None)
            valid = isinstance(content, str) and bool(content.strip()) and finish in (None, "stop")
            returned = getattr(resp, "model", None)
            if self.provider == "groq" and returned and returned != self.model:
                raise ProviderError(f"{self.name}: the API returned a different model. Check the model setting.")
            record = LLMCallRecord(
                agent=agent, model=self.name, latency_s=round(self._last_call - started, 3),
                tokens_in=tokens_in if usage_reported else 0, tokens_out=tokens_out if usage_reported else 0,
                api_attempts=attempt, api_latency_s=round(api_seconds, 3), usage_reported=usage_reported,
                returned_model=returned, system_fingerprint=getattr(resp, "system_fingerprint", None),
                finish_reason=finish, ok=valid, error=None if valid else "incomplete or empty model response",
            )
            if self.tpm_budget:
                used = record.tokens_in + record.tokens_out if usage_reported else self.max_tokens
                self._usage.append((self._last_call, used))
            return LLMResponse(content if isinstance(content, str) else "", record)
        raise ProviderError(f"{self.name}: no API attempts configured.")


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
        if agent == "diagnosis":
            out = {"index": 0, "evidence": "lowest replay error"}
        elif agent == "planner":
            out = {"target_mode": rule_mode(ctx["fault_report"], ctx["snapshot"]).value,
                   "rationale": "scripted rule"}
        else:
            act = rule_action(ctx["fault_report"], ctx["snapshot"], ctx.get("mode"), ctx.get("feedback"))
            out = json.loads(act.model_dump_json())
        text = json.dumps(out)
        rec = LLMCallRecord(agent=agent, model=self.name, latency_s=round(time.time() - t0, 4))
        return LLMResponse(text, rec)


def make_llm(provider: str, model: str | None = None, **kw):
    if provider == "scripted":
        return ScriptedLLM()
    return LLMClient(provider, model, **kw)
