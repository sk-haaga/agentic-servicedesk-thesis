"""LLM providers: Azure OpenAI, OpenAI and an offline 'fake' provider for tests.

All providers expose the same small interface:
  parse(system, user, schema, context)   -> LLMResult with a validated Pydantic object
  chat_tools(messages, tools)            -> assistant message (possibly with tool calls) + usage
  embed(texts)                           -> list of vectors
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import env, settings


class SchemaError(Exception):
    """The model did not return output that matches the schema, even after repair."""


@dataclass
class LLMResult:
    parsed: Any
    model: str
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    repairs: int = 0
    retries: int = 0


@dataclass
class Usage:
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    embed_tokens: int = 0
    retries: int = 0
    repairs: int = 0

    def add(self, r: LLMResult):
        self.calls += 1
        self.tokens_in += r.tokens_in
        self.tokens_out += r.tokens_out
        self.repairs += r.repairs
        self.retries += r.retries


def _transient_errors():
    try:
        import openai
        return (openai.APIConnectionError, openai.APITimeoutError, openai.RateLimitError, openai.InternalServerError)
    except Exception:  # pragma: no cover
        return (ConnectionError,)


class OpenAICompatibleLLM:
    """Shared implementation for Azure OpenAI and OpenAI (same SDK)."""

    is_fake = False

    def __init__(self, client, chat_model: str, embed_model: str, name: str):
        self.client = client
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.name = name
        self.usage = Usage()
        self._attempts = int(settings()["retries"]["llm_attempts"])
        self.sampling = {"temperature": settings()["temperature"], "seed": 42}

    def _sampled(self, fn, **kwargs):
        """Call with temperature/seed; reasoning models (e.g. gpt-5-mini) reject them, so drop them once and remember."""
        try:
            return self._call(fn, **kwargs, **self.sampling)
        except Exception as exc:  # openai.BadRequestError: unsupported parameter/value
            msg = str(exc).lower()
            if self.sampling and getattr(exc, "status_code", None) == 400 and ("temperature" in msg or "seed" in msg):
                self.sampling = {}
                return self._call(fn, **kwargs)
            raise

    # -------- retries for transient API errors (timeouts, rate limits, 5xx)
    def _call(self, fn, **kwargs):
        attempts = {"n": 0}

        @retry(retry=retry_if_exception_type(_transient_errors()), stop=stop_after_attempt(self._attempts),
               wait=wait_exponential(multiplier=1, min=1, max=20), reraise=True)
        def run():
            attempts["n"] += 1
            return fn(**kwargs)

        out = run()
        return out, attempts["n"] - 1

    def parse(self, system: str, user: str, schema: type[BaseModel], context: dict | None = None,
              messages: list[dict] | None = None) -> LLMResult:
        messages = list(messages) if messages else [{"role": "system", "content": system}, {"role": "user", "content": user}]
        repairs_allowed = int(settings()["retries"]["schema_repairs"])
        total_in = total_out = retries = 0
        t0 = time.perf_counter()
        for attempt in range(repairs_allowed + 1):
            try:
                resp, r = self._sampled(self.client.chat.completions.parse, model=self.chat_model, messages=messages,
                                        response_format=schema)
                retries += r
                if resp.usage:
                    total_in += resp.usage.prompt_tokens
                    total_out += resp.usage.completion_tokens
                parsed = resp.choices[0].message.parsed
                if parsed is None:
                    raise SchemaError(resp.choices[0].message.refusal or "empty parse")
                res = LLMResult(parsed, self.chat_model, (time.perf_counter() - t0) * 1000, total_in, total_out, attempt, retries)
                self.usage.add(res)
                return res
            except (ValidationError, SchemaError, json.JSONDecodeError) as exc:
                if attempt >= repairs_allowed:
                    raise SchemaError(str(exc)[:300]) from exc
                messages.append({"role": "user", "content": f"Your previous answer was invalid ({str(exc)[:200]}). Answer again using only the allowed values."})
        raise SchemaError("unreachable")

    def chat_tools(self, messages: list[dict], tools: list[dict]):
        t0 = time.perf_counter()
        resp, r = self._sampled(self.client.chat.completions.create, model=self.chat_model, messages=messages, tools=tools,
                                tool_choice="auto")
        res = LLMResult(None, self.chat_model, (time.perf_counter() - t0) * 1000,
                        resp.usage.prompt_tokens if resp.usage else 0, resp.usage.completion_tokens if resp.usage else 0, 0, r)
        self.usage.add(res)
        return resp.choices[0].message, res

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp, _ = self._call(self.client.embeddings.create, model=self.embed_model, input=texts)
        if resp.usage:
            self.usage.embed_tokens += resp.usage.prompt_tokens
        return [d.embedding for d in resp.data]


def azure_endpoint() -> str:
    """Validate AZURE_OPENAI_ENDPOINT and reduce it to https://host/ (a pasted full 'Target URI' is accepted)."""
    from urllib.parse import urlparse
    raw = (env("AZURE_OPENAI_ENDPOINT") or "").strip().strip('"').strip("'")
    host = urlparse(raw if "://" in raw else "https://" + raw).hostname or ""
    if not raw or "<" in raw or "." not in host:
        raise SystemExit("AZURE_OPENAI_ENDPOINT in .env is missing or still the placeholder. Copy the endpoint from the "
                         "Azure portal (Azure OpenAI resource > Keys and Endpoint), e.g. https://my-resource.openai.azure.com/")
    import socket
    try:
        socket.getaddrinfo(host, 443)
    except OSError:
        raise SystemExit(f"Cannot resolve the Azure host '{host}'. Check AZURE_OPENAI_ENDPOINT in .env for typos "
                         "(compare it with Keys and Endpoint in the Azure portal) and that you are online / not blocked by a VPN.")
    key = (env("AZURE_OPENAI_API_KEY") or "").strip()
    if not key or "<" in key:
        raise SystemExit("AZURE_OPENAI_API_KEY in .env is missing or still the placeholder.")
    return f"https://{host}/"


def azure_llm() -> OpenAICompatibleLLM:
    from openai import AzureOpenAI
    client = AzureOpenAI(azure_endpoint=azure_endpoint(), api_key=env("AZURE_OPENAI_API_KEY").strip(),
                         api_version=env("AZURE_OPENAI_API_VERSION", "2024-10-21"), timeout=60)
    return OpenAICompatibleLLM(client, env("AZURE_OPENAI_CHAT_DEPLOYMENT"), env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"), "azure")


def openai_llm() -> OpenAICompatibleLLM:
    from openai import OpenAI
    client = OpenAI(api_key=env("OPENAI_API_KEY"), timeout=60)
    return OpenAICompatibleLLM(client, env("OPENAI_CHAT_MODEL", "gpt-4.1-mini"), env("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), "openai")


class FakeLLM:
    """Deterministic offline stand-in used for tests and for developing without API costs.
    Classification uses the keyword baseline; resolution copies the steps of the best SOP."""

    is_fake = True
    name = "fake"
    chat_model = "fake-heuristic"

    def __init__(self):
        from sklearn.feature_extraction.text import HashingVectorizer
        self._vec = HashingVectorizer(n_features=1024, ngram_range=(1, 2), norm="l2", alternate_sign=False)
        self.usage = Usage()

    def parse(self, system: str, user: str, schema: type[BaseModel], context: dict | None = None,
              messages: list[dict] | None = None) -> LLMResult:
        t0 = time.perf_counter()
        context = context or {}
        if schema.__name__.startswith("Classification"):
            from ..baselines.keyword import classify as kw  # type: ignore
            out = kw(context["text"], context["catalogue"])
            parsed = schema(summary=out["summary"], category=out["category"], application=out["application"],
                            impact=out["impact"], urgency=out["urgency"], evidence=out["evidence"],
                            confidence=out["confidence"], injection_suspected=False)
        elif schema.__name__ == "Resolution":
            sops = context.get("sops") or []
            if "general IT support knowledge" in system:
                parsed = schema(answerable=True, sop_ids=[], self_check="covered",
                                response="Please restart the application and your computer, check your network connection and try again.")
            elif sops and sops[0].similarity >= 0.3:
                top = sops[0]
                steps = [l.strip() for l in top.text.splitlines() if l.strip()[:2].rstrip(".").isdigit()]
                parsed = schema(answerable=True, sop_ids=[top.sop_id], self_check="covered",
                                response="Please try the following steps:\n" + "\n".join(steps or [top.text[:300]]))
            else:
                parsed = schema(answerable=False, sop_ids=[], response="", self_check="not_covered")
        elif schema.__name__ == "Judgement":
            parsed = schema(score=2 if context.get("overlap", 0) > 0.5 else 1 if context.get("overlap", 0) > 0.2 else 0,
                            rationale="fake judge: word overlap with SOP")
        else:  # pragma: no cover
            raise SchemaError(f"fake provider cannot produce {schema.__name__}")
        res = LLMResult(parsed, self.chat_model, (time.perf_counter() - t0) * 1000, 0, 0)
        self.usage.add(res)
        return res

    def chat_tools(self, messages, tools):  # the fake model never calls tools
        class Msg:
            tool_calls = None
            content = ""
        return Msg(), LLMResult(None, self.chat_model, 0.0)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._vec.transform([t.lower() for t in texts]).toarray().tolist()


def get_llm(provider: str | None = None):
    provider = (provider or env("LLM_PROVIDER", "fake")).lower()
    if provider == "azure":
        return azure_llm()
    if provider == "openai":
        return openai_llm()
    return FakeLLM()
