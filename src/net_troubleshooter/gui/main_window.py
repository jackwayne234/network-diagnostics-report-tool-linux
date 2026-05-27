from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from net_troubleshooter.core.adapters import Diagnostics
from net_troubleshooter.core.diagnosis import OverallDiagnosis, build_overall_diagnosis
from net_troubleshooter.core.models import CommandResult, ResultStatus
from net_troubleshooter.core.quick_check import QuickCheckService
from net_troubleshooter.core.reports import timestamped_report_filename, write_report
from net_troubleshooter.core.website_check import WebsiteCheckService
from net_troubleshooter.gui.widgets import ResultCard


class WorkerSignals(QObject):
    finished = Signal(list)
    log = Signal(str)


class QuickCheckWorker(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        self.signals.log.emit("Quick Check started.")
        results = QuickCheckService().run()
        self.signals.log.emit("Quick Check finished.")
        self.signals.finished.emit(results)


class WebsiteCheckWorker(QRunnable):
    def __init__(self, service: WebsiteCheckService, target: str) -> None:
        super().__init__()
        self.service = service
        self.target = target
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        self.signals.log.emit("Website not loading guided check started.")
        results = self.service.run(self.target)
        self.signals.log.emit("Website not loading guided check finished.")
        self.signals.finished.emit(results)


class SingleCheckWorker(QRunnable):
    def __init__(self, fn, label: str) -> None:
        super().__init__()
        self.fn = fn
        self.label = label
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        self.signals.log.emit(f"{self.label} started.")
        result = self.fn()
        self.signals.log.emit(f"{self.label} finished.")
        self.signals.finished.emit([result])


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Network Diagnostics Report Tool")
        self.resize(1100, 760)
        self.thread_pool = QThreadPool.globalInstance()
        self.diagnostics = Diagnostics()
        self.recent_runs: list[list[CommandResult]] = []
        self.latest_results: list[CommandResult] = []
        self.latest_overall_diagnosis: OverallDiagnosis | None = None
        self.check_running = False
        self.active_workers: list[QRunnable] = []
        self.logs: list[str] = []

        tabs = QTabWidget()
        tabs.addTab(self._dashboard_tab(), "Dashboard")
        tabs.addTab(self._tests_tab(), "Tests")
        tabs.addTab(self._local_network_tab(), "Local Network")
        tabs.addTab(self._guided_tab(), "Guided Checks")
        tabs.addTab(self._reports_tab(), "Reports")
        tabs.addTab(self._logs_tab(), "Logs")
        self.setCentralWidget(tabs)

    def _dashboard_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("<h1>Network Dashboard</h1>")
        subtitle = QLabel("Linux-only, read-only diagnostics. Click Quick Check to test adapter, gateway, internet, DNS, and HTTPS.")
        subtitle.setWordWrap(True)
        button = QPushButton("Run Quick Check")
        button.setMinimumHeight(44)
        button.clicked.connect(self.run_quick_check)
        self.dashboard_results = self._result_area()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(button)
        layout.addWidget(self.dashboard_results["scroll"])
        return page

    def _tests_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>Manual Tests</h2>"))
        self.test_results = self._result_area()

        ping_row = self._input_row("Ping target", "1.1.1.1", lambda text: self._run_single(lambda: self.diagnostics.ping(text), "Ping", self.test_results))
        dns_row = self._input_row("DNS lookup", "example.com", lambda text: self._run_single(lambda: self.diagnostics.dns_lookup(text), "DNS lookup", self.test_results))
        trace_row = self._input_row("Trace route", "example.com", lambda text: self._run_single(lambda: self.diagnostics.trace_route(text), "Trace route", self.test_results))
        web_row = self._input_row("Website/HTTPS", "https://example.com", lambda text: self._run_single(lambda: self.diagnostics.http_check(text), "Website/HTTPS", self.test_results))
        port_row = self._port_row()
        for row in [ping_row, dns_row, trace_row, web_row, port_row]:
            layout.addLayout(row)
        layout.addWidget(self.test_results["scroll"])
        return page

    def _local_network_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>Local Network View</h2>"))
        self.local_results = self._result_area()
        for text, fn in [
            ("Load Routes", self.diagnostics.routes),
            ("Load Neighbors / ARP", self.diagnostics.neighbors),
            ("Load Listening Ports", self.diagnostics.listening_ports),
            ("Load Active Connections", self.diagnostics.active_connections),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, f=fn, label=text: self._run_single(f, label, self.local_results))
            layout.addWidget(btn)
        layout.addWidget(self.local_results["scroll"])
        return page

    def _guided_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>Guided Checks</h2>"))
        intro = QLabel("v0.1 guided flows are read-only and run step-by-step. Results can be exported from the Reports tab.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        no_internet = QPushButton("No internet — run guided check")
        no_internet.clicked.connect(self.run_quick_check)
        layout.addWidget(no_internet)

        website_help = QLabel("Website not loading: enter a URL or hostname. The app checks input, DNS, TCP ports 443/80, TLS for HTTPS, and HTTP status/redirects.")
        website_help.setWordWrap(True)
        layout.addWidget(website_help)
        website_row = QHBoxLayout()
        website_row.addWidget(QLabel("Website"))
        self.website_target_field = QLineEdit("https://example.com")
        website_button = QPushButton("Run Website not loading check")
        website_button.clicked.connect(lambda: self.run_website_check(self.website_target_field.text()))
        website_row.addWidget(self.website_target_field)
        website_row.addWidget(website_button)
        layout.addLayout(website_row)

        self.guided_results = self._result_area()
        layout.addWidget(self.guided_results["scroll"])
        return page

    def _reports_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("<h2>Reports</h2>"))
        text = QLabel(
            "Export is explicit: nothing is saved until you click Export. "
            "Choose Markdown or JSON. Redaction is enabled by default."
        )
        text.setWordWrap(True)
        self.report_status_label = QLabel("Run a diagnostic first, then export the latest/current-session results.")
        self.report_status_label.setWordWrap(True)
        self.redact_reports_checkbox = QCheckBox("Redact sensitive values by default")
        self.redact_reports_checkbox.setChecked(True)

        md_button = QPushButton("Export latest run as Markdown")
        json_button = QPushButton("Export latest run as JSON")
        md_button.clicked.connect(lambda: self._export_latest_report("md"))
        json_button.clicked.connect(lambda: self._export_latest_report("json"))

        layout.addWidget(text)
        layout.addWidget(self.redact_reports_checkbox)
        layout.addWidget(md_button)
        layout.addWidget(json_button)
        layout.addWidget(self.report_status_label)
        layout.addStretch()
        return page

    def _logs_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.logs_label = QLabel("App logs for this session will appear here.")
        self.logs_label.setWordWrap(True)
        layout.addWidget(QLabel("<h2>Logs / Debug</h2>"))
        layout.addWidget(self.logs_label)
        layout.addStretch()
        return page

    def _result_area(self) -> dict[str, QWidget | QVBoxLayout]:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return {"scroll": scroll, "content": content, "layout": layout}

    def _input_row(self, label: str, default: str, callback) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        field = QLineEdit(default)
        button = QPushButton("Run")
        button.clicked.connect(lambda: callback(field.text()))
        row.addWidget(field)
        row.addWidget(button)
        return row

    def _port_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("TCP port check"))
        host = QLineEdit("example.com")
        port = QLineEdit("443")
        button = QPushButton("Run")
        button.clicked.connect(lambda: self._run_single(lambda: self.diagnostics.tcp_port_check(host.text(), port.text()), "TCP port check", self.test_results))
        row.addWidget(host)
        row.addWidget(port)
        row.addWidget(button)
        return row

    def run_quick_check(self) -> None:
        self._clear_results(self.dashboard_results)
        self.latest_results = []
        self.latest_overall_diagnosis = None
        self.check_running = True
        if hasattr(self, "report_status_label"):
            self.report_status_label.setText("Quick Check is running. Export will be available when it finishes.")
        worker = QuickCheckWorker()
        worker.signals.finished.connect(lambda results, w=worker: self._finish_worker(w, results, self.dashboard_results, append=False))
        worker.signals.log.connect(self._log)
        self._start_worker(worker)

    def run_website_check(self, target: str) -> None:
        self._clear_results(self.guided_results)
        self.latest_results = []
        self.latest_overall_diagnosis = None
        self.check_running = True
        if hasattr(self, "report_status_label"):
            self.report_status_label.setText("Website not loading guided check is running. Export will be available when it finishes.")
        worker = WebsiteCheckWorker(WebsiteCheckService(self.diagnostics), target)
        worker.signals.finished.connect(lambda results, w=worker: self._finish_worker(w, results, self.guided_results, append=False))
        worker.signals.log.connect(self._log)
        self._start_worker(worker)

    def _run_single(self, fn, label: str, area: dict[str, QWidget | QVBoxLayout], append: bool = True) -> None:
        self.check_running = True
        if hasattr(self, "report_status_label"):
            self.report_status_label.setText(f"{label} is running. Export will be available when it finishes.")
        worker = SingleCheckWorker(fn, label)
        retry_actions = {0: lambda _checked=False, f=fn, l=label, a=area: self._run_single(f, l, a, append=False)}
        worker.signals.finished.connect(lambda results, w=worker: self._finish_worker(w, results, area, append=append, retry_actions=retry_actions))
        worker.signals.log.connect(self._log)
        self._start_worker(worker)

    def _start_worker(self, worker: QRunnable) -> None:
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def _finish_worker(
        self,
        worker: QRunnable,
        results: list[CommandResult],
        area: dict[str, QWidget | QVBoxLayout],
        append: bool,
        retry_actions: dict[int, Callable[[], None]] | None = None,
    ) -> None:
        self.check_running = False
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        self._show_results(results, area, append=append, retry_actions=retry_actions)

    def _clear_results(self, area: dict[str, QWidget | QVBoxLayout]) -> None:
        layout = area["layout"]
        assert isinstance(layout, QVBoxLayout)
        while layout.count() > 1:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _show_results(
        self,
        results: list[CommandResult],
        area: dict[str, QWidget | QVBoxLayout],
        append: bool = False,
        retry_actions: dict[int, Callable[[], None]] | None = None,
    ) -> None:
        if not append:
            self._clear_results(area)
        layout = area["layout"]
        assert isinstance(layout, QVBoxLayout)
        retry_actions = retry_actions or {}
        overall = build_overall_diagnosis(results)
        self.latest_overall_diagnosis = overall
        layout.insertWidget(max(0, layout.count() - 1), ResultCard(self._overall_result_card(overall)))
        for index, result in enumerate(results):
            layout.insertWidget(max(0, layout.count() - 1), ResultCard(result, retry_callback=retry_actions.get(index)))
        self.latest_results = results
        self.recent_runs.append(results)
        if hasattr(self, "report_status_label"):
            self.report_status_label.setText(f"Latest run has {len(results)} result(s), ready to export.")

    def _overall_result_card(self, overall: OverallDiagnosis) -> CommandResult:
        status = ResultStatus.PASS if overall.status == "healthy" else ResultStatus.WARNING
        summary = overall.summary
        if overall.next_step:
            summary = f"{summary} Next step: {overall.next_step}"
        return CommandResult(
            name="Overall Diagnosis",
            command="internal-diagnosis",
            args=[],
            status=status,
            summary=summary,
            details=overall.to_dict(),
        )

    def _latest_results(self) -> list[CommandResult]:
        return self.latest_results

    def _export_latest_report(self, extension: str) -> None:
        results = self._latest_results()
        if not results:
            message = "Quick Check is still running. Wait for it to finish before exporting." if self.check_running else "Run a diagnostic check before exporting a report."
            QMessageBox.information(self, "No results to export", message)
            return

        suffix = ".json" if extension == "json" else ".md"
        file_filter = "JSON reports (*.json)" if extension == "json" else "Markdown reports (*.md)"
        default_name = timestamped_report_filename(extension)
        path, _ = QFileDialog.getSaveFileName(self, "Export diagnostic report", default_name, file_filter)
        if not path:
            return
        if not path.lower().endswith(suffix):
            path += suffix

        redact = self.redact_reports_checkbox.isChecked()
        try:
            written = write_report(path, results, redact=redact, overall=self.latest_overall_diagnosis)
        except Exception as exc:  # pragma: no cover - GUI safety net
            self._log(f"Report export failed: {exc}")
            QMessageBox.critical(self, "Export failed", f"Could not export report:\n{exc}")
            return

        self._log(f"Report exported: {written}")
        self.report_status_label.setText(f"Exported report: {written}")
        QMessageBox.information(self, "Report exported", f"Saved report to:\n{written}")

    def _log(self, message: str) -> None:
        self.logs.append(message)
        self.logs_label.setText("<br>".join(self.logs[-50:]))
