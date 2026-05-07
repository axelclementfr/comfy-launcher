# syntax=docker/dockerfile:1.7
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps NOT auto-injected by vast.ai (those are sshd, git, wget, curl, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip \
    supervisor \
    ca-certificates \
    debian-keyring debian-archive-keyring apt-transport-https gnupg curl \
    iproute2 iputils-ping iptables \
    && rm -rf /var/lib/apt/lists/*

# Caddy (official repo)
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y --no-install-recommends caddy \
    && rm -rf /var/lib/apt/lists/*

# Tailscale (official repo)
RUN curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null \
    && curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list \
    && apt-get update && apt-get install -y --no-install-recommends tailscale \
    && rm -rf /var/lib/apt/lists/*

# Python venv with our agent + boot deps
ENV VIRTUAL_ENV=/opt/launcher-venv
RUN python3.11 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# ComfyUI clone — version pinned at build time, bumped via CI
ARG COMFYUI_REF=master
RUN git clone --depth 1 --branch ${COMFYUI_REF} https://github.com/Comfy-Org/ComfyUI /workspace/ComfyUI
RUN pip install --upgrade pip && pip install -r /workspace/ComfyUI/requirements.txt

# ComfyUI-Manager (lets the user install other custom nodes via UI)
RUN git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager /workspace/ComfyUI/custom_nodes/ComfyUI-Manager

# Pre-create models dirs (empty)
RUN mkdir -p \
    /workspace/ComfyUI/models/checkpoints \
    /workspace/ComfyUI/models/loras \
    /workspace/ComfyUI/models/vae \
    /workspace/ComfyUI/models/controlnet \
    /workspace/ComfyUI/models/upscale_models \
    /workspace/ComfyUI/models/embeddings \
    /workspace/ComfyUI/models/clip \
    /workspace/ComfyUI/models/unet

# Our launcher code
COPY launcher /opt/launcher/launcher
COPY scripts /opt/launcher/scripts
COPY pyproject.toml /opt/launcher/pyproject.toml
RUN pip install fastapi uvicorn[standard] pydantic
RUN pip install -e /opt/launcher

# supervisord + Caddy configs
COPY supervisord/supervisord.conf /etc/supervisor/conf.d/launcher.conf
COPY Caddyfile /etc/caddy/Caddyfile

# Logs + state dirs
RUN mkdir -p /var/log/launcher /var/log/tailscale /var/lib/tailscale /var/run \
    && chmod 1777 /var/run

# Expose: 8188 ComfyUI (via Caddy), 7777 Agent (via Caddy)
EXPOSE 8188 7777

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/launcher.conf"]
