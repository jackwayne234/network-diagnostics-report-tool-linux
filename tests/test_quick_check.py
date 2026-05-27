from net_troubleshooter.core.models import CommandResult, ResultStatus
from net_troubleshooter.core.quick_check import QuickCheckService


class FakeDiagnostics:
    def interfaces(self):
        return CommandResult("Interfaces", "ip", ["addr"], ResultStatus.PASS, "ok")
    def routes(self):
        return CommandResult("Routes", "ip", ["route"], ResultStatus.PASS, "ok", details={"default_gateway": "192.168.1.1"})
    def ping(self, target, count=4):
        return CommandResult(f"Ping {target}", "ping", [target], ResultStatus.PASS, "ok")
    def dns_lookup(self, target="example.com"):
        return CommandResult("DNS", "dig", [target], ResultStatus.PASS, "ok")
    def http_check(self, url="https://example.com"):
        return CommandResult("HTTP", "curl", [url], ResultStatus.PASS, "ok")


def test_quick_check_runs_balanced_sequence():
    results = QuickCheckService(FakeDiagnostics()).run()
    assert [r.name for r in results] == ["Interfaces", "Routes", "Ping 192.168.1.1", "Ping 1.1.1.1", "DNS", "HTTP"]
