# Network Troubleshooting GUI Research

## Goal
Turn common terminal workflows used by network troubleshooters into implementation-ready desktop GUI features. Linux-first, with cross-platform equivalents where useful.

## Locked project decisions
- **Platform for v0.1**: Linux only.
- **Safety scope for v0.1**: read-only diagnostics only. The app may inspect, test, parse, explain, and export results, but it must not change network settings, restart services, reconnect adapters, flush caches, edit firewall rules, or run packet captures in v0.1.
- **Command policy**: use allowlisted command adapters and argument builders; do not expose arbitrary shell execution.

## MVP feature set
1. **Dashboard / Snapshot**: interfaces, IPs, gateway, DNS servers, Wi-Fi SSID/signal, default route, public IP, basic internet reachability.
2. **Connectivity Tests**: ping, tracepath/traceroute, DNS lookup, HTTP/TLS check, TCP port check.
3. **Local Network View**: ARP/neighbor table, listening connections, active connections, route table.
4. **Guided Diagnostic Flows**: read-only “No internet” and “Website not loading” flows.
5. **Exportable Report**: one-click diagnostic bundle with redacted IP/MAC option.
6. **Privilege Model**: v0.1 should avoid privileged actions. If a read-only command lacks permission for optional details, degrade gracefully and explain what could not be read.

## Categories and GUI mapping

| Category | Linux commands | Windows/macOS equivalents | GUI feature | Privilege | Expected output | Risks/notes |
|---|---|---|---|---|---|---|
| Interface inventory | `ip addr`, `ip link`, `nmcli device`, `networkctl status` | Win: `ipconfig /all`, `Get-NetAdapter`; macOS: `ifconfig`, `networksetup -listallhardwareports` | Adapter cards with state, IPs, MAC, MTU, speed, driver | Read-only mostly | Up/down, IPv4/IPv6, MAC, MTU | MAC/IP are sensitive; redact on export |
| Link health | `ethtool eth0`, `nmcli dev show`, `iw dev`, `iw link`, `rfkill list` | Win: adapter status/WLAN report; macOS: `airport -I`, Wireless Diagnostics | Link speed/duplex, carrier, Wi-Fi RSSI/channel/security, blocked radios | Read-only; some `ethtool` details may need root | speed, duplex, signal dBm, tx bitrate | Do not expose Wi-Fi passwords |
| IP config / DHCP | `nmcli con show`, `nmcli dev show`, `resolvectl status`, DHCP logs via `journalctl` | Win: `ipconfig /renew`, `Get-DnsClientServerAddress`; macOS: `ipconfig getpacket`, `networksetup -getdnsservers` | DHCP lease panel and renew/reconnect button | Renew/reconnect may need privileges/polkit | lease times, DNS, gateway, domain | Changing profiles can disconnect user |
| Routes | `ip route`, `ip -6 route`, `ip rule`, legacy `route -n` | Win: `route print`, `Get-NetRoute`; macOS: `netstat -rn`, `route get` | Route table + default gateway checker | Read-only | destination, gateway, metric, interface | Complex policy routing; present clearly |
| Neighbors / ARP | `ip neigh`, legacy `arp -a` | Win/macOS: `arp -a` | LAN neighbor list | Read-only | IP, MAC, interface, REACHABLE/STALE | LAN enumeration is privacy-sensitive |
| Connectivity reachability | `ping`, `ping -6`, `fping` | Win/macOS: `ping` | Ping test with latency chart, loss %, jitter | Usually read-only; Linux ping uses capabilities | RTT min/avg/max, packet loss | Continuous ping can generate traffic |
| Path diagnostics | `tracepath`, `traceroute`, `mtr` | Win: `tracert`, `pathping`; macOS: `traceroute`, `mtr` | Hop-by-hop path table/map and loss view | `mtr`/ICMP modes may need caps/root | hop IP/hostname, latency/loss, MTU hints | Some networks rate-limit/block ICMP |
| DNS | `dig`, `host`, `nslookup`, `resolvectl query/statistics/flush-caches` | Win: `Resolve-DnsName`, `nslookup`, `Clear-DnsClientCache`; macOS: `dig`, `dscacheutil -flushcache` | DNS lookup tool: A/AAAA/CNAME/MX/TXT, compare resolvers, DNS cache flush | Lookups read-only; flush cache may need admin | answer, TTL, resolver, status, timing | TXT/MX outputs may be verbose; DNSSEC later |
| HTTP/HTTPS | `curl -v`, `curl -I`, `wget --spider`, `openssl s_client` | Win: `curl`, `Test-NetConnection`; macOS: `curl`, `openssl` | URL check: DNS time, connect time, TLS cert, status code, redirects | Read-only | HTTP code, headers, TLS issuer/expiry, timing | Avoid sending credentials; redact headers |
| TCP/UDP ports | `nc -vz host port`, `ss -tulpen`, `nmap` | Win: `Test-NetConnection`, `netstat -ano`; macOS: `nc`, `lsof -i` | Port check and local listener browser | Connect read-only; process names may need root | open/closed/timed out, PID/program for listeners | Port scanning can violate policy; rate-limit |
| Sockets/processes | `ss -tunap`, `lsof -i`, `fuser` | Win: `netstat -ano`, Resource Monitor; macOS: `lsof -i`, `netstat` | Active connections table with process attribution | PID/process details often need root | local/remote, state, PID, process | Exposes private endpoints |
| Packet capture | `tcpdump`, `dumpcap`, Wireshark/tshark | Win/macOS: Wireshark/dumpcap, pktmon on Win | Capture wizard with filters, ring buffer, pcap export | Requires root/cap_net_raw or dumpcap privileges | packet counts, protocols, pcap file | High privacy risk; captures secrets/PII; require consent and size limits |
| Firewall/NAT | `nft list ruleset`, `iptables -S`, `ufw status`, `firewall-cmd`, `conntrack` | Win: Windows Defender Firewall PowerShell; macOS: `pfctl`, app firewall | Firewall status viewer; later rule editor | View may need root; edits require admin | chains/rules, default policy, counters | Rule edits can cut off network/SSH; add rollback |
| Performance | `iperf3`, `speedtest-cli`, `ping` stats, `ethtool -S` | Win/macOS: `iperf3`, vendor speed test CLIs | Throughput test, latency under load, interface error counters | Usually read-only; iperf server opens port | Mbps, jitter, retransmits, drops/errors | Speed tests consume data; iperf server exposure |
| Wi-Fi scanning | `nmcli dev wifi list`, `iw dev wlan0 scan` | Win: `netsh wlan show networks`; macOS: airport scan | Nearby networks, channel congestion, signal | Scans may need privileges; can disrupt briefly | SSID, BSSID, channel, signal, security | BSSID/location privacy; hidden SSIDs |
| Logs/events | `journalctl -u NetworkManager`, `journalctl -k`, `dmesg`, `nmcli monitor` | Win: Event Viewer/netsh wlan report; macOS: Console/log stream | Timeline of link, DHCP, DNS, driver events | Reading system logs may need admin/group | timestamped errors/warnings | Logs may contain hostnames, SSIDs, tokens |
| VPN/proxy | `ip route`, `resolvectl`, `nmcli con`, `wg show`, `openvpn --status`, env proxy vars | Win/macOS VPN settings | VPN state, split tunnel routes, DNS leak checks | WireGuard details may need root | tunnel interface, peers, routes, DNS | Peer public keys and endpoints sensitive |
| Remote access | `ssh -v`, `scp`, `sftp` diagnostics | Win: OpenSSH client, PowerShell remoting | SSH connection tester/log parser | Read-only unless key handling | auth method attempted, failure cause | Never collect private keys/passphrases |

## Common workflows to model as guided flows

### 1. “No internet” flow
- Check adapter up/carrier/Wi-Fi association.
- Check IP address and DHCP lease.
- Ping default gateway.
- Ping public IP such as `1.1.1.1`.
- Resolve DNS name with configured resolver and public resolver.
- HTTP/TLS check to known endpoint.
- Output: fault domain label: local link, DHCP, gateway, DNS, routing, captive portal, remote site.

### 2. “Website not loading” flow
- DNS lookup for target host.
- TCP connect to 80/443.
- TLS certificate check.
- HTTP HEAD/GET with redirects and timing.
- Compare with another resolver/network target if configured.

### 3. “Slow network” flow
- Ping latency/loss to gateway and internet.
- Trace/MTR path loss.
- Interface speed/duplex and errors.
- Optional iperf3/speed test.
- Output: local Wi-Fi/link quality vs WAN/ISP vs remote service.

### 4. “Port/service unreachable” flow
- Local listener check with `ss`.
- Firewall status.
- Local TCP connect or remote connect if target provided.
- Route and DNS checks.
- Optional nmap in later versions.

### 5. “Wi-Fi issue” flow
- rfkill/radio state.
- Current SSID/signal/channel/bitrate.
- Scan nearby networks for congestion.
- DHCP/DNS after association.
- Logs filtered for authentication/roaming/disconnects.

## MVP vs later versions

### MVP
- Linux with NetworkManager/systemd-resolved best effort.
- Read-only dashboard: `ip`, `nmcli`, `resolvectl`, `ss`, `iw/rfkill` when present.
- Tests: ping, tracepath/traceroute fallback, DNS lookup, TCP port check, HTTP/TLS check.
- Local tables: routes, neighbors, listeners.
- Guided “No internet” and “Website not loading” flows.
- Export report as JSON + human-readable Markdown with redaction toggles.
- Explicit command preview and timeout controls.

### Version 1.1 / 1.2
- Packet capture wizard using `dumpcap`/`tcpdump` with BPF filters and pcap export.
- Wi-Fi scanner/channel congestion view.
- Log timeline for NetworkManager, kernel, DNS resolver.
- Performance tests with iperf3 and speed test integration.
- Safe fix actions: reconnect, DHCP renew, DNS flush, restart NetworkManager with warnings.

### Later / Pro features
- Cross-platform backends for Windows PowerShell/netsh and macOS networksetup/scutil/route.
- Remote agent mode for testing from another machine.
- Firewall rule diff/viewer and guarded editor with rollback.
- nmap scanning profiles with authorization prompts and rate limits.
- VPN diagnostics for WireGuard/OpenVPN/IPsec.
- Historical monitoring, scheduled checks, anomaly alerts.
- AI-assisted interpretation of collected report.

## Implementation notes
- Treat commands as backend adapters returning typed JSON, not raw terminal blobs.
- Always show: command run, start/end time, exit code, timeout, stderr, and parsed summary.
- Use allowlisted commands and argument builders; avoid arbitrary shell strings.
- Add per-command timeouts and cancellation.
- Elevate via polkit/pkexec only for specific actions; never run the whole app as root.
- Store captures/reports locally with clear delete/export controls.
- Redact by default: public IP option, MACs, SSIDs/BSSIDs, hostnames, DNS search domains, URLs with query strings, HTTP headers like Authorization/Cookie.
