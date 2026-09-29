#!/usr/bin/env bash
set -eo pipefail

BROWSER="${BROWSER_DIR:-data/browser}"
mkdir -p /fgc/data
rm -f "/fgc/$BROWSER/SingletonLock"
rm -f /tmp/.X1-lock /tmp/.tX1-lock /tmp/.X11-unix/X1

export DISPLAY=:1

Xvfb "$DISPLAY" -screen 0 "${WIDTH}x${HEIGHT}x${DEPTH}" -nolisten tcp -ac > /fgc/data/Xvfb.log 2>&1 &

for _ in $(seq 1 100); do
	if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
		break
	fi
	sleep 0.05
done

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
	echo "Xvfb failed to start on $DISPLAY" >&2
	exit 1
fi

if [ -n "${VNC_PASSWORD:-}" ]; then
	x11vnc -storepasswd "$VNC_PASSWORD" /tmp/x11vnc.pass >/dev/null
	chmod 600 /tmp/x11vnc.pass
fi

echo "Xvfb is running on $DISPLAY with resolution ${WIDTH}x${HEIGHT}"

exec tini -g -- "$@"
