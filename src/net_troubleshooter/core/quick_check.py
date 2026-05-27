from __future__ import annotations

from .adapters import Diagnostics
from .models import CommandResult, ResultStatus


class QuickCheckService:
    def __init__(self, diagnostics: Diagnostics | None = None) -> None:
        self.diagnostics = diagnostics or Diagnostics()

    def run(self) -> list[CommandResult]:
        results: list[CommandResult] = []
        interfaces = self.diagnostics.interfaces()
        results.append(interfaces)

        routes = self.diagnostics.routes()
        results.append(routes)

        gateway = routes.details.get("default_gateway")
        if gateway:
            results.append(self.diagnostics.ping(str(gateway), count=3))
        else:
            results.append(CommandResult(
                name="Ping default gateway",
                command="ping",
                args=[],
                status=ResultStatus.SKIPPED,
                summary="Skipped gateway ping because no default gateway was found.",
            ))

        results.append(self.diagnostics.ping("1.1.1.1", count=3))
        results.append(self.diagnostics.dns_lookup("example.com"))
        results.append(self.diagnostics.http_check("https://example.com"))
        return results
