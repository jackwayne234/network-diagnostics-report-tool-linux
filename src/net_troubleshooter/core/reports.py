from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import CommandResult
from .redaction import redact_text, redact_value
from .diagnosis import OverallDiagnosis


def timestamped_report_filename(extension: str, now: datetime | None = None) -> str:
    extension = extension.lower().lstrip(".")
    if extension == "markdown":
        extension = "md"
    now = now or datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    return f"network-diagnostics-report-{stamp}.{extension}"


def _result_to_report_dict(result: CommandResult) -> dict:
    data = result.to_dict()
    data["likely_cause"] = result.details.get("likely_cause")
    data["next_step"] = result.details.get("next_step")
    return data


def results_to_json(results: list[CommandResult], redact: bool = True, overall: OverallDiagnosis | None = None) -> str:
    payload = {
        "schema_version": "1.0",
        "app": "Network Diagnostics Report Tool",
        "version": "0.1.0",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "redaction_enabled": redact,
        "diagnostic_run": {
            "report_kind": "network_diagnostics",
            "platform": "linux",
            "source": "local_gui",
            "intended_consumer": "future_troubleshooting_tool",
        },
        "overall": overall.to_dict() if overall else None,
        "results": [_result_to_report_dict(result) for result in results],
    }
    if redact:
        payload = redact_value(payload)
    return json.dumps(payload, indent=2, sort_keys=True)


def results_to_markdown(results: list[CommandResult], redact: bool = True, overall: OverallDiagnosis | None = None) -> str:
    lines = [
        "# Network Diagnostics Report",
        "",
        f"- Created at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Redaction enabled: {'yes' if redact else 'no'}",
        "",
    ]
    if overall:
        summary = redact_text(overall.summary) if redact else overall.summary
        next_step = redact_text(overall.next_step) if redact else overall.next_step
        likely = overall.likely_problem_area or "none"
        lines.extend([
            "## Overall Diagnosis",
            "",
            f"- Status: `{overall.status}`",
            f"- Likely problem area: `{likely}`",
            f"- Summary: {summary}",
            f"- Next step: {next_step}",
            "",
        ])
    lines.extend([
        "## Summary",
        "",
    ])
    for result in results:
        name = redact_text(result.name) if redact else result.name
        summary = redact_text(result.summary) if redact else result.summary
        lines.append(f"- **{result.status.value.upper()}** — {name}: {summary}")

    lines.extend(["", "## Details", ""])
    for result in results:
        name = redact_text(result.name) if redact else result.name
        command = result.display_command
        stdout = result.stdout or "(empty)"
        stderr = result.stderr or "(empty)"
        if redact:
            command = redact_text(command)
            stdout = redact_text(stdout)
            stderr = redact_text(stderr)
        next_step = result.details.get("next_step")
        if redact and isinstance(next_step, str):
            next_step = redact_text(next_step)
        detail_lines = [
            f"### {name}",
            "",
            f"- Status: `{result.status.value}`",
            f"- Summary: {redact_text(result.summary) if redact else result.summary}",
            f"- Command: `{command}`",
            f"- Exit code: `{result.exit_code}`",
            f"- Duration: `{result.duration_seconds:.3f}s`",
            f"- Timed out: `{result.timed_out}`",
            f"- Missing tool: `{result.missing_tool}`",
        ]
        if next_step:
            detail_lines.append(f"- Next safe step: {next_step}")
        detail_lines.extend([
            "",
            "#### STDOUT",
            "",
            "```text",
            stdout,
            "```",
            "",
            "#### STDERR",
            "",
            "```text",
            stderr,
            "```",
            "",
        ])
        lines.extend(detail_lines)
    return "\n".join(lines)


def write_report(path: str | Path, results: list[CommandResult], redact: bool = True, overall: OverallDiagnosis | None = None) -> Path:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        content = results_to_json(results, redact=redact, overall=overall)
    elif suffix in {".md", ".markdown"}:
        content = results_to_markdown(results, redact=redact, overall=overall)
    else:
        raise ValueError("Report path must end in .md or .json")
    path.write_text(content, encoding="utf-8")
    return path
