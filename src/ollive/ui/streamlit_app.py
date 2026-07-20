"""Streamlit chat UI for the Ollive Wellness Assistant."""

from __future__ import annotations

import hashlib
import html
import sys
from pathlib import Path

# Allow `streamlit run src/ollive/ui/streamlit_app.py` without install
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st
from openai import APIConnectionError, APIError

from ollive.application.config import load_config
from ollive.application.factory import build_agent
from ollive.domain.citations import CITATION_RE


st.set_page_config(
    page_title="Ollive Wellness Assistant",
    page_icon="🫒",
    layout="wide",
    initial_sidebar_state="expanded",
)


STYLESHEET = Path(__file__).with_name("styles.css")


def _inject_styles() -> None:
    css = STYLESHEET.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "citations" not in st.session_state:
        st.session_state.citations = []
    if "citation_map" not in st.session_state:
        st.session_state.citation_map = {}
    if "agent_key" not in st.session_state:
        st.session_state.agent_key = None
    if "agent" not in st.session_state:
        st.session_state.agent = None


def _ensure_agent(backend: str, rebuild: bool = False) -> None:
    key = f"{backend}:{rebuild}"
    if st.session_state.agent is None or st.session_state.agent_key != backend or rebuild:
        with st.spinner("Loading agent / index..."):
            st.session_state.agent = build_agent(
                backend_name=backend, rebuild_index=rebuild
            )
        st.session_state.agent_key = backend
        if rebuild:
            st.session_state.messages = []
            st.session_state.citations = []


def _source_id(marker: str) -> str:
    digest = hashlib.sha1(marker.encode("utf-8")).hexdigest()[:12]
    return f"source-{digest}"


def _render_answer(text: str) -> None:
    def citation_link(match: object) -> str:
        marker = match.group(0)
        citation = st.session_state.citation_map.get(marker)
        label = (
            citation.title
            if citation and citation.title
            else match.group("doc_type").replace("_", " ").title()
        )
        return (
            f'<a class="citation-link" href="#{_source_id(marker)}" '
            f'aria-label="Open {html.escape(label)} source">{html.escape(label)}</a>'
        )

    st.markdown(CITATION_RE.sub(citation_link, text), unsafe_allow_html=True)


def _render_source_drawers() -> None:
    drawers = []
    for marker, citation in st.session_state.citation_map.items():
        end_line = citation.end_line or citation.line
        line_label = f"Line {citation.line}" if end_line == citation.line else f"Lines {citation.line}–{end_line}"
        drawers.append(
            '<aside class="source-drawer" id="' + _source_id(marker) + '">'
            '<div class="source-drawer__top"><div class="source-drawer__heading">'
            '<span class="source-drawer__label">Knowledge source</span>'
            '<span class="source-drawer__line">' + html.escape(line_label) + '</span></div>'
            '<a class="source-drawer__close" href="#" aria-label="Close source">×</a></div>'
            '<h2>' + html.escape(citation.title or citation.doc_type.replace("_", " ").title()) + '</h2>'
            '<div class="source-drawer__body">' + html.escape(citation.text) + '</div></aside>'
        )
    if drawers:
        st.markdown("".join(drawers), unsafe_allow_html=True)


def main() -> None:
    _init_state()
    cfg = load_config()
    backends = list(cfg.get("backends", {}).keys())

    _inject_styles()
    st.markdown(
        """
        <section class="ollive-hero">
          <div class="ollive-eyebrow">Personal wellness intelligence</div>
          <h1>Better habits,<br>grounded answers.</h1>
          <p>
            Practical guidance across nutrition, movement, mindfulness, and
            everyday wellbeing—grounded in a curated knowledge base.
          </p>
          <div class="ollive-status">Assistant ready</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown('<div class="sidebar-kicker">Ollive workspace</div>', unsafe_allow_html=True)
        st.header("Model")
        default_idx = (
            backends.index(cfg["active"]) if cfg.get("active") in backends else 0
        )
        backend = st.selectbox("Active backend", backends, index=default_idx)
        if st.button("Rebuild KB index"):
            _ensure_agent(backend, rebuild=True)
            st.success("Index rebuilt")
        if st.button("Clear chat"):
            if st.session_state.agent:
                st.session_state.agent.reset()
            st.session_state.messages = []
            st.session_state.citations = []
            st.session_state.citation_map = {}
            st.rerun()

        st.divider()
        st.header("Session usage")
        agent = st.session_state.agent
        if agent:
            u = agent.session_usage
            left, right = st.columns(2)
            left.metric("Input", u.prompt_tokens)
            right.metric("Output", u.completion_tokens)
            left.metric("Total", u.total_tokens)
            right.metric("Latency", f"{u.latency_ms:.0f} ms")
            st.caption(f"Model: `{u.model}` · Backend: `{u.backend}`")
        else:
            st.caption("No session yet.")

    _ensure_agent(backend)
    _render_source_drawers()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                _render_answer(msg["content"])
                if msg.get("tools"):
                    with st.expander("Tool calls"):
                        st.json(msg["tools"])
            else:
                st.markdown(msg["content"])

    prompt = st.chat_input("Ask Ollive about your wellbeing…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                with st.spinner("Thinking…"):
                    result = st.session_state.agent.chat(prompt)
            except APIConnectionError:
                service = "local Qwen" if backend == "oss" else "OpenAI"
                message = (
                    f"The {service} service is temporarily unreachable. "
                    "Please retry in a moment."
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": message, "service_error": True}
                )
                st.rerun()
            except APIError:
                message = (
                    f"The selected {backend} model rejected the request. "
                    "Please check its backend configuration."
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": message, "service_error": True}
                )
                st.rerun()
            for citation in result.citations:
                st.session_state.citation_map[citation.marker] = citation
            _render_answer(result.assistant_message)
            if result.tool_trace:
                with st.expander("Tool calls"):
                    st.json(result.tool_trace)
            st.caption(
                f"{result.usage.total_tokens} tokens · {result.usage.latency_ms:.0f} ms · {result.model}"
            )

        st.session_state.citations = result.citations
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result.assistant_message,
                "tools": result.tool_trace,
            }
        )
        st.rerun()


if __name__ == "__main__":
    main()
