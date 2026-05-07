# comfy-launcher

Docker image for renting [vast.ai](https://vast.ai) GPU instances with **on-demand ComfyUI model loading via a JSON manifest**. Pass a list of Civitai/HuggingFace models as a single env var, the container boots ComfyUI with exactly that set — no pre-baked models, no bandwidth wasted on stuff you don't need.

## Tags

- `comfy-launcher:base` — rolling tag, always the latest verified-good ComfyUI
- `comfy-launcher:base-v<X.Y.Z>` — immutable, pinned to a specific ComfyUI version

## Quickstart

Rent a vast.ai instance with this Docker image and a few env vars:

| Env var | Required | Purpose |
|---|---|---|
| `LAUNCHER_MANIFEST_B64` | yes | base64 of the JSON manifest (see below) |
| `LAUNCHER_AGENT_TOKEN` | yes | Bearer token for API auth |
| `CIVITAI_TOKEN` | optional | for Civitai downloads |
| `HF_TOKEN` | optional | for gated HuggingFace models |
| `TAILSCALE_AUTHKEY` | optional but recommended | joins the instance to your tailnet (private VPN access) |

### Manifest format

```json
{
  "version": 1,
  "models": [
    {"type": "checkpoint", "url": "https://civitai.com/api/download/models/2836417", "filename": "myModel.safetensors"},
    {"type": "lora",       "url": "https://civitai.com/api/download/models/1246364", "filename": "myLora.safetensors"}
  ]
}
```

Supported types: `checkpoint`, `lora`, `vae`, `controlnet`, `upscaler`, `embedding`, `clip`, `unet`. Files land under `/workspace/ComfyUI/models/<type>/`.

Encode it once:
```bash
echo -n '{"version":1,"models":[...]}' | base64 -w0
```

Paste the result in the `LAUNCHER_MANIFEST_B64` env var when creating the instance.

## What the container exposes

| Port | Service | Notes |
|---|---|---|
| `8188` | ComfyUI HTTP + WebSocket | gated by Bearer token via Caddy |
| `7777` | Live install agent (FastAPI) | `POST /install`, `GET /jobs/{id}`, `GET /models`, `DELETE /models`, `GET /health` |

Both ports are behind a Caddy reverse proxy that requires `Authorization: Bearer <LAUNCHER_AGENT_TOKEN>`. Combined with Tailscale (when configured), the instance is invisible to the public internet and only reachable from your devices.

## Live install while running

The agent on `:7777` accepts new models without restarting the instance:

```bash
curl -X POST http://<instance>:7777/install \
  -H "Authorization: Bearer $LAUNCHER_AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"models":[{"type":"lora","url":"https://huggingface.co/.../file.safetensors","filename":"new.safetensors"}]}'
# → {"job_id":"..."}

curl http://<instance>:7777/jobs/<job_id> \
  -H "Authorization: Bearer $LAUNCHER_AGENT_TOKEN"
# → {"status":"downloading","progress_pct":42, ...}
```

Models are placed in the right directory automatically. ComfyUI sees them on its next scan.

## License

MIT
