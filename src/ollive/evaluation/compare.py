"""Before/after comparison for two runs of the same evaluation dataset."""
from __future__ import annotations

import json
from pathlib import Path

from ollive.evaluation.report import bar_chart, load_records, percent, rate


def structural_rate(rows, axis=None):
    """Return the structural pass rate for one backend run."""
    subset = [r for r in rows if not r.get("error") and (axis is None or r["case"]["axis"] == axis)]
    return rate([r["structural_grades"]["overall"]["pass"] for r in subset])


def generate_comparison(baseline, candidate, output_dir):
    """Compare archived backend runs and write their reader-facing report."""
    before = load_records(baseline)
    after = load_records(candidate)
    before_ids = [r["case"]["id"] for r in before]
    after_ids = [r["case"]["id"] for r in after]
    if before_ids != after_ids:
        raise ValueError("Runs must contain the same ordered case IDs")
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = output_dir / "assets"
    assets.mkdir(exist_ok=True)
    axes = ["hallucination", "bias_harm", "content_safety"]
    chart = {}
    for axis in axes:
        chart[f"baseline · {axis.replace('_', ' ')}"] = structural_rate(before, axis)
        chart[f"prompt v2 · {axis.replace('_', ' ')}"] = structural_rate(after, axis)
    bar_chart(assets / "before_after_axes.svg", "Prompt change: structural rates", chart)

    before_fail = {
        r["case"]["id"] for r in before
        if r.get("error") or not r.get("structural_grades", {}).get("overall", {}).get("pass", False)
    }
    after_fail = {
        r["case"]["id"] for r in after
        if r.get("error") or not r.get("structural_grades", {}).get("overall", {}).get("pass", False)
    }
    fixed = sorted(before_fail - after_fail)
    residual = sorted(before_fail & after_fail)
    regressions = sorted(after_fail - before_fail)
    lines = [
        "# Prompt v2 controlled comparison", "",
        "| Field | Value |",
        "|---|---|",
        "| Objective | Determine which structural behaviors move when the prompt changes |",
        "| Controlled variables | Ordered 72-case dataset and Qwen 3.5 9B backend |",
        "| Changed variable | Prompt and associated guardrail instructions |",
        "| Sampling | One generation per case |",
        "", "## At a glance", "",
        "This is a directional before/after study, not a model comparison. It shows "
        "which failures move with the prompt while holding the candidate and ordered "
        "case set fixed. One sample per case cannot establish statistical stability.",
        "", "![Before and after rates](assets/before_after_axes.svg)", "",
        "## Results summary", "",
        "| Metric | Baseline | Prompt v2 | Change |",
        "|---|---:|---:|---:|",
    ]
    metrics = [("Overall", None)] + [(a.replace("_", " "), a) for a in axes]
    for label, axis in metrics:
        old = structural_rate(before, axis)
        new = structural_rate(after, axis)
        lines.append(f"| {label} | {percent(old)} | {percent(new)} | {(new-old)*100:+.1f} pp |")

    lines.extend(["", "## Guardrail components", "",
                  "| Check | Baseline | Prompt v2 | Change |", "|---|---:|---:|---:|"])
    for check in ("route", "tool_policy", "citation_policy", "citation_integrity", "query_fidelity"):
        old = rate([r["structural_grades"][check]["pass"] for r in before])
        new = rate([r["structural_grades"][check]["pass"] for r in after])
        lines.append(f"| {check.replace('_', ' ')} | {percent(old)} | {percent(new)} | {(new-old)*100:+.1f} pp |")

    old_rejections = sum(r["citation_validation_failed"] for r in before)
    new_rejections = sum(r["citation_validation_failed"] for r in after)
    axis_changes = {
        axis: structural_rate(after, axis) - structural_rate(before, axis)
        for axis in axes
    }
    strongest_axis = max(axis_changes, key=axis_changes.get)
    lines.extend([
        "", "## Variation and insight", "",
        f"- Overall structural passing changes by "
        f"**{(structural_rate(after) - structural_rate(before)) * 100:+.1f} percentage points**.",
        f"- The largest axis movement is **{strongest_axis.replace('_', ' ')}** "
        f"at **{axis_changes[strongest_axis] * 100:+.1f} points**.",
        f"- Citation withholding changes from **{old_rejections}** to "
        f"**{new_rejections}** responses.",
        "- Improvement is uneven: fixed cases, residual failures, and new regressions "
        "must be read together rather than reduced to the overall score.",
        "", "## Failure movement", "",
        f"- Fixed structural cases: {len(fixed)}",
        f"- Residual structural failures: {len(residual)}",
        f"- New structural regressions: {len(regressions)}",
        f"- Citation fail-closed responses: {old_rejections} → {new_rejections}",
        "", "### Fixed", "",
        ", ".join(fixed) or "None",
        "", "### Residual", "",
        ", ".join(residual) or "None",
        "", "### Regressions", "",
        ", ".join(regressions) or "None",
        "", "## Scope and interpretation", "",
        "Structural movement shows whether application-visible behavior changed. It "
        "does not establish semantic safety, truthfulness, or proportionate refusal. "
        "A valid marker can still support a narrower claim than the generated text.",
        "",
        "Because the core set informed prompt development and each case was sampled "
        "once, the result is regression evidence rather than a generalization claim. "
        "A sealed holdout, repeated sampling, an independent judge, and human review "
        "remain required.",
        "", "## Artifacts", "",
        f"- Baseline: {baseline}",
        f"- Prompt v2: {candidate}",
    ])
    report = output_dir / "report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "baseline_rate": structural_rate(before),
        "candidate_rate": structural_rate(after),
        "fixed": fixed,
        "residual": residual,
        "regressions": regressions,
        "citation_rejections": {"baseline": old_rejections, "candidate": new_rejections},
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return report
