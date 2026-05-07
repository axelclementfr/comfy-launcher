#!/usr/bin/env bash
# Start tailscaled if TAILSCALE_AUTHKEY is set; otherwise exit silently.
set -euo pipefail

if [[ -z "${TAILSCALE_AUTHKEY:-}" ]]; then
    echo "[tailscale] TAILSCALE_AUTHKEY not set, skipping VPN setup"
    exit 0
fi

# Strip defensive quotes (vast.ai env var quirk)
AUTHKEY="${TAILSCALE_AUTHKEY//\"/}"
AUTHKEY="${AUTHKEY//\'/}"

# Start daemon in background, redirect logs to file
mkdir -p /var/log/tailscale
tailscaled --state=/var/lib/tailscale/tailscaled.state \
           --tun=userspace-networking \
           >> /var/log/tailscale/tailscaled.log 2>&1 &

# Wait for daemon to be reachable (max 15 sec)
for i in {1..15}; do
    if tailscale status >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Authenticate and bring up
HOSTNAME="${TAILSCALE_HOSTNAME:-comfy-launcher-$(hostname | tr -dc 'a-z0-9')}"
tailscale up \
    --authkey="$AUTHKEY" \
    --hostname="$HOSTNAME" \
    --accept-dns=false \
    --accept-routes=false

echo "[tailscale] up as: $(tailscale ip -4)"
