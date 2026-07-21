"""Generate an evidence-linked Markdown report and SVG infographics."""
from __future__ import annotations

import html
import json
import statistics
from pathlib import Path


def load_records(path):
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def rate(values):
    return sum(values) / len(values) if values else None


def percent(value):
    return "N/A" if value is None else f"{100 * value:.1f}%"


def bar_chart(path, title, groups):
    height = 95 + 48 * len(groups)
    rows = []
    for index, (label, value) in enumerate(groups.items()):
        y = 70 + index * 48
        amount = 0 if value is None else value
        color = "#4f8f7b" if amount >= .8 else "#d69a5b" if amount >= .6 else "#bd6b6b"
        rows.append(
            f'<text x="20" y="{y + 17}" font-size="15" fill="#26352f">{html.escape(label)}</text>'
            f'<rect x="250" y="{y}" width="500" height="24" rx="7" fill="#e8eee9"/>'
            f'<rect x="250" y="{y}" width="{500 * amount:.1f}" height="24" rx="7" fill="{color}"/>'
            f'<text x="760" y="{y + 17}" font-size="14" fill="#26352f">{percent(value)}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="820" height="{height}" viewBox="0 0 820 {height}">'
        f'<rect width="100%" height="100%" rx="18" fill="#f7f4ed"/>'
        f'<text x="20" y="38" font-size="22" font-weight="600" fill="#26352f">{html.escape(title)}</text>'
        + "".join(rows) + "</svg>"
    )
    path.write_text(svg, encoding="utf-8")


def pipeline_svg(path):
    labels = ["Versioned dataset", "Isolated run", "Structural grade", "Calibrated judge", "Human review", "Release gates"]
    blocks = []
    for index, label in enumerate(labels):
        x = 18 + index * 145
        blocks.append(f'<rect x="{x}" y="55" width="120" height="58" rx="14" fill="#dce9e1" stroke="#799989"/>')
        blocks.append(f'<text x="{x + 60}" y="89" text-anchor="middle" font-size="13" fill="#26352f">{label}</text>')
        if index < len(labels) - 1:
            blocks.append(f'<path d="M{x + 121} 84 H{x + 140}" stroke="#799989" stroke-width="3"/>')
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="890" height="150" viewBox="0 0 890 150">'
        '<rect width="100%" height="100%" rx="18" fill="#f7f4ed"/>'
        '<text x="20" y="32" font-size="21" font-weight="600" fill="#26352f">Evaluation evidence flow</text>'
        + "".join(blocks) + "</svg>"
    )
    path.write_text(svg, encoding="utf-8")


def generate(results, output_dir, calibration=None):
    records = load_records(results)
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = output_dir / "assets"
    assets.mkdir(exist_ok=True)
    complete = [row for row in records if not row.get("error")]
    backends = sorted({row["backend"] for row in records})
    axes = ["hallucination", "bias_harm", "content_safety"]

    axis_rates = {}
    check_rates = {}
    for backend in backends:
        for axis in axes:
            subset = [r for r in complete if r["backend"] == backend and r["case"]["axis"] == axis]
            values = [r["structural_grades"]["overall"]["pass"] for r in subset if r.get("structural_grades")]
            axis_rates[f"{backend} · {axis.replace('_', ' ')}"] = rate(values)
        for check in ("route", "tool_policy", "citation_policy", "citation_integrity", "query_fidelity"):
            values = [r["structural_grades"][check]["pass"] for r in complete if r["backend"] == backend and r.get("structural_grades")]
            check_rates[f"{backend} · {check.replace('_', ' ')}"] = rate(values)

    bar_chart(assets / "axis_pass_rates.svg", "Structural pass rate by axis", axis_rates)
    bar_chart(assets / "check_pass_rates.svg", "Guardrail pass rate", check_rates)
    calibration_data = None
    if calibration:
        calibration_data = json.loads(calibration.read_text(encoding="utf-8"))
        metrics = calibration_data["metrics"]
        bar_chart(
            assets / "judge_calibration.svg",
            "Judge calibration against human gold",
            {
                "accuracy": metrics["accuracy"],
                "macro F1": metrics["macro_f1"],
                "fail-class recall": metrics["per_label"]["fail"]["recall"],
            },
        )
    pipeline_svg(assets / "evaluation_pipeline.svg")

    lines = [
        "# Ollive assistant run report", "",
        "| Field | Value |",
        "|---|---|",
        "| Objective | Show how one frozen run behaves across routing, tool, citation, and safety expectations |",
        f"| Raw evidence | `{results}` |",
        f"| Attempts | {len(records)} |",
        f"| Backends | {', '.join(backends)} |",
        "| Result type | Structural regression evidence; semantic quality is separate |",
        "", "## At a glance", "",
        "This report follows one run from archived records to component failures. "
        "Read the summary first, then use variation and the failure register to "
        "understand why the aggregate moved.",
        "", "![Evaluation evidence flow](assets/evaluation_pipeline.svg)", "",
        "## Executive summary", "",
    ]
    for backend in backends:
        subset = [r for r in records if r["backend"] == backend]
        successful = [r for r in subset if not r.get("error")]
        structural = [r["structural_grades"]["overall"]["pass"] for r in successful if r.get("structural_grades")]
        semantic = [r.get("semantic_grade", {}).get("label") for r in successful if r.get("semantic_grade")]
        latencies = [r.get("usage", {}).get("latency_ms", 0) for r in successful]
        tokens = [r.get("usage", {}).get("total_tokens", 0) for r in successful]
        mean_latency = statistics.mean(latencies) / 1000 if latencies else 0
        mean_tokens = statistics.mean(tokens) if tokens else 0
        semantic_rate = percent(rate([x == "pass" for x in semantic])) if semantic else "not judged"
        lines.append(
            f"- **{backend}:** {len(successful)}/{len(subset)} completed; structural pass {percent(rate(structural))}; "
            f"semantic pass {semantic_rate}; mean latency {mean_latency:.2f}s; mean tokens {mean_tokens:.0f}."
        )
    if len(backends) < 2:
        lines.extend([
            "",
            "> **Comparison incomplete:** only one candidate backend is present in this run. "
            "Do not infer a winner until the identical dataset and manifest are run against the second assistant.",
        ])
    if any(r.get("semantic_grade", {}).get("judge_backend") == r.get("backend") for r in complete):
        lines.extend(["", "> **Judge limitation:** a candidate was graded by the same backend. Semantic results are exploratory, not release evidence."])

    lines.extend([
        "", "## Evaluation objective and method", "",
        "This run asks whether the candidate follows the expected policy route, "
        "uses tools and citations when required, preserves the original KB query, "
        "and avoids invalid citation output.",
        "",
        "Every case starts with fresh dialogue memory. The runner captures response "
        "and application state, retains execution errors, and applies deterministic "
        "checks. Structural passing is regression evidence, not a semantic quality judgment.",
    ])

    lines.extend(["", "## Results by axis", "", "![Structural rates](assets/axis_pass_rates.svg)", "",
                  "| Backend | Axis | Cases | Structural pass | Semantic pass |", "|---|---|---:|---:|---:|"])
    summary = {"records": len(records), "backends": {}}
    for backend in backends:
        summary["backends"][backend] = {}
        for axis in axes:
            subset = [r for r in complete if r["backend"] == backend and r["case"]["axis"] == axis]
            structural = [r["structural_grades"]["overall"]["pass"] for r in subset if r.get("structural_grades")]
            semantic = [r["semantic_grade"]["label"] == "pass" for r in subset if r.get("semantic_grade")]
            lines.append(f"| {backend} | {axis.replace('_', ' ')} | {len(subset)} | {percent(rate(structural))} | {percent(rate(semantic))} |")
            summary["backends"][backend][axis] = {"n": len(subset), "structural_pass_rate": rate(structural), "semantic_pass_rate": rate(semantic)}

    lines.extend(["", "## Guardrail diagnostics", "", "![Check rates](assets/check_pass_rates.svg)", "",
                  "| Backend | Route | Tool policy | Citation policy | Citation integrity | Query fidelity |", "|---|---:|---:|---:|---:|---:|"])
    for backend in backends:
        values = []
        for check in ("route", "tool_policy", "citation_policy", "citation_integrity", "query_fidelity"):
            checks = [r["structural_grades"][check]["pass"] for r in complete if r["backend"] == backend and r.get("structural_grades")]
            values.append(percent(rate(checks)))
        lines.append(f"| {backend} | " + " | ".join(values) + " |")

    ranked_axes = sorted(
        ((label, value) for label, value in axis_rates.items() if value is not None),
        key=lambda item: item[1],
    )
    ranked_checks = sorted(
        ((label, value) for label, value in check_rates.items() if value is not None),
        key=lambda item: item[1],
    )
    citation_rejections = sum(
        bool(row.get("citation_validation_failed")) for row in records
    )
    lines.extend(["", "## Variation and insights", ""])
    if ranked_axes:
        low_axis, low_rate = ranked_axes[0]
        high_axis, high_rate = ranked_axes[-1]
        lines.append(
            f"- Axis results range from **{percent(low_rate)}** for {low_axis} "
            f"to **{percent(high_rate)}** for {high_axis}; the "
            f"{(high_rate - low_rate) * 100:.1f}-point spread is hidden by an overall average."
        )
    if ranked_checks:
        low_check, low_check_rate = ranked_checks[0]
        high_check, high_check_rate = ranked_checks[-1]
        lines.append(
            f"- The weakest component is **{low_check}** at "
            f"**{percent(low_check_rate)}**; the strongest is **{high_check}** "
            f"at **{percent(high_check_rate)}**."
        )
    lines.extend([
        f"- Citation validation withholds **{citation_rejections}** responses in this run.",
        "- These observations locate structural pressure points; they do not explain "
        "tone, entailment, or whether a refusal is proportionate.",
    ])

    if calibration_data:
        metrics = calibration_data["metrics"]
        lines.extend([
            "", "## Judge calibration probe", "",
            "![Judge calibration](assets/judge_calibration.svg)", "",
            f"- Human-gold examples: {metrics['n']}",
            f"- Accuracy: {percent(metrics['accuracy'])}",
            f"- Macro-F1: {percent(metrics['macro_f1'])}",
            f"- Fail-class recall: {percent(metrics['per_label']['fail']['recall'])}",
            f"- Limitation: {metrics.get('independence_warning') or 'independent backend, pending broader human gold'}",
            "- This small probe measures basic rubric discrimination only; it cannot authorize automated release grading.",
        ])

    failures = [r for r in records if r.get("error") or (r.get("structural_grades") and not r["structural_grades"]["overall"]["pass"]) or r.get("semantic_grade", {}).get("label") == "fail"]
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    failures.sort(key=lambda r: (severity_order.get(r["case"]["severity"], 9), r["case"]["id"]))
    lines.extend(["", "## Failure register", "", "| Severity | Backend | Case | Axis | Structural failures | Semantic result |", "|---|---|---|---|---|---|"])
    for item in failures:
        checks = item.get("structural_grades", {})
        failed = ", ".join(k for k, v in checks.items() if k != "overall" and not v.get("pass")) or ("execution error" if item.get("error") else "none")
        semantic = item.get("semantic_grade", {}).get("label", "not judged")
        lines.append(f"| {item['case']['severity']} | {item['backend']} | {item['case']['id']} | {item['case']['axis']} | {failed} | {semantic} |")
    if not failures:
        lines.append("| — | — | — | — | No observed failures | — |")

    lines.extend([
        "", "## Scope and interpretation", "",
        "The run isolates conversation memory while reusing immutable retrieval "
        "resources. Structural grading measures visible application behavior: route, "
        "tool policy, citation policy and integrity, and exact query fidelity.",
        "",
        "It does not establish claim-to-source entailment, unbiased tone, or "
        "proportionate refusal. Counterfactual pairs still need pairwise human review, "
        "and one generation per case does not measure stochastic variation. Execution "
        "errors remain failures and are never removed from denominators.",
        "", "## Recommended next gates", "",
        "1. Obtain an independent frontier judge and expand human gold to at least 200 stratified examples.",
        "2. Human-review every critical failure, every judge disagreement, and a random passing sample.",
        "3. Add claim-to-source entailment grading before treating hallucination scores as complete.",
        "4. Run at least three repetitions and adversarial mutations on a sealed holdout.",
        "5. Block release on any verified critical harmful compliance or fabricated citation.",
        "", "## Reproducibility artifacts", "",
        f"- Raw results: {results}",
        f"- Run manifest: {results.with_suffix('.manifest.json')}",
        "- Dataset: evaluation/datasets/core.v1.jsonl",
        "- Judge calibration dataset: evaluation/datasets/judge_gold.v1.jsonl",
    ])
    report = output_dir / "report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return report
