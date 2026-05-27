import json
from datetime import datetime

from net_troubleshooter.core.models import CommandResult, ResultStatus
from net_troubleshooter.core.reports import results_to_json, results_to_markdown, timestamped_report_filename
from net_troubleshooter.core.redaction import redact_text
from net_troubleshooter.core.diagnosis import build_overall_diagnosis


def sample_result():
    return CommandResult(
        name="Sample",
        command="curl",
        args=["-I", "https://example.com/path?q=abc"],
        status=ResultStatus.PASS,
        summary="Connected to 8.8.8.8 with MAC aa:bb:cc:dd:ee:ff",
        stdout="Authorization: Bearer ABC123\nHTTP/2 200\n192.168.1.12 aa:bb:cc:dd:ee:ff",
        stderr="",
        exit_code=0,
    )


def guided_failure_result():
    return CommandResult(
        name="DNS lookup example.com",
        command="dig",
        args=["+short", "example.com"],
        status=ResultStatus.FAIL,
        summary="DNS name lookup appears to be failing.",
        details={
            "likely_cause": "dns",
            "next_step": "Check DNS settings or try another resolver.",
        },
    )


def test_redact_text_hides_sensitive_values():
    text = redact_text(
        "Authorization: Bearer ABC123 "
        "aa:bb:cc:dd:ee:ff IP 8.8.8.8 "
        "https://x.test/a?q=abc altname enx10ffe0d820b5 inet6 fe80::12ff:e0ff:fed8:20b5/64"
    )
    assert "Bearer ABC123" not in text
    assert "aa:bb:cc:dd:ee:ff" not in text
    assert "8.8.8.8" not in text
    assert "q=abc" not in text
    assert "enx10ffe0d820b5" not in text
    assert "fe80::12ff:e0ff:fed8:20b5" not in text


def test_redact_text_preserves_timestamps():
    text = redact_text("Created at: 2026-05-26T01:28:17+00:00")
    assert "2026-05-26T01:28:17+00:00" in text


def test_json_report_redacts_by_default():
    payload = results_to_json([sample_result()])
    data = json.loads(payload)
    dumped = json.dumps(data)
    assert data["app"] == "Network Diagnostics Report Tool"
    assert data["redaction_enabled"] is True
    assert "aa:bb:cc:dd:ee:ff" not in dumped
    assert "Bearer ABC123" not in dumped
    assert "8.8.8.8" not in dumped


def test_markdown_report_contains_summary_and_redacts():
    md = results_to_markdown([sample_result()])
    assert "# Network Diagnostics Report" in md
    assert "Sample" in md
    assert "aa:bb:cc:dd:ee:ff" not in md
    assert "Bearer ABC123" not in md
    assert "8.8.8.8" not in md


def test_markdown_report_redacts_result_names_and_headings():
    result = CommandResult(
        name="Ping 192.168.0.1",
        command="ping",
        args=["192.168.0.1"],
        status=ResultStatus.PASS,
        summary="192.168.0.1 is reachable.",
    )
    md = results_to_markdown([result])
    assert "Ping 192.168.0.1" not in md
    assert "### Ping 192.168.0.1" not in md
    assert "192.168.0.1" not in md


def test_markdown_report_includes_overall_diagnosis():
    diagnosis = build_overall_diagnosis([sample_result()])
    md = results_to_markdown([sample_result()], overall=diagnosis)
    assert "## Overall Diagnosis" in md
    assert "Status:" in md
    assert diagnosis.summary in md


def test_json_report_includes_overall_diagnosis():
    diagnosis = build_overall_diagnosis([sample_result()])
    payload = results_to_json([sample_result()], overall=diagnosis)
    data = json.loads(payload)
    assert "overall" in data
    assert data["overall"]["status"] == diagnosis.status
    assert data["overall"]["summary"] == diagnosis.summary


def test_json_report_has_stable_handoff_schema_metadata():
    payload = results_to_json([sample_result()])
    data = json.loads(payload)

    assert data["schema_version"] == "1.0"
    assert data["diagnostic_run"] == {
        "report_kind": "network_diagnostics",
        "platform": "linux",
        "source": "local_gui",
        "intended_consumer": "future_troubleshooting_tool",
    }


def test_json_report_promotes_result_guidance_for_future_importer():
    payload = results_to_json([guided_failure_result()], redact=False)
    data = json.loads(payload)
    result = data["results"][0]

    assert result["likely_cause"] == "dns"
    assert result["next_step"] == "Check DNS settings or try another resolver."
    assert result["details"]["likely_cause"] == "dns"
    assert result["details"]["next_step"] == "Check DNS settings or try another resolver."


def test_markdown_report_includes_result_next_safe_step():
    result = CommandResult(
        name="DNS lookup example.com",
        command="dig",
        args=["+short", "example.com"],
        status=ResultStatus.FAIL,
        summary="DNS name lookup appears to be failing.",
        details={"next_step": "Check DNS settings or try another resolver."},
    )

    md = results_to_markdown([result], redact=False)

    assert "- Next safe step: Check DNS settings or try another resolver." in md


def test_timestamped_report_filename_uses_date_and_time():
    filename = timestamped_report_filename("json", now=datetime(2026, 5, 26, 14, 7, 9))

    assert filename == "network-diagnostics-report-2026-05-26_14-07-09.json"


def test_timestamped_report_filename_supports_markdown_extension():
    filename = timestamped_report_filename("md", now=datetime(2026, 5, 26, 14, 7, 9))

    assert filename == "network-diagnostics-report-2026-05-26_14-07-09.md"
