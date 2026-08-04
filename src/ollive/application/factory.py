"""Composition root — wires ports to adapters from YAML/env."""

from __future__ import annotations

import uuid
from typing import Any

from ollive.adapters.llm.openai_compatible import OpenAICompatibleLLM
from ollive.adapters.observability.factory import build_tracer_from_config
from ollive.adapters.rag.local_retriever import LocalRetriever
from ollive.adapters.search.tavily_search import TavilyWebSearch
from ollive.adapters.security.llm_security import LLMSecurityGate
from ollive.application.agent import WellnessAgent
from ollive.application.canary import OutputCanary
from ollive.application.config import load_config, resolve_path
from ollive.application.request_limits import RequestLimits
from ollive.application.security import SecurityBroker
from ollive.application.tools import ToolRouter
from ollive.ports.llm import LLMPort
from ollive.ports.tracer import TracerPort
from ollive.ports.web_search import WebSearchPort


def build_llm(cfg: dict[str, Any], backend_name: str | None = None) -> LLMPort:
    """Construct the configured local or frontier language-model adapter."""
    name = backend_name or cfg["active"]
    backend = cfg["backends"][name]
    provider = backend["provider"]

    if provider == "local":
        # Defer the heavyweight Transformers import so API deployments do not
        # load the in-process model stack.
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


def build_security_broker(cfg: dict[str, Any]) -> SecurityBroker:
    """Build the mandatory, independently configured runtime Security LM."""
    security_cfg = cfg.get("security", {})
    if not security_cfg.get("enabled", True):
        raise ValueError("The runtime Security LM cannot be disabled")
    model = str(security_cfg.get("model") or "").strip()
    if not model:
        raise ValueError(
            "security.model is required for the mandatory Security LM adapter"
        )
    provider = str(security_cfg.get("provider", "openai"))
    if provider == "openai" and not security_cfg.get("api_key"):
        raise ValueError("SECURITY_LM_API_KEY is required for the Security LM")
    shadow_cfg = {
        "active": "security",
        "backends": {"security": security_cfg},
    }
    security_llm = build_llm(shadow_cfg, "security")
    configured_canary = str(security_cfg.get("canary_token") or "").strip()
    canary = (
        OutputCanary(configured_canary)
        if configured_canary
        else OutputCanary.generate()
    )
    max_input_chars = int(security_cfg.get("max_input_chars", 120_000))
    if max_input_chars <= 0:
        raise ValueError("security.max_input_chars must be positive")
    return SecurityBroker(
        LLMSecurityGate(security_llm, max_input_chars=max_input_chars),
        output_canary=canary,
    )


def build_retriever(cfg: dict[str, Any], rebuild: bool = False) -> LocalRetriever:
    """Load or rebuild the local retriever used by knowledge-base tools."""
    rag = cfg["rag"]
    return LocalRetriever.from_paths(
        kb_dir=resolve_path(rag["kb_dir"]),
        index_dir=resolve_path(rag["index_dir"]),
        embedder=rag["embedder"],
        rebuild=rebuild,
    )


def build_web_search(cfg: dict[str, Any]) -> WebSearchPort:
    """Construct mandatory trusted-domain web search or fail startup."""
    search_cfg = cfg.get("tools", {}).get("search_web", {})
    provider = str(search_cfg.get("provider") or "").strip()
    if provider != "tavily":
        raise ValueError("tools.search_web.provider must be tavily")
    key = str(search_cfg.get("api_key") or "").strip()
    if not key:
        raise ValueError(
            "TAVILY_API_KEY is required because every grounded wellness turn "
            "must perform a web search"
        )
    max_results = int(search_cfg.get("max_results", 5))
    return TavilyWebSearch(
        api_key=key,
        max_results=max_results,
        trusted_domains=list(search_cfg.get("trusted_domains", [])),
        min_score=float(search_cfg.get("min_score", 0.5)),
    )


def build_agent(
    backend_name: str | None = None,
    *,
    rebuild_index: bool = False,
    session_id: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> WellnessAgent:
    """Compose the agent used by Streamlit and evaluation runners."""
    cfg = cfg or load_config()
    llm = build_llm(cfg, backend_name)
    security = build_security_broker(cfg)
    retriever = build_retriever(cfg, rebuild=rebuild_index)
    indexed_doc_types = retriever.list_doc_types()
    configured_doc_types = list(cfg["rag"].get("doc_types", indexed_doc_types))
    # Require configuration and the physical index to agree so every offered
    # filter resolves and no corpus category is hidden.
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
    limits_cfg = cfg.get("request_limits", {})
    pipeline_cfg = cfg.get("pipeline", {})
    system_prompt = agent_cfg.get("system_prompt", "You are a wellness assistant.")
    # Guide model choice in prose while ToolRouter independently enforces the same
    # live enum as a hard validation boundary.
    system_prompt += (
        "\n\nlookup_kb doc_types are a closed enum. Select only from these exact "
        f"values: {', '.join(configured_doc_types)}. Never construct or guess a "
        "doc_type. Omit doc_types when no listed value is clearly appropriate."
    )
    system_prompt += security.canary_instruction
    return WellnessAgent(
        llm=llm,
        tools=tools,
        tracer=tracer,
        security=security,
        system_prompt=system_prompt,
        memory_turns=int(agent_cfg.get("memory_turns", 8)),
        max_tool_rounds=int(pipeline_cfg.get("max_tool_rounds", 10)),
        min_web_searches=int(pipeline_cfg.get("min_web_searches", 1)),
        max_web_searches=int(pipeline_cfg.get("max_web_searches", 3)),
        session_id=session_id or str(uuid.uuid4()),
        request_limits=RequestLimits(
            max_requests=int(limits_cfg.get("max_requests", 12)),
            window_seconds=float(limits_cfg.get("window_seconds", 60)),
            max_message_chars=int(limits_cfg.get("max_message_chars", 20_000)),
            max_context_chars=int(limits_cfg.get("max_context_chars", 48_000)),
        ),
    )
