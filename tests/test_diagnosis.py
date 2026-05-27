from net_troubleshooter.core.diagnosis import build_overall_diagnosis
from net_troubleshooter.core.models import CommandResult, ResultStatus


def result(name, status=ResultStatus.PASS, summary="ok", details=None):
    return CommandResult(
        name=name,
        command="test",
        args=[],
        status=status,
        summary=summary,
        details=details or {},
    )


def test_all_quick_check_results_pass_returns_healthy_summary():
    diagnosis = build_overall_diagnosis([
        result("Interfaces"),
        result("Routes"),
        result("Ping 192.168.0.1", details={"avg_latency_ms": 2.2}),
        result("Ping 1.1.1.1", details={"avg_latency_ms": 21.0}),
        result("DNS lookup example.com"),
        result("HTTPS check https://example.com"),
    ])

    assert diagnosis.status == "healthy"
    assert diagnosis.likely_problem_area is None
    assert "All 6 checks passed" in diagnosis.summary
    assert diagnosis.metrics["checks_passed"] == 6
    assert diagnosis.metrics["gateway_latency_ms"] == 2.2
    assert diagnosis.metrics["internet_latency_ms"] == 21.0


def test_dns_failure_after_internet_ping_points_to_dns_problem():
    diagnosis = build_overall_diagnosis([
        result("Interfaces"),
        result("Routes"),
        result("Ping 192.168.0.1"),
        result("Ping 1.1.1.1"),
        result("DNS lookup example.com", ResultStatus.FAIL, "DNS failed"),
        result("HTTPS check https://example.com", ResultStatus.SKIPPED, "skipped"),
    ])

    assert diagnosis.status == "problem_detected"
    assert diagnosis.likely_problem_area == "dns"
    assert "DNS" in diagnosis.summary
    assert "name lookup" in diagnosis.next_step.lower()


def test_gateway_failure_points_to_local_network_or_router_problem():
    diagnosis = build_overall_diagnosis([
        result("Interfaces"),
        result("Routes"),
        result("Ping 192.168.0.1", ResultStatus.FAIL, "gateway failed"),
        result("Ping 1.1.1.1", ResultStatus.FAIL, "internet failed"),
    ])

    assert diagnosis.status == "problem_detected"
    assert diagnosis.likely_problem_area == "gateway_or_local_network"
    assert "router" in diagnosis.summary.lower()


def test_no_default_gateway_points_to_routing_problem():
    diagnosis = build_overall_diagnosis([
        result("Interfaces"),
        result("Routes", ResultStatus.WARNING, "No default gateway found."),
        result("Ping default gateway", ResultStatus.SKIPPED, "skipped"),
    ])

    assert diagnosis.status == "problem_detected"
    assert diagnosis.likely_problem_area == "routing_or_dhcp"
    assert "default gateway" in diagnosis.summary.lower()


def test_http_status_failure_points_to_web_tls_proxy_or_site_problem():
    diagnosis = build_overall_diagnosis([
        result("Website input example.com"),
        result("DNS lookup example.com"),
        result("TCP port example.com:443"),
        result("TCP port example.com:80"),
        result("TLS certificate example.com"),
        result("HTTP status https://example.com", ResultStatus.FAIL, "HTTP failed"),
    ])

    assert diagnosis.status == "problem_detected"
    assert diagnosis.likely_problem_area == "web_tls_proxy_or_site"
    assert "web access failed" in diagnosis.summary
