#!/usr/bin/env bash
set -eo pipefail

BROWSER="${BROWSER_DIR:-data/browser}"
mkdir -p /fgc/data
rm -f "/fgc/$BROWSER/SingletonLock"

export DISPLAY=:1

if [ -n "${VNC_PASSWORD:-}" ]; then
	x11vnc -storepasswd "$VNC_PASSWORD" /tmp/x11vnc.pass >/dev/null
	chmod 600 /tmp/x11vnc.pass
fi

exec tini -g -- "$@"
