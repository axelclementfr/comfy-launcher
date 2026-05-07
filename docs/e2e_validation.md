# E2E Validation Checklist (manual, on vast.ai)

These tests run against a real vast.ai instance with our published image.

## Prerequisites
- Image pushed: `<dockerhub_user>/comfy-launcher:base`
- vast.ai API key
- Civitai token (for AC1, AC2)
- HuggingFace token (for AC2)
- Tailscale auth key (for AC5)

## AC1 — Single Civitai checkpoint, fresh boot

**Setup:**
- Image: `<user>/comfy-launcher:base`
- Launch Mode: SSH
- Container disk: 12 GB
- Env vars:
  - `LAUNCHER_MANIFEST_B64` = base64 of `{"version":1,"models":[{"type":"checkpoint","url":"https://civitai.com/api/download/models/2836417","filename":"test.safetensors"}]}`
  - `CIVITAI_TOKEN` = (your token)
  - `LAUNCHER_AGENT_TOKEN` = `test-token-ac1`

**Expected:**
- [ ] Boot completes < 5 min
- [ ] Logs show `--- checkpoint: test.safetensors ... OK: ~3800 MB`
- [ ] `curl -H "Authorization: Bearer test-token-ac1" http://<external_ip>:7777/models` lists `checkpoints/test.safetensors`
- [ ] `curl -H "Authorization: Bearer test-token-ac1" http://<external_ip>:8188/object_info` returns 200 with JSON

## AC2 — 5 mixed models (Civitai + HF, varied types)

[similar template, with 5 models in manifest]

## AC3 — Live install via /install endpoint

**Setup:** Reuse the AC1 instance after boot. Run:
```bash
curl -X POST http://<external_ip>:7777/install \
  -H "Authorization: Bearer test-token-ac1" \
  -H "Content-Type: application/json" \
  -d '{"models":[{"type":"lora","url":"https://huggingface.co/...","filename":"test_lora.safetensors"}]}'
# Returns: {"job_id":"..."}

# Poll:
curl http://<external_ip>:7777/jobs/<job_id> -H "Authorization: Bearer test-token-ac1"
```

**Expected:**
- [ ] Initial response 202 with job_id
- [ ] Polling shows status progresses pending → downloading → done
- [ ] After done: `GET /models` includes the new LoRA

## AC4 — Without TAILSCALE_AUTHKEY: fallback to direct port + Bearer

**Setup:** Same as AC1 but no `TAILSCALE_AUTHKEY`.

**Expected:**
- [ ] Instance boots, services up
- [ ] External IP/port from vast.ai accessible
- [ ] All endpoints reject requests without `Authorization: Bearer`

## AC5 — With TAILSCALE_AUTHKEY: VPN private access

**Setup:** Same as AC1 plus `TAILSCALE_AUTHKEY=<your tailscale auth key>`.

**Expected:**
- [ ] Instance appears in your Tailscale dashboard with hostname `comfy-launcher-XXX`
- [ ] `curl http://<tailscale_ip>:8188/...` works (with Bearer)
- [ ] `curl http://<tailscale_ip>:7777/...` works (with Bearer)

## AC6 — CI smoke test passes on a known-good ComfyUI version

Trigger workflow manually with current latest ComfyUI tag — should pass.

## AC7 — CI smoke test fails on a deliberately broken build

In a feature branch, modify Dockerfile to install a broken ComfyUI version (e.g., a non-existent tag). Push. Verify:
- [ ] CI fails at smoke test step
- [ ] No new image is pushed to `:base`
- [ ] `:base` on Docker Hub still points to the previous good build

## AC8 — Future-version manifest rejected gracefully

**Setup:** Manifest with `"version": 99`.

**Expected:**
- [ ] Boot fails with clear error in logs ("unsupported manifest version: 99")
- [ ] Sentinel `/var/run/launcher_boot_done` is NOT created
- [ ] Container stays alive (supervisord won't kill it), SSH still accessible for diagnosis
