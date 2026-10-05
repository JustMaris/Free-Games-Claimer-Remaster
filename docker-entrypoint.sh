#!/usr/bin/env bash
set -eo pipefail

BROWSER="${BROWSER_DIR:-/fgc/data/browser}"
# A relative setting is meant to be relative to the app folder, an absolute one is already final.
case "$BROWSER" in /*) ;; *) BROWSER="/fgc/$BROWSER" ;; esac
mkdir -p /fgc/data
rm -f "${BROWSER:?}"/*/SingletonLock "${BROWSER:?}"/SingletonLock

export DISPLAY="${DISPLAY:-:1}"

# ── Run as your own user (PUID / PGID) ──
# Files in a mounted data folder then belong to you on the host instead of to root (issue #58).

# cap_drop: ALL takes away what the switch needs, so it is tried on a scratch file before anything changes.
can_switch_to() {
	local probe ok=1
	probe=$(mktemp) || return 1
	chown "$1:$2" "$probe" 2>/dev/null && setpriv --reuid="$1" --regid="$2" --clear-groups true 2>/dev/null && ok=0
	rm -f "$probe"
	return "$ok"
}

run_as=()
run_uid="$(id -u)"
if [ -n "${PUID:-}" ]; then
	PGID="${PGID:-$PUID}"
	if [ "$run_uid" != "0" ]; then
		echo "PUID is set, but the container already runs as user $run_uid, so PUID is ignored."
	elif ! [[ "$PUID" =~ ^[0-9]+$ && "$PGID" =~ ^[0-9]+$ ]]; then
		echo "PUID and PGID have to be numbers, so the container keeps running as root."
	elif ! can_switch_to "$PUID" "$PGID"; then
		echo "PUID needs the CHOWN, SETUID and SETGID capabilities, which this container was started without" \
			"(cap_drop). Add them back with cap_add, until then the container keeps running as root."
	else
		getent group "$PGID" >/dev/null || groupadd -o -g "$PGID" fgc
		getent passwd "$PUID" >/dev/null || useradd -o -u "$PUID" -g "$PGID" -d /fgc/home -M -s /usr/sbin/nologin fgc
		export HOME=/fgc/home
		mkdir -p "$HOME" /fgc/data /tmp/.X11-unix
		chmod 1777 /tmp/.X11-unix
		chown "$PUID:$PGID" "$HOME"
		# A screen lock left by an earlier root start would keep this user's screen from starting.
		rm -f /tmp/.X*-lock /tmp/.tX*-lock /tmp/.X11-unix/X*
		# Only when something still belongs to someone else: browser profiles are thousands of files.
		for dir in /fgc/data "$BROWSER"; do
			if [ -e "$dir" ] && [ -n "$(find "$dir" \( ! -user "$PUID" -o ! -group "$PGID" \) -print -quit 2>/dev/null)" ]; then
				echo "Handing $dir over to $PUID:$PGID, a one-time step that can take a moment."
				chown -R "$PUID:$PGID" "$dir"
			fi
		done
		run_as=(setpriv --reuid="$PUID" --regid="$PGID" --init-groups)
		run_uid="$PUID"
	fi
fi

# A container a template starts as an unknown user gets "/" as its home, where VNC cannot write.
if ! "${run_as[@]}" test -w "${HOME:-/}"; then
	export HOME=/tmp/fgc-home
	"${run_as[@]}" mkdir -p "$HOME"
fi

# ── Say who we are ──
# On a NAS the app is often started as a user other than root, and that same user cannot
# write the browser profile or start the screen, which looks like two unrelated faults.
if "${run_as[@]}" test -w /fgc/data; then
	data_state="writable"
else
	data_state="NOT writable, the bot cannot save sessions or screenshots"
fi
# The lookup fails for a user id the image does not know, which is normal on a NAS, not a reason to stop.
user_name=$(getent passwd "$run_uid" 2>/dev/null | cut -d: -f1) || user_name=""
echo "Running as ${user_name:-unnamed}($run_uid), data folder is $data_state"

# Xvfb and x11vnc are started by the bot on demand; only the password file is prepared here.
if [ -n "${VNC_PASSWORD:-}" ]; then
	x11vnc -storepasswd "$VNC_PASSWORD" /tmp/x11vnc.pass >/dev/null
	chmod 600 /tmp/x11vnc.pass
	[ "$run_uid" = "0" ] || chown "$run_uid" /tmp/x11vnc.pass
fi

exec "${run_as[@]}" tini -g -- "$@"
