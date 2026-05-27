from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import CommandResult, ResultStatus


@dataclass(slots=True)
class OverallDiagnosis:
    status: str
    summary: str
    likely_problem_area: str | None = None
    next_step: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "likely_problem_area": self.likely_problem_area,
            "next_step": self.next_step,
            "metrics": self.metrics,
        }


def build_overall_diagnosis(results: list[CommandResult]) -> OverallDiagnosis:
    total = len(results)
    passed = sum(1 for r in results if r.status == ResultStatus.PASS)
    failed = sum(1 for r in results if r.status == ResultStatus.FAIL)
    warnings = sum(1 for r in results if r.status == ResultStatus.WARNING)
    skipped = sum(1 for r in results if r.status == ResultStatus.SKIPPED)
    metrics = {
        "checks_total": total,
        "checks_passed": passed,
        "checks_failed": failed,
        "checks_warning": warnings,
        "checks_skipped": skipped,
    }

    gateway_ping = _find_first(results, "Ping ", exclude="1.1.1.1")
    internet_ping = _find_by_name(results, "Ping 1.1.1.1")
    if gateway_ping and "avg_latency_ms" in gateway_ping.details:
        metrics["gateway_latency_ms"] = gateway_ping.details["avg_latency_ms"]
    if internet_ping and "avg_latency_ms" in internet_ping.details:
        metrics["internet_latency_ms"] = internet_ping.details["avg_latency_ms"]

    if total and passed == total:
        return OverallDiagnosis(
            status="healthy",
            summary=f"All {total} checks passed. No obvious network problem was detected.",
            likely_problem_area=None,
            next_step="If you are still having trouble, test the specific website or service that is failing.",
            metrics=metrics,
        )

    interfaces = _find_by_name(results, "Interfaces")
    routes = _find_by_name(results, "Routes")
    dns = _find_by_prefix(results, "DNS lookup")
    https = _find_by_prefix(results, "HTTPS check") or _find_by_prefix(results, "HTTP status")

    if interfaces and interfaces.status != ResultStatus.PASS:
        return OverallDiagnosis(
            status="problem_detected",
            summary="The computer does not appear to have a healthy local IP/interface state.",
            likely_problem_area="local_adapter_or_dhcp",
            next_step="Check whether Ethernet/Wi-Fi is connected and whether DHCP assigned an IP address.",
            metrics=metrics,
        )

    if routes and routes.status != ResultStatus.PASS:
        return OverallDiagnosis(
            status="problem_detected",
            summary="No working default gateway was found. This usually points to a routing, DHCP, or router connection problem.",
            likely_problem_area="routing_or_dhcp",
            next_step="Check router connection, DHCP settings, and whether the network assigned a default gateway.",
            metrics=metrics,
        )

    if gateway_ping and gateway_ping.status == ResultStatus.FAIL:
        return OverallDiagnosis(
            status="problem_detected",
            summary="The default gateway/router did not respond. The issue is likely on the local network or router path.",
            likely_problem_area="gateway_or_local_network",
            next_step="Check Ethernet/Wi-Fi connection, router power, and whether the router responds from another device.",
            metrics=metrics,
        )

    if internet_ping and internet_ping.status == ResultStatus.FAIL:
        return OverallDiagnosis(
            status="problem_detected",
            summary="The router/local gateway appears reachable, but public internet ping failed.",
            likely_problem_area="internet_or_isp",
            next_step="Check ISP/router WAN status or test from another device on the same network.",
            metrics=metrics,
        )

    if dns and dns.status == ResultStatus.FAIL:
        return OverallDiagnosis(
            status="problem_detected",
            summary="Internet reachability appears to work, but DNS name lookup failed.",
            likely_problem_area="dns",
            next_step="Check DNS settings or try another resolver; name lookup is likely the problem.",
            metrics=metrics,
        )

    if https and https.status == ResultStatus.FAIL:
        return OverallDiagnosis(
            status="problem_detected",
            summary="DNS appears to work, but HTTPS/web access failed.",
            likely_problem_area="web_tls_proxy_or_site",
            next_step="Check the target site, proxy/firewall settings, captive portal, or TLS path.",
            metrics=metrics,
        )

    return OverallDiagnosis(
        status="needs_review",
        summary=f"{passed} of {total} checks passed. Review warning, skipped, or failed checks for details.",
        likely_problem_area="unknown",
        next_step="Open the failed or warning result cards and review the suggested next step and command output.",
        metrics=metrics,
    )


def _find_by_name(results: list[CommandResult], name: str) -> CommandResult | None:
    return next((r for r in results if r.name == name), None)


def _find_by_prefix(results: list[CommandResult], prefix: str) -> CommandResult | None:
    return next((r for r in results if r.name.startswith(prefix)), None)


def _find_first(results: list[CommandResult], prefix: str, exclude: str = "") -> CommandResult | None:
    return next((r for r in results if r.name.startswith(prefix) and exclude not in r.name), None)
