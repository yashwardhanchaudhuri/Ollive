"""Composition root — wires ports to adapters from YAML/env."""

from __future__ import annotations

import uuid
from typing import Any

from ollive.adapters.llm.openai_compatible import OpenAICompatibleLLM
from ollive.adapters.observability.factory import build_tracer_from_config
from ollive.adapters.rag.local_retriever import LocalRetriever
from ollive.adapters.search.tavily_search import NullWebSearch, TavilyWebSearch
from ollive.application.agent import WellnessAgent
from ollive.application.config import load_config, resolve_path
from ollive.application.tools import ToolRouter
from ollive.ports.llm import LLMPort
from ollive.ports.tracer import TracerPort
from ollive.ports.web_search import WebSearchPort


def build_llm(cfg: dict[str, Any], backend_name: str | None = None) -> LLMPort:
    name = backend_name or cfg["active"]
    backend = cfg["backends"][name]
    provider = backend["provider"]

    if provider == "local":
        from ollive.adapters.llm.local_transformers import LocalTransformersLLM

        return LocalTransformersLLM(
            backend_name=name,
            model=backend["model"],
            temperature=float(backend.get("temperature", 0.3)),
            max_tokens=int(backend.get("max_tokens", 1024)),
            load_in_4bit=bool(backend.get("load_in_4bit", False)),
        )

    if provider in {"openai", "vllm"}:
        return OpenAICompatibleLLM(
            backend_name=name,
            model=backend["model"],
            api_key=backend.get("api_key") or "EMPTY",
            base_url=(
                backend.get("base_url")
                or ("https://api.openai.com/v1" if provider == "openai" else None)
            ),
            temperature=(
                float(backend["temperature"]) if "temperature" in backend else None
            ),
            max_tokens=int(backend.get("max_tokens", 1024)),
            instruct_mode=bool(backend.get("instruct_mode", False)),
            provider=provider,
        )
    raise ValueError(f"Unsupported provider: {provider}")


def build_retriever(cfg: dict[str, Any], rebuild: bool = False) -> LocalRetriever:
    rag = cfg["rag"]
    return LocalRetriever.from_paths(
        kb_dir=resolve_path(rag["kb_dir"]),
        index_dir=resolve_path(rag["index_dir"]),
        embedder=rag["embedder"],
        rebuild=rebuild,
    )


def build_web_search(cfg: dict[str, Any]) -> WebSearchPort:
    search_cfg = cfg.get("tools", {}).get("search_web", {})
    key = search_cfg.get("api_key") or ""
    max_results = int(search_cfg.get("max_results", 5))
    if not key:
        return NullWebSearch()
    return TavilyWebSearch(api_key=key, max_results=max_results)


def build_agent(
    backend_name: str | None = None,
    *,
    rebuild_index: bool = False,
    session_id: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> WellnessAgent:
    cfg = cfg or load_config()
    llm = build_llm(cfg, backend_name)
    retriever = build_retriever(cfg, rebuild=rebuild_index)
    indexed_doc_types = retriever.list_doc_types()
    configured_doc_types = list(cfg["rag"].get("doc_types", indexed_doc_types))
    if set(configured_doc_types) != set(indexed_doc_types):
        raise ValueError(
            "rag.doc_types must exactly match indexed doc types; "
            f"configured={configured_doc_types}, indexed={indexed_doc_types}"
        )
    web = build_web_search(cfg)
    tools = ToolRouter(
        retriever,
        web,
        default_top_k=int(cfg["rag"].get("top_k", 4)),
        allowed_doc_types=configured_doc_types,
    )
    obs = cfg.get("observability", {})
    tracer: TracerPort = build_tracer_from_config(obs)
    agent_cfg = cfg.get("agent", {})
    system_prompt = agent_cfg.get("system_prompt", "You are a wellness assistant.")
    system_prompt += (
        "\n\nlookup_kb doc_types are a closed enum. Select only from these exact "
        f"values: {', '.join(configured_doc_types)}. Never construct or guess a "
        "doc_type. Omit doc_types when no listed value is clearly appropriate."
    )
    return WellnessAgent(
        llm=llm,
        tools=tools,
        tracer=tracer,
        system_prompt=system_prompt,
        memory_turns=int(agent_cfg.get("memory_turns", 8)),
        max_tool_rounds=int(agent_cfg.get("max_tool_rounds", 4)),
        session_id=session_id or str(uuid.uuid4()),
    )
