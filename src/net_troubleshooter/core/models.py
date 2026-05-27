from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ResultStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    SKIPPED = "skipped"


@dataclass(slots=True)
class CommandResult:
    name: str
    command: str
    args: list[str]
    status: ResultStatus
    summary: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    started_at: str = ""
    ended_at: str = ""
    duration_seconds: float = 0.0
    timed_out: bool = False
    missing_tool: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def display_command(self) -> str:
        return " ".join([self.command, *self.args]).strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "status": self.status.value,
            "summary": self.summary,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "timed_out": self.timed_out,
            "missing_tool": self.missing_tool,
            "details": self.details,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
