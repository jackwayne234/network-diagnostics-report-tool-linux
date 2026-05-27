from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QFrame, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from net_troubleshooter.core.models import CommandResult, ResultStatus


STATUS_COLORS = {
    ResultStatus.PASS: "#1f7a3a",
    ResultStatus.WARNING: "#a56a00",
    ResultStatus.FAIL: "#b3261e",
    ResultStatus.SKIPPED: "#5f6368",
}


class ResultCard(QFrame):
    def __init__(self, result: CommandResult, parent: QWidget | None = None, retry_callback: Callable[[], None] | None = None) -> None:
        super().__init__(parent)
        self.result = result
        self.retry_callback = retry_callback
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("QFrame { border: 1px solid #d0d0d0; border-radius: 8px; padding: 8px; }")
        layout = QVBoxLayout(self)

        color = STATUS_COLORS.get(result.status, "#5f6368")
        title = QLabel(f"<b style='color:{color}'>{result.status.value.upper()}</b> — {result.name}")
        summary = QLabel(result.summary)
        summary.setWordWrap(True)
        meta = QLabel(f"Command: <code>{result.display_command or result.command}</code> · {result.duration_seconds:.3f}s")
        meta.setWordWrap(True)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setVisible(False)
        self.details.setPlainText(self._details_text(result))
        self.details.setMinimumHeight(120)

        toggle = QPushButton("Show command/details")
        toggle.clicked.connect(self._toggle_details)

        layout.addWidget(title)
        layout.addWidget(summary)
        layout.addWidget(meta)
        if self._can_retry(result):
            retry = QPushButton("Retry this check")
            retry.clicked.connect(self.retry_callback)
            layout.addWidget(retry)
        layout.addWidget(toggle)
        layout.addWidget(self.details)

    def _toggle_details(self) -> None:
        self.details.setVisible(not self.details.isVisible())

    def _can_retry(self, result: CommandResult) -> bool:
        return self.retry_callback is not None and (result.status == ResultStatus.FAIL or result.timed_out)

    @staticmethod
    def _details_text(result: CommandResult) -> str:
        parts = [
            f"Command: {result.display_command}",
            f"Exit code: {result.exit_code}",
            f"Started: {result.started_at}",
            f"Ended: {result.ended_at}",
            f"Timed out: {result.timed_out}",
            f"Missing tool: {result.missing_tool}",
            "",
            "STDOUT:",
            result.stdout or "(empty)",
            "",
            "STDERR:",
            result.stderr or "(empty)",
        ]
        return "\n".join(parts)
