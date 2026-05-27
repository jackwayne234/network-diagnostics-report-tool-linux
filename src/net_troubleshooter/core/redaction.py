from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
ENX_MAC_RE = re.compile(r"\benx[0-9A-Fa-f]{12}\b")
IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
IPV6_CANDIDATE_RE = re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{1,4}\b")
AUTH_HEADER_RE = re.compile(r"(?im)^(Authorization|Cookie|Set-Cookie):\s*.*$")
URL_QUERY_RE = re.compile(r"https?://[^\s<>\"]+")


def redact_text(text: str, redact_public_ip: bool = True) -> str:
    """Redact common sensitive network report values.

    This intentionally uses conservative pattern-based redaction for v0.1.
    """
    if not text:
        return text
    redacted = AUTH_HEADER_RE.sub(lambda m: f"{m.group(1)}: [REDACTED]", text)
    redacted = MAC_RE.sub("[MAC_REDACTED]", redacted)
    redacted = ENX_MAC_RE.sub("enx[MAC_REDACTED]", redacted)
    redacted = URL_QUERY_RE.sub(_redact_url_query, redacted)
    if redact_public_ip:
        redacted = IPV4_RE.sub("[IP_REDACTED]", redacted)
        redacted = IPV6_CANDIDATE_RE.sub(_redact_ipv6_candidate, redacted)
    return redacted


def redact_value(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    return value


def _redact_ipv6_candidate(match: re.Match[str]) -> str:
    candidate = match.group(0)
    # Avoid redacting ordinary clock-like values such as 01:28:17.
    # Redact when it looks like actual IPv6: contains alphabetic hex groups
    # such as fe80/dead/beef, or enough colon groups to be unlikely as time.
    if re.search(r"[A-Fa-f]", candidate) or candidate.count(":") >= 3:
        return "[IPV6_REDACTED]"
    return candidate


def _redact_url_query(match: re.Match[str]) -> str:
    raw = match.group(0)
    parsed = urlsplit(raw)
    if parsed.query:
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "[REDACTED_QUERY]", parsed.fragment))
    return raw
