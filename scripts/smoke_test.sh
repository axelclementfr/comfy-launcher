#!/usr/bin/env bash
# Local smoke test: build the image, run it with a tiny manifest, hit health endpoints.
# Requires: docker, ~30 GB free disk for the build cache.
set -euo pipefail

IMAGE_TAG="comfy-launcher:smoke"
CONTAINER_NAME="comfy-launcher-smoke"
TEST_TOKEN="smoke-token-$(date +%s)"

# Empty manifest just to exercise the boot path without DLs
MANIFEST_JSON='{"version":1,"models":[]}'
MANIFEST_B64="$(echo -n "$MANIFEST_JSON" | base64 -w0)"

echo "==> Building image (skip if already present, e.g. from CI)"
if ! docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    docker build -t "$IMAGE_TAG" .
else
    echo "    image $IMAGE_TAG already present, skipping build"
fi

echo "==> Cleaning any prior container"
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "==> Starting container"
docker run -d --name "$CONTAINER_NAME" \
    -p 18188:8188 \
    -p 17777:7777 \
    -e "LAUNCHER_MANIFEST_B64=$MANIFEST_B64" \
    -e "LAUNCHER_AGENT_TOKEN=$TEST_TOKEN" \
    "$IMAGE_TAG"

echo "==> Waiting for boot sentinel (max 90s)"
for i in $(seq 1 45); do
    if docker exec "$CONTAINER_NAME" test -f /var/run/launcher_boot_done; then
        echo "    boot sentinel found after ${i}x2=$((i*2))s"
        break
    fi
    sleep 2
done

echo "==> Waiting for ComfyUI to respond (max 120s)"
for i in $(seq 1 60); do
    if curl -sf -H "Authorization: Bearer $TEST_TOKEN" http://localhost:18188/object_info > /dev/null; then
        echo "    ComfyUI alive"
        break
    fi
    sleep 2
done

echo "==> Verifying agent health"
curl -sf -H "Authorization: Bearer $TEST_TOKEN" http://localhost:17777/health \
    | grep -q '"status":"ok"' \
    || { echo "FAIL: agent /health"; docker logs "$CONTAINER_NAME"; exit 1; }

echo "==> Verifying Bearer auth blocks unauthorized"
status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:17777/health)
[[ "$status" == "401" ]] || { echo "FAIL: expected 401 without Bearer, got $status"; exit 1; }

echo "==> Verifying agent /models endpoint"
curl -sf -H "Authorization: Bearer $TEST_TOKEN" http://localhost:17777/models \
    | grep -q '"models"' \
    || { echo "FAIL: agent /models"; exit 1; }

echo "==> Cleanup"
docker rm -f "$CONTAINER_NAME"

echo ""
echo "✅ SMOKE TEST PASSED"
