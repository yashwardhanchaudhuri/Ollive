from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]

FOUNDATIONAL_DOCS = {
    "README.md": ("At a glance", "Design choices", "Documentation map"),
    "docs/AGENT_WORKFLOW.md": ("Objective", "At a glance", "Scope and limitations"),
    "docs/INSTALL.md": ("What this guide produces", "Choose a path", "Scope and security"),
    "docs/KNOWLEDGE_BASE.md": ("Objective", "At a glance", "Evidence quality boundary"),
    "docs/PROJECT_STRUCTURE.md": ("Objective", "How to read the repository", "Design boundaries"),
    "docs/WRITING_STANDARD.md": ("The reader should understand the point first", "Use progressive disclosure", "Review checklist"),
    "docs/prompt_guardrails.md": ("Objective", "Threat model", "Design insight"),
    "requirements.md": ("Objective", "At a glance", "Resolution and known versions"),
    "evaluation/README.md": ("At a glance", "Evidence map", "Governance"),
    "evaluation/REPORT.md": ("How to read this report", "Key insights", "Limitations"),
}

LOCAL_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)#]+)(?:#[^)]+)?\)")


def test_foundational_docs_expose_reader_orientation():
    for relative, phrases in FOUNDATIONAL_DOCS.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in text, f"{relative} is missing {phrase!r}"


def test_run_reports_explain_objective_variation_and_scope():
    for path in (ROOT / "evaluation/reports").glob("*/report.md"):
        text = path.read_text(encoding="utf-8")
        assert "Objective" in text
        assert "Variation" in text or "Failure movement" in text
        assert "Scope" in text


def test_knowledge_documents_open_with_scope_without_shifting_content():
    for path in sorted((ROOT / "assignment_kb").glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) >= 5
        assert lines[2].startswith("*Scope:")
        assert lines[4].strip(), f"{path.name} lost its first evidence paragraph"


def test_markdown_local_links_resolve():
    missing = []
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts or ".pytest_cache" in path.parts:
            continue
        for target in LOCAL_LINK_RE.findall(path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                missing.append((str(path.relative_to(ROOT)), target))
    assert not missing


def test_local_setup_uses_one_requirements_path():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "vllm==0.25.0" in requirements
    assert not (ROOT / "requirements-vllm.txt").exists()

    for relative in ("README.md", "docs/INSTALL.md", "requirements.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "requirements-vllm" not in text
