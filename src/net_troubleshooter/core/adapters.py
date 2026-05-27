from __future__ import annotations

import re
from urllib.parse import urlparse

from .models import CommandResult, ResultStatus
from .runner import CommandRunner


class Diagnostics:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self.runner = runner or CommandRunner()

    def interfaces(self) -> CommandResult:
        result = self.runner.run("Interfaces", "ip", ["addr"], timeout=5, success_summary="Interface information loaded.")
        if result.status == ResultStatus.PASS:
            has_ip = bool(re.search(r"inet\s+\d+\.\d+\.\d+\.\d+", result.stdout))
            result.summary = "At least one IPv4 address found." if has_ip else "No IPv4 address found in interface output."
            result.status = ResultStatus.PASS if has_ip else ResultStatus.WARNING
            result.details["has_ipv4"] = has_ip
        return result

    def routes(self) -> CommandResult:
        result = self.runner.run("Routes", "ip", ["route"], timeout=5, success_summary="Route table loaded.")
        if result.status == ResultStatus.PASS:
            gateway = self.default_gateway_from_output(result.stdout)
            result.details["default_gateway"] = gateway
            if gateway:
                result.summary = f"Default gateway found: {gateway}."
            else:
                result.status = ResultStatus.WARNING
                result.summary = "No default gateway found."
        return result

    @staticmethod
    def default_gateway_from_output(output: str) -> str | None:
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0] == "default" and parts[1] == "via":
                return parts[2]
        return None

    def dns_status(self) -> CommandResult:
        return self.runner.run("DNS status", "resolvectl", ["status"], timeout=5, success_summary="DNS resolver status loaded.")

    def ping(self, target: str, count: int = 4) -> CommandResult:
        target = target.strip()
        result = self.runner.run(
            f"Ping {target}",
            "ping",
            ["-c", str(count), "-W", "2", target],
            timeout=max(6, count * 3),
            success_summary=f"{target} is reachable.",
            failure_summary=f"{target} did not respond to ping.",
        )
        if result.status == ResultStatus.PASS:
            loss = self._packet_loss(result.stdout)
            avg = self._avg_latency(result.stdout)
            if loss is not None:
                result.details["packet_loss_percent"] = loss
            if avg is not None:
                result.details["avg_latency_ms"] = avg
                result.summary = f"{target} is reachable. Average latency: {avg} ms."
        return result

    def dns_lookup(self, target: str = "example.com") -> CommandResult:
        target = target.strip() or "example.com"
        result = self.runner.run(
            f"DNS lookup {target}",
            "dig",
            ["+short", target],
            timeout=6,
            success_summary=f"DNS lookup for {target} completed.",
            failure_summary=f"DNS lookup for {target} failed.",
        )
        if result.status == ResultStatus.PASS:
            answers = [line for line in result.stdout.splitlines() if line.strip()]
            result.details["answers"] = answers
            if answers:
                result.summary = f"DNS resolved {target}: {', '.join(answers[:3])}."
            else:
                result.status = ResultStatus.WARNING
                result.summary = f"DNS command ran, but no answers were returned for {target}."
        return result

    def http_check(self, url: str = "https://example.com") -> CommandResult:
        url = self._normalize_url(url)
        result = self.runner.run(
            f"HTTP status {url}",
            "curl",
            ["-I", "--max-time", "8", "--location", url],
            timeout=10,
            success_summary=f"HTTP/HTTPS check for {url} completed.",
            failure_summary=f"HTTP/HTTPS check for {url} failed.",
        )
        if result.status == ResultStatus.PASS:
            status_line = next((line for line in result.stdout.splitlines() if line.startswith("HTTP/")), "")
            if status_line:
                result.details["status_line"] = status_line
                result.summary = f"Website responded: {status_line}."
        return result

    def tls_certificate_summary(self, host: str) -> CommandResult:
        host = host.strip()
        result = self.runner.run(
            f"TLS certificate {host}",
            "openssl",
            ["s_client", "-connect", f"{host}:443", "-servername", host, "-brief"],
            timeout=8,
            success_summary=f"TLS certificate summary for {host} loaded.",
            failure_summary=f"TLS certificate check for {host} failed.",
        )
        output = "\n".join(part for part in [result.stdout, result.stderr] if part)
        if output:
            protocol = re.search(r"Protocol version:\s*(.+)", output)
            cipher = re.search(r"Ciphersuite:\s*(.+)", output)
            verification = re.search(r"Verification:\s*(.+)", output)
            if protocol:
                result.details["protocol"] = protocol.group(1).strip()
            if cipher:
                result.details["cipher"] = cipher.group(1).strip()
            if verification:
                result.details["verification"] = verification.group(1).strip()
                if result.status == ResultStatus.PASS:
                    result.summary = f"TLS certificate check completed. Verification: {verification.group(1).strip()}."
        return result

    def trace_route(self, target: str) -> CommandResult:
        target = target.strip()
        return self.runner.run(f"Trace route {target}", "tracepath", [target], timeout=15, success_summary=f"Trace route to {target} completed.")

    def tcp_port_check(self, host: str, port: str) -> CommandResult:
        host = host.strip()
        port = port.strip()
        return self.runner.run(f"TCP port {host}:{port}", "nc", ["-vz", "-w", "5", host, port], timeout=7, success_summary=f"TCP port {host}:{port} is reachable.", failure_summary=f"TCP port {host}:{port} is not reachable.")

    def neighbors(self) -> CommandResult:
        return self.runner.run("Neighbors / ARP", "ip", ["neigh"], timeout=5, success_summary="Neighbor/ARP table loaded.")

    def listening_ports(self) -> CommandResult:
        return self.runner.run("Listening ports", "ss", ["-tuln"], timeout=5, success_summary="Listening ports loaded.")

    def active_connections(self) -> CommandResult:
        return self.runner.run("Active connections", "ss", ["-tun"], timeout=5, success_summary="Active connections loaded.")

    @staticmethod
    def _packet_loss(output: str) -> float | None:
        match = re.search(r"(\d+(?:\.\d+)?)% packet loss", output)
        return float(match.group(1)) if match else None

    @staticmethod
    def _avg_latency(output: str) -> float | None:
        match = re.search(r"=\s*[\d.]+/([\d.]+)/", output)
        return float(match.group(1)) if match else None

    @staticmethod
    def _normalize_url(url: str) -> str:
        url = url.strip() or "https://example.com"
        parsed = urlparse(url)
        if not parsed.scheme:
            return f"https://{url}"
        return url
