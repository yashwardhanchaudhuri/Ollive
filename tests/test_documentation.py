import ast
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]

FOUNDATIONAL_DOCS = {
    "README.md": ("At a glance", "Design choices", "Documentation map"),
    "docs/AGENT_WORKFLOW.md": ("Objective", "At a glance", "Scope and limitations"),
    "docs/INSTALL.md": ("What this guide produces", "Choose a path", "Scope and security"),
    "docs/KNOWLEDGE_BASE.md": ("Objective", "At a glance", "Evidence quality boundary"),
    "docs/PROJECT_STRUCTURE.md": ("Objective", "How to read the repository", "Design boundaries"),
    "docs/prompt_guardrails.md": ("Objective", "Threat model", "Design insight"),
    "evaluation/README.md": ("At a glance", "Evidence map", "Governance"),
    "evaluation/REPORT.md": ("30-second conclusion", "Findings", "Decision and release boundary"),
}

LOCAL_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)#]+)(?:#[^)]+)?\)")


def _source_controlled_files() -> set[Path]:
    """Return tracked and non-ignored untracked files relative to the repository."""
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
    )
    files = {
        Path(value.decode("utf-8"))
        for value in output.split(b"\0")
        if value
    }
    return {path for path in files if (ROOT / path).exists()}


def test_foundational_docs_expose_reader_orientation():
    """Require foundational documents to expose their purpose and reading path."""
    for relative, phrases in FOUNDATIONAL_DOCS.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in text, f"{relative} is missing {phrase!r}"


def test_run_reports_explain_objective_variation_and_scope():
    """Require run reports to interpret objectives, variation, and scope."""
    for path in (ROOT / "evaluation/reports").glob("*/report.md"):
        text = path.read_text(encoding="utf-8")
        assert "Objective" in text
        assert "Variation" in text or "Failure movement" in text
        assert "Scope" in text


def test_knowledge_documents_open_with_scope_without_shifting_content():
    """Preserve corpus scope metadata and the first evidence paragraph."""
    for path in sorted(
        path for path in (ROOT / "assignment_kb").glob("*.md")
        if path.name.casefold() != "readme.md"
    ):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) >= 5
        assert lines[2].startswith("*Scope:")
        assert lines[4].strip(), f"{path.name} lost its first evidence paragraph"


def test_markdown_local_links_resolve():
    """Ensure every repository-local Markdown link resolves to an artifact."""
    missing = []
    for path in ROOT.rglob("*.md"):
        if (
            ".git" in path.parts
            or ".pytest_cache" in path.parts
            or any(part.startswith(".venv") for part in path.parts)
        ):
            continue
        for target in LOCAL_LINK_RE.findall(path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                missing.append((str(path.relative_to(ROOT)), target))
    assert not missing


def test_local_setup_uses_one_requirements_path():
    """Keep local installation on one unified requirements file."""
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "vllm==0.25.0" in requirements
    assert "pytest>=9.1,<10" in requirements
    assert not (ROOT / "requirements-vllm.txt").exists()
    assert not (ROOT / "requirements-dev.txt").exists()

    for relative in (
        "README.md",
        "docs/INSTALL.md",
        "environment.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "requirements-vllm" not in text
        assert "requirements-dev" not in text


def test_source_functions_explain_their_contract():
    """Require every project Python function to provide a contract docstring."""
    missing = []
    for folder in ("src", "scripts", "tests"):
        for path in (ROOT / folder).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not ast.get_docstring(node)
                ):
                    missing.append(
                        (str(path.relative_to(ROOT)), node.name, node.lineno)
                    )
    assert not missing


def test_streamlit_state_contains_only_consumed_objects():
    """Keep Streamlit session state limited to objects used by the UI."""
    text = (ROOT / "src/ollive/ui/streamlit_app.py").read_text(encoding="utf-8")
    assert "session_state.citations" not in text
    for key in ("messages", "citation_map", "agent_key", "agent"):
        assert f'session_state.setdefault("{key}"' in text


def test_project_folders_have_orienting_readmes():
    """Require a concise local guide at every source-controlled folder boundary."""
    directories = {Path(".")}
    for path in _source_controlled_files():
        directories.update((path.parent, *path.parents[:-1]))

    missing = []
    unoriented = []
    for relative in sorted(directories):
        guide = ROOT / relative / "README.md"
        if not guide.exists():
            missing.append(str(relative or Path(".")))
            continue
        if "At a glance" not in guide.read_text(encoding="utf-8"):
            unoriented.append(str(relative or Path(".")))

    assert not missing, f"folders missing README.md: {missing}"
    assert not unoriented, f"folder guides missing 'At a glance': {unoriented}"


def test_folder_guides_name_immediate_source_files():
    """Keep local file maps synchronized with the source files beside them."""
    generated_dirs = {Path("data/indexes"), Path("data/traces")}
    source_files = _source_controlled_files()
    missing = []
    guides = sorted(path for path in source_files if path.name == "README.md")
    for guide_relative in guides:
        directory_relative = guide_relative.parent
        if directory_relative == Path("."):
            continue
        text = (ROOT / guide_relative).read_text(encoding="utf-8")
        immediate_files = sorted(
            path for path in source_files if path.parent == directory_relative
        )
        for path in immediate_files:
            if path.name == "README.md" or path.suffix == ".orig":
                continue
            if (
                directory_relative in generated_dirs
                and path.name != ".gitkeep"
            ):
                continue
            if f"`{path.name}`" not in text:
                missing.append((str(directory_relative), path.name))
    assert not missing, f"folder guides omit files: {missing}"
