from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .adapters import Diagnostics
from .models import CommandResult, ResultStatus


@dataclass(slots=True)
class WebsiteTarget:
    raw: str
    url: str
    hostname: str
    scheme: str


class WebsiteCheckService:
    def __init__(self, diagnostics: Diagnostics | None = None) -> None:
        self.diagnostics = diagnostics or Diagnostics()

    def run(self, user_input: str) -> list[CommandResult]:
        target = self._parse_target(user_input)
        if target is None:
            return [
                CommandResult(
                    name="Website input",
                    command="internal-website-input",
                    args=[],
                    status=ResultStatus.FAIL,
                    summary="Enter a website URL or hostname before running this guided check.",
                )
            ]

        results = [
            CommandResult(
                name=f"Website input {target.hostname}",
                command="internal-website-input",
                args=[target.raw],
                status=ResultStatus.PASS,
                summary=f"Website target recognized as {target.url}.",
                details={"hostname": target.hostname, "url": target.url, "scheme": target.scheme},
            )
        ]
        results.append(self._with_guidance(self.diagnostics.dns_lookup(target.hostname)))
        results.append(self._with_guidance(self.diagnostics.tcp_port_check(target.hostname, "443")))
        results.append(self._with_guidance(self.diagnostics.tcp_port_check(target.hostname, "80")))
        if target.scheme == "https":
            results.append(self._with_guidance(self.diagnostics.tls_certificate_summary(target.hostname)))
        results.append(self._with_guidance(self.diagnostics.http_check(target.url)))
        return results

    @staticmethod
    def _with_guidance(result: CommandResult) -> CommandResult:
        if result.status not in {ResultStatus.FAIL, ResultStatus.WARNING}:
            return result
        if result.name.startswith("DNS lookup"):
            result.details["likely_cause"] = "dns"
            result.details["next_step"] = "Check DNS settings or try another resolver; name lookup is likely the problem."
            result.summary = f"DNS name lookup appears to be failing. {result.summary}"
        elif result.name.startswith("HTTP status"):
            result.details["likely_cause"] = "web_tls_proxy_or_site"
            result.details["next_step"] = "Check the target site, firewall, proxy, captive portal, or TLS path."
            result.summary = f"Name lookup and TCP checks ran, but the website request failed. {result.summary}"
        return result

    @staticmethod
    def _parse_target(user_input: str) -> WebsiteTarget | None:
        raw = user_input.strip()
        if not raw:
            return None
        candidate = raw if "://" in raw else f"https://{raw}"
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        hostname = parsed.hostname
        return WebsiteTarget(raw=raw, url=candidate, hostname=hostname, scheme=parsed.scheme)
