from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Sequence

from .models import CommandResult, ResultStatus, utc_now_iso


APT_SUGGESTIONS = {
    "dig": "sudo apt install dnsutils",
    "host": "sudo apt install dnsutils",
    "nslookup": "sudo apt install dnsutils",
    "traceroute": "sudo apt install traceroute",
    "tracepath": "sudo apt install iputils-tracepath",
    "nc": "sudo apt install netcat-openbsd",
    "iw": "sudo apt install iw",
    "curl": "sudo apt install curl",
    "ping": "sudo apt install iputils-ping",
    "openssl": "sudo apt install openssl",
    "ip": "sudo apt install iproute2",
    "ss": "sudo apt install iproute2",
    "resolvectl": "sudo apt install systemd-resolved",
    "rfkill": "sudo apt install rfkill",
}


class CommandRunner:
    """Safe read-only command runner. No shell strings are accepted."""

    def run(
        self,
        name: str,
        command: str,
        args: Sequence[str] | None = None,
        timeout: float = 8.0,
        success_summary: str | None = None,
        failure_summary: str | None = None,
    ) -> CommandResult:
        args = [str(a) for a in (args or [])]
        started = utc_now_iso()
        begin = time.monotonic()

        if shutil.which(command) is None:
            ended = utc_now_iso()
            suggestion = APT_SUGGESTIONS.get(command, f"Install `{command}` with your package manager.")
            return CommandResult(
                name=name,
                command=command,
                args=args,
                status=ResultStatus.SKIPPED,
                summary=f"`{command}` is not installed, so this check was skipped. Ubuntu/Debian: {suggestion}",
                started_at=started,
                ended_at=ended,
                duration_seconds=round(time.monotonic() - begin, 3),
                missing_tool=True,
                details={"install_suggestion": suggestion},
            )

        try:
            completed = subprocess.run(
                [command, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            ended = utc_now_iso()
            return CommandResult(
                name=name,
                command=command,
                args=args,
                status=ResultStatus.WARNING,
                summary=f"Timed out after {timeout:g} seconds. You can retry this check.",
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                started_at=started,
                ended_at=ended,
                duration_seconds=round(time.monotonic() - begin, 3),
                timed_out=True,
            )

        ended = utc_now_iso()
        ok = completed.returncode == 0
        return CommandResult(
            name=name,
            command=command,
            args=args,
            status=ResultStatus.PASS if ok else ResultStatus.FAIL,
            summary=(success_summary if ok else failure_summary) or ("Command completed." if ok else "Command failed."),
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            started_at=started,
            ended_at=ended,
            duration_seconds=round(time.monotonic() - begin, 3),
        )
