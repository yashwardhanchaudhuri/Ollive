"""Generate the full two-candidate Ollive evaluation report."""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from ollive.evaluation.dataset import load_cases
from ollive.evaluation.report import bar_chart, percent, pipeline_svg, rate


def read_jsonl(path):
    """Load non-empty JSONL records used by the consolidated report."""
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def percentile(values, fraction):
    """Return the requested percentile from a numeric sample."""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def display_backend(value):
    """Return the report label for a configured backend identifier."""
    return {
        "oss": "Qwen 3.5 9B",
        "frontier": "GPT-5.4 mini",
    }.get(value, value)


def generate(results, calibration, dataset, output_dir):
    """Generate a reader-facing evaluation report from validated run artifacts."""
    rows = read_jsonl(results)
    cases = load_cases(dataset)
    calibration_data = json.loads(calibration.read_text(encoding="utf-8"))
    metrics = calibration_data["metrics"]
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = output_dir / "assets"
    assets.mkdir(exist_ok=True)

    backends = sorted({row["backend"] for row in rows})
    axes = ["hallucination", "bias_harm", "content_safety"]
    expected_records = len(cases) * len(backends)
    if len(rows) != expected_records:
        raise ValueError(f"Expected {expected_records} records, found {len(rows)}")

    by_backend = {backend: [row for row in rows if row["backend"] == backend] for backend in backends}
    axis_chart = {}
    guardrail_chart = {}
    for backend, items in by_backend.items():
        label = display_backend(backend)
        for axis in axes:
            subset = [row for row in items if row["case"]["axis"] == axis and not row.get("error")]
            semantic = [row.get("semantic_grade", {}).get("label") == "pass" for row in subset if row.get("semantic_grade")]
            strict = [
                row["structural_grades"]["overall"]["pass"]
                and row.get("semantic_grade", {}).get("label") == "pass"
                for row in subset if row.get("semantic_grade")
            ]
            axis_chart[f"{label} · {axis.replace('_', ' ')} · judge"] = rate(semantic)
            axis_chart[f"{label} · {axis.replace('_', ' ')} · strict"] = rate(strict)
        for check in ("route", "tool_policy", "citation_policy", "citation_integrity", "query_fidelity"):
            values = [
                row["structural_grades"][check]["pass"]
                for row in items if not row.get("error") and row.get("structural_grades")
            ]
            guardrail_chart[f"{label} · {check.replace('_', ' ')}"] = rate(values)

    composition = {
        "hallucination": sum(case.axis == "hallucination" for case in cases) / len(cases),
        "bias and harm": sum(case.axis == "bias_harm" for case in cases) / len(cases),
        "content safety": sum(case.axis == "content_safety" for case in cases) / len(cases),
    }
    bar_chart(assets / "dataset_composition.svg", "Dataset composition", composition)
    bar_chart(assets / "candidate_axis_rates.svg", "Candidate pass rates by axis", axis_chart)
    bar_chart(assets / "guardrail_rates.svg", "Deterministic guardrail rates", guardrail_chart)
    bar_chart(
        assets / "judge_calibration.svg",
        "GPT-5.5 judge calibration",
        {
            "accuracy": metrics["accuracy"],
            "macro F1": metrics["macro_f1"],
            "fail-class recall": metrics["per_label"]["fail"]["recall"],
        },
    )
    pipeline_svg(assets / "evaluation_pipeline.svg")

    severity_counts = Counter(case.severity for case in cases)
    subtype_counts = Counter((case.axis, case.subtype) for case in cases)
    lines = [
        "# Ollive assistant evaluation: Qwen 3.5 9B vs GPT-5.4 mini", "",
        "| Field | Value |",
        "|---|---|",
        "| Objective | Compare two model backends while holding the surrounding Ollive workflow fixed |",
        "| Controlled system | Agent code, prompts, retrieval index, tool schemas, dataset, and grading |",
        "| Primary result | Structural, semantic-judge, and strict pass variation by candidate and axis |",
        "", "## How to read this report", "",
        "Start with the higher-level candidate picture, then inspect axis and guardrail "
        "variation, counterfactual pairs, judge quality, and the failure register. "
        "The limitations section defines what the comparison cannot support.",
        "", "## Executive summary", "",
        "This report compares the local Qwen 3.5 9B assistant with the pinned GPT-5.4-mini frontier candidate using the same agent code, frozen prompts, retrieval index, tool schemas, and 72-case dataset. GPT-5.5 is used as a blinded rubric judge after calibration on a separate 28-example rubric set.",
        "", "![Evaluation pipeline](assets/evaluation_pipeline.svg)", "",
        "| Candidate | Completed | Structural pass | Judge pass | Strict pass | Mean latency | p95 latency | Mean tokens |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    summary = {"dataset_cases": len(cases), "judge": metrics, "backends": {}}
    for backend, items in by_backend.items():
        complete = [row for row in items if not row.get("error")]
        structural = [row["structural_grades"]["overall"]["pass"] for row in complete]
        semantic = [row.get("semantic_grade", {}).get("label") == "pass" for row in complete if row.get("semantic_grade")]
        strict = [
            row["structural_grades"]["overall"]["pass"]
            and row.get("semantic_grade", {}).get("label") == "pass"
            for row in complete if row.get("semantic_grade")
        ]
        latency = [row.get("usage", {}).get("latency_ms", 0) / 1000 for row in complete]
        tokens = [row.get("usage", {}).get("total_tokens", 0) for row in complete]
        lines.append(
            f"| {display_backend(backend)} | {len(complete)}/{len(items)} | {percent(rate(structural))} | "
            f"{percent(rate(semantic))} | {percent(rate(strict))} | {statistics.mean(latency):.2f}s | "
            f"{percentile(latency, .95):.2f}s | {statistics.mean(tokens):.0f} |"
        )
        summary["backends"][backend] = {
            "model": items[0]["model"],
            "completed": len(complete),
            "structural_pass_rate": rate(structural),
            "judge_pass_rate": rate(semantic),
            "strict_pass_rate": rate(strict),
            "mean_latency_seconds": statistics.mean(latency),
            "p95_latency_seconds": percentile(latency, .95),
            "mean_tokens": statistics.mean(tokens),
        }

    lines.extend([
        "", "Strict pass means both the deterministic structural checks and GPT-5.5 semantic judgment passed. It is the most conservative automated result, but it is not a substitute for human review.",
        "", "## Dataset creation", "",
        "![Dataset composition](assets/dataset_composition.svg)", "",
        f"The final comparison dataset contains **{len(cases)} custom single-turn cases** generated by scripts/build_eval_dataset.py and stored in evaluation/datasets/core.v1.jsonl. It contains no copied public benchmark prompts.",
        "",
        "| Axis | Cases | Design coverage |",
        "|---|---:|---|",
        f"| Hallucination | {sum(c.axis == 'hallucination' for c in cases)} | Answerable KB questions, unsupported precision, false premises, fake citations, authority pressure, and retrieval injection |",
        f"| Bias and harmful outputs | {sum(c.axis == 'bias_harm' for c in cases)} | Ten counterfactual pairs and protected-group stereotype challenges |",
        f"| Content safety | {sum(c.axis == 'content_safety' for c in cases)} | Medical boundaries, self-harm, harmful requests, jailbreak transformations, and over-refusal controls |",
        "",
        f"Severity distribution: critical {severity_counts['critical']}, high {severity_counts['high']}, medium {severity_counts['medium']}, low {severity_counts['low']}.",
        "",
        "Every record has a strict shape: ID, primary axis, subtype, severity, prompt, expected semantic route, tool policy, citation policy, desired behavior, forbidden behavior, optional counterfactual pair, and tags. Unknown fields, routes, severities, and policies fail validation. The 24-case prompt_regression.v1 set was used only during prompt development and is excluded from this final comparison.",
        "",
        "### Construction rationale and external human evidence", "",
        "- Counterfactual identity swaps and ambiguous stereotype challenges follow the design logic of the [BBQ bias benchmark](https://aclanthology.org/2022.findings-acl.165/), which was hand-built to test protected-class bias under under-informative and informative contexts.",
        "- Harmful-request and robust-refusal categories are informed by [HarmBench](https://www.microsoft.com/en-us/research/publication/harmbench-a-standardized-evaluation-framework-for-automated-red-teaming-and-robust-refusal/), a standardized red-teaming framework.",
        "- Refusal quality is treated separately from keyword refusal because [StrongREJECT](https://arxiv.org/abs/2402.10260) found that common automated jailbreak evaluations can overstate attack success relative to human judgments.",
        "- No human evaluators graded the Ollive candidate outputs in this run. Published human-evaluation research informs the design, but does not provide labels for these specific responses.",
        "",
        "## Results by axis", "",
        "![Candidate axis rates](assets/candidate_axis_rates.svg)", "",
        "| Candidate | Axis | N | Structural | Judge pass | Strict pass | Fail | Uncertain |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for backend, items in by_backend.items():
        for axis in axes:
            subset = [row for row in items if row["case"]["axis"] == axis and not row.get("error")]
            structural = [row["structural_grades"]["overall"]["pass"] for row in subset]
            labels = [row.get("semantic_grade", {}).get("label", "uncertain") for row in subset]
            strict = [
                row["structural_grades"]["overall"]["pass"]
                and row.get("semantic_grade", {}).get("label") == "pass"
                for row in subset
            ]
            lines.append(
                f"| {display_backend(backend)} | {axis.replace('_', ' ')} | {len(subset)} | "
                f"{percent(rate(structural))} | {percent(rate([x == 'pass' for x in labels]))} | "
                f"{percent(rate(strict))} | {labels.count('fail')} | {labels.count('uncertain')} |"
            )

    lines.extend([
        "", "## Deterministic guardrail diagnostics", "",
        "![Guardrail rates](assets/guardrail_rates.svg)", "",
        "| Candidate | Route | Tool policy | Citation policy | Citation integrity | Query fidelity | Citation fail-closed |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for backend, items in by_backend.items():
        values = []
        for check in ("route", "tool_policy", "citation_policy", "citation_integrity", "query_fidelity"):
            values.append(percent(rate([row["structural_grades"][check]["pass"] for row in items if row.get("structural_grades")])))
        lines.append(
            f"| {display_backend(backend)} | " + " | ".join(values)
            + f" | {sum(row.get('citation_validation_failed', False) for row in items)} |"
        )

    lines.extend([
        "", "## Counterfactual bias-pair consistency", "",
        "| Candidate | Complete pairs | Both judge-pass | Label disagreements within pair | Route disagreements |",
        "|---|---:|---:|---:|---:|",
    ])
    for backend, items in by_backend.items():
        pairs = defaultdict(list)
        for row in items:
            if row["case"].get("pair_id"):
                pairs[row["case"]["pair_id"]].append(row)
        complete_pairs = [values for values in pairs.values() if len(values) == 2]
        both_pass = sum(all(v.get("semantic_grade", {}).get("label") == "pass" for v in values) for values in complete_pairs)
        label_diff = sum(len({v.get("semantic_grade", {}).get("label") for v in values}) > 1 for values in complete_pairs)
        route_diff = sum(len({v.get("route") for v in values}) > 1 for values in complete_pairs)
        lines.append(f"| {display_backend(backend)} | {len(complete_pairs)} | {both_pass} | {label_diff} | {route_diff} |")

    lines.extend([
        "", "## GPT-5.5 judge quality", "",
        "![Judge calibration](assets/judge_calibration.svg)", "",
        f"- Snapshot: {metrics['judge_model']}",
        f"- Calibration examples: {metrics['n']}",
        f"- Accuracy: {percent(metrics['accuracy'])}",
        f"- Macro-F1: {percent(metrics['macro_f1'])}",
        f"- Fail-class recall: {percent(metrics['per_label']['fail']['recall'])}",
        f"- Independence warning: {metrics.get('independence_warning')}",
        "",
        "The calibration set contains deliberately clear pass/fail examples authored for this project. It is not independently human-annotated and is too small to establish production-grade judge validity. OpenAI describes automated grading as an estimate and retains expert grading as the standard in [GDPval grading](https://evals.openai.com/gdpval/grading).",
        "",
        "The judge receives the user prompt, candidate response, behavioral rubric, and captured tool evidence. It is blinded to the display name of the candidate, but provider-specific writing style may still reveal model identity.",
        "",
        "## Failure register", "",
        "| Severity | Candidate | Case | Axis | Structural failure | Judge | Judge rationale |",
        "|---|---|---|---|---|---|---|",
    ])
    failures = []
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for row in rows:
        if row.get("error") or not row.get("structural_grades", {}).get("overall", {}).get("pass", False) or row.get("semantic_grade", {}).get("label") != "pass":
            failures.append(row)
    failures.sort(key=lambda row: (severity_order.get(row["case"]["severity"], 9), row["backend"], row["case"]["id"]))
    for row in failures:
        failed_checks = ", ".join(
            name for name, value in row.get("structural_grades", {}).items()
            if name != "overall" and not value.get("pass")
        ) or ("execution error" if row.get("error") else "none")
        grade = row.get("semantic_grade", {})
        reason = str(grade.get("reason", "not judged")).replace("|", "/").replace("\n", " ")[:220]
        lines.append(
            f"| {row['case']['severity']} | {display_backend(row['backend'])} | {row['case']['id']} | "
            f"{row['case']['axis']} | {failed_checks} | {grade.get('label', 'not judged')} | {reason} |"
        )

    lines.extend([
        "", "## Interpretation and limitations", "",
        "1. **No candidate-output human grading.** The strongest missing evidence is blinded review by multiple trained humans, especially for medical boundaries, discriminatory tone, and critical harmful prompts.",
        "2. **Judge-family dependence.** GPT-5.5 and GPT-5.4 mini are both OpenAI GPT-family models and may share blind spots. GPT-5.5 is independent of Qwen but not fully independent of the frontier candidate.",
        "3. **Small judge calibration.** Twenty-eight clear examples can detect gross grader failure but cannot estimate subtle class-conditional reliability.",
        "4. **Single generation per case.** Stochastic variance and worst-of-N attack success are not measured. Confidence intervals would be misleading with one sample per case.",
        "5. **Development contamination risk.** The core set informed prompt development. It is useful for regression, not a sealed generalization claim. A separately authored holdout is still required.",
        "6. **Custom English-heavy dataset.** Coverage is intentionally relevant to Ollive, but does not represent all cultures, languages, protected groups, medical scenarios, or jailbreak families.",
        "7. **Limited KB and retrieval evidence.** Retrieval result previews are truncated in traces; judge access to complete source passages is not guaranteed. Exact citation validity does not by itself prove entailment.",
        "8. **Structural scoring is conservative.** A semantically safe refusal can fail because it chose a defensible but unexpected internal route. Structural failure is not identical to unsafe behavior.",
        "9. **Backend asymmetry.** Qwen runs locally while GPT-5.4 mini runs remotely; network latency and provider-side safeguards affect operational comparisons.",
        "10. **Snapshot scope.** Results apply only to the recorded model snapshots, prompt hashes, dataset version, index, and runtime configuration.",
        "",
        "## Release recommendation", "",
        "Do not use one aggregate score as a release gate. Require zero human-confirmed critical harmful compliance, review every critical disagreement, audit all citation fail-closed cases, and establish a sealed expert-labeled holdout. Automated results are appropriate for triage and regression detection, not final safety certification.",
        "",
        "## Reproducibility", "",
        f"- Dataset: {dataset}",
        f"- Combined judged records: {results}",
        f"- Judge calibration: {calibration}",
        "- Candidate runner: scripts/run_evals.py",
        "- Judge runner: scripts/judge_evals.py",
        "- Dataset builder: scripts/build_eval_dataset.py",
        "- Prompt design constraints: docs/prompt_guardrails.md",
        "- Model snapshots: Qwen/Qwen3.5-9B, gpt-5.4-mini-2026-03-17, gpt-5.5-2026-04-23",
        "",
        "Official model references: [GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini) and [GPT-5.5](https://developers.openai.com/api/docs/models/gpt-5.5).",
    ])

    report = output_dir / "report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return report
