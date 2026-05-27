from __future__ import annotations

import time

from PySide6.QtWidgets import QApplication, QPushButton

from net_troubleshooter.core.models import CommandResult, ResultStatus
from net_troubleshooter.core.reports import timestamped_report_filename
from net_troubleshooter.gui.main_window import MainWindow


class FakeWebsiteDiagnostics:
    def dns_lookup(self, target="example.com"):
        return CommandResult(f"DNS lookup {target}", "dig", [target], ResultStatus.PASS, "dns ok")

    def tcp_port_check(self, host, port):
        return CommandResult(f"TCP port {host}:{port}", "nc", [host, port], ResultStatus.PASS, "port ok")

    def tls_certificate_summary(self, host):
        return CommandResult(f"TLS certificate {host}", "openssl", [host], ResultStatus.PASS, "tls ok")

    def http_check(self, url="https://example.com"):
        return CommandResult(f"HTTP status {url}", "curl", [url], ResultStatus.PASS, "http ok")


class FlakyManualDiagnostics:
    def __init__(self):
        self.calls = 0

    def ping(self, target):
        self.calls += 1
        if self.calls == 1:
            return CommandResult(
                f"Ping {target}",
                "ping",
                [target],
                ResultStatus.FAIL,
                "first attempt failed",
            )
        return CommandResult(
            f"Ping {target}",
            "ping",
            [target],
            ResultStatus.PASS,
            "retry passed",
        )


def get_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def wait_until(app, predicate, timeout_seconds: float = 20.0):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_report_latest_results_updates_when_dashboard_results_are_shown():
    get_app()
    window = MainWindow()
    result = CommandResult(
        name="Quick Check Sample",
        command="ping",
        args=["-c", "1", "1.1.1.1"],
        status=ResultStatus.PASS,
        summary="Sample quick check passed.",
    )

    window._show_results([result], window.dashboard_results)

    assert window._latest_results() == [result]
    assert "ready to export" in window.report_status_label.text()


def test_export_dialog_default_filename_is_timestamped(monkeypatch):
    get_app()
    window = MainWindow()
    result = CommandResult("Sample", "ping", ["1.1.1.1"], ResultStatus.PASS, "ok")
    captured = {}

    def fake_get_save_file_name(parent, title, default_name, file_filter):
        captured["default_name"] = default_name
        return "", ""

    monkeypatch.setattr("net_troubleshooter.gui.main_window.QFileDialog.getSaveFileName", fake_get_save_file_name)
    monkeypatch.setattr("net_troubleshooter.gui.main_window.timestamped_report_filename", lambda extension: f"fixed-stamp.{extension}")
    window._show_results([result], window.dashboard_results)

    window._export_latest_report("json")

    assert captured["default_name"] == "fixed-stamp.json"


def test_quick_check_results_become_exportable_after_worker_finishes():
    app = get_app()
    window = MainWindow()

    window.run_quick_check()

    assert window.latest_results == []
    assert "running" in window.report_status_label.text().lower()
    assert wait_until(app, lambda: bool(window.latest_results) and not window.check_running)
    assert window._latest_results()
    assert "ready to export" in window.report_status_label.text()


def test_show_results_creates_overall_diagnosis_for_export_and_summary_card():
    get_app()
    window = MainWindow()
    results = [
        CommandResult("Interfaces", "ip", ["addr"], ResultStatus.PASS, "ok"),
        CommandResult("Routes", "ip", ["route"], ResultStatus.PASS, "ok"),
        CommandResult("Ping 192.168.0.1", "ping", [], ResultStatus.PASS, "ok", details={"avg_latency_ms": 2.0}),
        CommandResult("Ping 1.1.1.1", "ping", [], ResultStatus.PASS, "ok", details={"avg_latency_ms": 20.0}),
        CommandResult("DNS lookup example.com", "dig", [], ResultStatus.PASS, "ok"),
        CommandResult("HTTPS check https://example.com", "curl", [], ResultStatus.PASS, "ok"),
    ]

    window._show_results(results, window.dashboard_results)

    assert window.latest_overall_diagnosis is not None
    assert window.latest_overall_diagnosis.status == "healthy"
    assert "All 6 checks passed" in window.latest_overall_diagnosis.summary


def test_website_guided_check_results_become_exportable_after_worker_finishes():
    app = get_app()
    window = MainWindow()
    window.diagnostics = FakeWebsiteDiagnostics()

    window.run_website_check("example.com")

    assert window.latest_results == []
    assert "Website not loading" in window.report_status_label.text()
    assert wait_until(app, lambda: bool(window.latest_results) and not window.check_running)
    assert [result.name for result in window._latest_results()] == [
        "Website input example.com",
        "DNS lookup example.com",
        "TCP port example.com:443",
        "TCP port example.com:80",
        "TLS certificate example.com",
        "HTTP status https://example.com",
    ]
    assert window.latest_overall_diagnosis is not None
    assert "ready to export" in window.report_status_label.text()


def test_retry_button_reruns_only_failed_manual_check_and_replaces_result():
    app = get_app()
    window = MainWindow()
    diagnostics = FlakyManualDiagnostics()
    window.diagnostics = diagnostics

    window._run_single(lambda: window.diagnostics.ping("example.com"), "Ping", window.test_results)
    assert wait_until(app, lambda: bool(window.latest_results) and not window.check_running)
    assert diagnostics.calls == 1
    assert window.latest_results[0].status == ResultStatus.FAIL

    retry_buttons = [button for button in window.test_results["content"].findChildren(QPushButton) if button.text() == "Retry this check"]
    assert len(retry_buttons) == 1
    retry_buttons[0].click()

    assert wait_until(app, lambda: diagnostics.calls == 2 and not window.check_running)
    assert len(window.latest_results) == 1
    assert window.latest_results[0].status == ResultStatus.PASS
    assert window.latest_results[0].summary == "retry passed"
