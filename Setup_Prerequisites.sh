#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Network Diagnostics Report Tool"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$APP_DIR/setup-prerequisites.log"
exec > >(tee -a "$LOG_FILE") 2>&1

say() { printf '%s\n' "$*"; }

ask_yes_no() {
  local question="$1"
  if command -v zenity >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    zenity --question --title="$APP_NAME setup" --text="$question" && return 0 || return 1
  fi
  printf '%s [y/N]: ' "$question"
  read -r ans || return 1
  case "$ans" in y|Y|yes|YES) return 0;; *) return 1;; esac
}

need_cmd() { ! command -v "$1" >/dev/null 2>&1; }

install_system_packages() {
  local packages=("$@")
  if [ "${#packages[@]}" -eq 0 ]; then return 0; fi
  say "Need system packages: ${packages[*]}"
  if ! ask_yes_no "Install missing system packages for $APP_NAME?"; then
    say "User declined install."
    return 1
  fi
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y "${packages[@]}"
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y "${packages[@]}"
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --needed --noconfirm "${packages[@]}"
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y "${packages[@]}"
  else
    say "Unsupported package manager. Please install manually: ${packages[*]}"
    return 1
  fi
}

missing=()
if need_cmd python3; then missing+=(python3); fi
if ! python3 -m venv --help >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then missing+=(python3-venv python3-pip); else missing+=(python3-pip); fi
fi
if need_cmd sudo; then
  say "sudo is missing. Please install Python 3, venv, and pip manually."
  exit 1
fi
install_system_packages "${missing[@]}" || exit 1

if [ ! -d "$APP_DIR/.venv" ]; then
  say "Creating private Python environment for $APP_NAME..."
  python3 -m venv "$APP_DIR/.venv"
fi
VENV_PYTHON="$APP_DIR/.venv/bin/python"
say "Installing/updating app dependencies in private environment..."
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -e "$APP_DIR"

say "Setup complete for $APP_NAME."
if command -v notify-send >/dev/null 2>&1; then
  notify-send "$APP_NAME setup" "Setup complete." 2>/dev/null || true
fi
