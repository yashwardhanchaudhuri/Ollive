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
    """Load the adjacent stylesheet into the current Streamlit page."""
    css = STYLESHEET.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _init_state() -> None:
    """Create per-browser-session objects that survive Streamlit reruns."""
    # Streamlit reruns this module after every interaction. The transcript is the
    # display history; citation_map resolves its markers to source drawers.
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("citation_map", {})

    # Agent construction loads the retriever and model adapter, so cache it until
    # the backend changes or the user explicitly rebuilds the index.
    st.session_state.setdefault("agent_key", None)
    st.session_state.setdefault("agent", None)


def _ensure_agent(backend: str, rebuild: bool = False) -> None:
    """Reuse the session agent or rebuild it after a backend or index change."""
    if st.session_state.agent is None or st.session_state.agent_key != backend or rebuild:
        with st.spinner("Loading agent / index..."):
            st.session_state.agent = build_agent(
                backend_name=backend, rebuild_index=rebuild
            )
        st.session_state.agent_key = backend
        if rebuild:
            st.session_state.messages = []
            st.session_state.citation_map = {}


def _source_id(marker: str) -> str:
    """Derive a stable HTML drawer target from an internal citation marker."""
    digest = hashlib.sha1(marker.encode("utf-8")).hexdigest()[:12]
    return f"source-{digest}"


def _render_answer(text: str) -> None:
    """Replace validated markers with source links and render the answer."""

    def citation_link(match: object) -> str:
        """Convert one citation match into its human-readable drawer link."""
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
    """Render one hidden, anchor-addressable drawer per known citation."""
    drawers = []
    for marker, citation in st.session_state.citation_map.items():
        is_web = citation.source_type == "web"
        if is_web:
            source_label = "Authoritative web source"
            source_meta = citation.domain or "External source"
            external_link = (
                '<a class="source-drawer__external" href="'
                + html.escape(citation.url or "", quote=True)
                + '" target="_blank" rel="noopener noreferrer">Open original source ↗</a>'
            )
        else:
            end_line = citation.end_line or citation.line
            source_label = "Knowledge source"
            source_meta = (
                f"Line {citation.line}"
                if end_line == citation.line
                else f"Lines {citation.line}–{end_line}"
            )
            external_link = ""

        drawers.append(
            '<aside class="source-drawer" id="' + _source_id(marker) + '">'
            '<div class="source-drawer__top"><div class="source-drawer__heading">'
            '<span class="source-drawer__label">' + html.escape(source_label) + '</span>'
            '<span class="source-drawer__line">' + html.escape(source_meta) + '</span></div>'
            '<a class="source-drawer__close" href="#" aria-label="Close source">×</a></div>'
            '<h2>' + html.escape(citation.title or citation.doc_type.replace("_", " ").title()) + '</h2>'
            '<div class="source-drawer__body">' + html.escape(citation.text) + '</div>'
            + external_link
            + '</aside>'
        )
    if drawers:
        st.markdown("".join(drawers), unsafe_allow_html=True)


def main() -> None:
    """Render the Ollive page and process at most one submitted chat turn."""
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
