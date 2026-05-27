from net_troubleshooter.core.models import CommandResult, ResultStatus
from net_troubleshooter.core.website_check import WebsiteCheckService


class FakeDiagnostics:
    def __init__(self):
        self.calls = []

    def dns_lookup(self, target="example.com"):
        self.calls.append(("dns_lookup", target))
        return CommandResult(f"DNS lookup {target}", "dig", [target], ResultStatus.PASS, "dns ok")

    def tcp_port_check(self, host, port):
        self.calls.append(("tcp_port_check", host, port))
        return CommandResult(f"TCP port {host}:{port}", "nc", [host, port], ResultStatus.PASS, "port ok")

    def tls_certificate_summary(self, host):
        self.calls.append(("tls_certificate_summary", host))
        return CommandResult(f"TLS certificate {host}", "openssl", [host], ResultStatus.PASS, "tls ok")

    def http_check(self, url="https://example.com"):
        self.calls.append(("http_check", url))
        return CommandResult(f"HTTP status {url}", "curl", [url], ResultStatus.PASS, "http ok")


class DnsFailingDiagnostics(FakeDiagnostics):
    def dns_lookup(self, target="example.com"):
        self.calls.append(("dns_lookup", target))
        return CommandResult(f"DNS lookup {target}", "dig", [target], ResultStatus.FAIL, "DNS lookup failed.")


class HttpFailingDiagnostics(FakeDiagnostics):
    def http_check(self, url="https://example.com"):
        self.calls.append(("http_check", url))
        return CommandResult(f"HTTP status {url}", "curl", [url], ResultStatus.FAIL, "HTTP check failed.")


def test_website_check_runs_ordered_read_only_checks_for_https_url():
    diagnostics = FakeDiagnostics()

    results = WebsiteCheckService(diagnostics).run("example.com/path")

    assert [result.name for result in results] == [
        "Website input example.com",
        "DNS lookup example.com",
        "TCP port example.com:443",
        "TCP port example.com:80",
        "TLS certificate example.com",
        "HTTP status https://example.com/path",
    ]
    assert diagnostics.calls == [
        ("dns_lookup", "example.com"),
        ("tcp_port_check", "example.com", "443"),
        ("tcp_port_check", "example.com", "80"),
        ("tls_certificate_summary", "example.com"),
        ("http_check", "https://example.com/path"),
    ]


def test_website_check_rejects_blank_input_without_running_network_commands():
    diagnostics = FakeDiagnostics()

    results = WebsiteCheckService(diagnostics).run("   ")

    assert len(results) == 1
    assert results[0].name == "Website input"
    assert results[0].status == ResultStatus.FAIL
    assert "Enter a website" in results[0].summary
    assert diagnostics.calls == []


def test_website_check_preserves_http_scheme_and_skips_tls_for_plain_http():
    diagnostics = FakeDiagnostics()

    results = WebsiteCheckService(diagnostics).run("http://example.com")

    assert [result.name for result in results] == [
        "Website input example.com",
        "DNS lookup example.com",
        "TCP port example.com:443",
        "TCP port example.com:80",
        "HTTP status http://example.com",
    ]
    assert ("tls_certificate_summary", "example.com") not in diagnostics.calls


def test_website_check_dns_failure_includes_likely_cause_and_safe_next_step():
    results = WebsiteCheckService(DnsFailingDiagnostics()).run("example.com")

    dns_result = next(result for result in results if result.name == "DNS lookup example.com")
    assert dns_result.status == ResultStatus.FAIL
    assert dns_result.details["likely_cause"] == "dns"
    assert "DNS name lookup appears to be failing" in dns_result.summary
    assert "Check DNS settings" in dns_result.details["next_step"]


def test_website_check_http_failure_includes_likely_cause_and_safe_next_step():
    results = WebsiteCheckService(HttpFailingDiagnostics()).run("example.com")

    http_result = next(result for result in results if result.name == "HTTP status https://example.com")
    assert http_result.status == ResultStatus.FAIL
    assert http_result.details["likely_cause"] == "web_tls_proxy_or_site"
    assert "Name lookup and TCP checks ran, but the website request failed" in http_result.summary
    assert "target site, firewall, proxy, captive portal, or TLS path" in http_result.details["next_step"]
