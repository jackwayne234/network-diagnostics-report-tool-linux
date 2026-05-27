# Network Diagnostics Report Tool for Linux

Read-only Linux desktop GUI that collects network diagnostic evidence and exports clear Markdown/JSON reports.

## What it does

- Runs a Quick Check for common network diagnostics
- Includes guided checks for “no internet” and “website not loading” workflows
- Provides manual Ping, DNS, Trace route, Website/HTTPS, and TCP port checks
- Shows local network views for routes, neighbors/ARP, listening ports, and active connections
- Exports Markdown and JSON reports only when the user chooses to export
- Redacts sensitive details by default in reports

## What it does not do

- Does not change network settings
- Does not require AI
- Does not upload reports anywhere
- Does not run packet capture in v0.1

## Platform

Linux. Python 3.10+ recommended.

## Run from source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
network-diagnostics-report-tool
```

Developer fallback:

```bash
python3 -m net_troubleshooter
```

## Test

```bash
source .venv/bin/activate
pytest -q
```

Verified locally before public prep: **36 tests passed**.

## Privacy / safety

This app is read-only. It collects diagnostic evidence locally and exports reports only when the user explicitly chooses to save them. Reports are designed to redact sensitive details by default.

## First-time prerequisite setup

If the app does not open, run:

```bash
./Setup_Prerequisites.sh
```

The setup script checks for Python and the app's Python dependencies. If common Linux system packages are missing, it asks before trying to install them.

Supported automatic system package managers:

- apt / apt-get
- dnf
- pacman
- zypper

If your distro uses a different package manager, install Python 3, venv/pip, and the app dependencies manually.

## Support development

These apps are free/pay-what-you-want so people can actually use them.

If this app helped you, a small tip helps me keep building and improving them.

- Cash App: $jaydubgtfo

## License

No open-source license has been selected yet. Unless a license is added later, all rights are reserved by the author.
