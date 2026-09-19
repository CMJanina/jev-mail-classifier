#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.10+ first: https://www.python.org/downloads/"
  exit 1
fi

echo "Setting up jev-mail-classifier in ${here}/.venv ..."
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .
chmod +x "$here/jev-mail"

echo ""
echo "Installed. From now on, run it from this directory with ./jev-mail"
echo "(e.g. ./jev-mail run --dry-run) -- no venv activation needed."
echo ""

if [ -f "$here/config.yaml" ]; then
  echo "config.yaml already exists -- skipping the setup wizard."
  echo "Run './jev-mail configure' any time to add/edit categories or credentials."
else
  echo "Launching the setup wizard (paste one API key + your IMAP login)..."
  echo ""
  exec "$here/jev-mail" configure
fi
