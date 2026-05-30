# Agon benchmark image — Lenos + Temenos for Terminal-Bench tasks
#
# Binary acquisition modes:
#   1. Pinned release download (default) — downloads from GitHub releases
#   2. Local mount — mount a local binary at /usr/local/bin/lenos to override
#
# Build args control version pinning:
#   TEMENOS_VERSION  — temenos release tag (default: latest known working)
#   LENOS_VERSION    — lenos release tag (default: latest known working)
#
# Provider secrets are NEVER baked into this image.
# Pass them as environment variables at runtime.
FROM ubuntu:24.04
# Build args for version pinning
ARG TEMENOS_VERSION=v0.9.0
ARG LENOS_VERSION=v1.3.0
# Base tools: tmux/asciinema (required by Terminal-Bench), Python for runner
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
    asciinema \
    && rm -rf /var/lib/apt/lists/*
# Install Python deps for the runner
COPY agon_bench/runner/requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages -r /tmp/requirements.txt && rm /tmp/requirements.txt
# Download and install temenos (pinned release binary)
RUN mkdir -p /tmp/temenos && \
    curl -fsSL "https://github.com/tta-lab/temenos/releases/download/${TEMENOS_VERSION}/temenos_Linux_x86_64.tar.gz" \
        -o /tmp/temenos/temenos.tar.gz && \
    tar -xzf /tmp/temenos/temenos.tar.gz -C /tmp/temenos && \
    mv /tmp/temenos/temenos /usr/local/bin/temenos && \
    chmod +x /usr/local/bin/temenos && \
    rm -rf /tmp/temenos
# Download and install lenos (pinned release binary) — can be overridden via volume mount
RUN mkdir -p /tmp/lenos && \
    curl -fsSL "https://github.com/tta-lab/lenos/releases/download/${LENOS_VERSION}/lenos_Linux_x86_64.tar.gz" \
        -o /tmp/lenos/lenos.tar.gz && \
    tar -xzf /tmp/lenos/lenos.tar.gz -C /tmp/lenos && \
    mv /tmp/lenos/lenos /usr/local/bin/lenos && \
    chmod +x /usr/local/bin/lenos && \
    rm -rf /tmp/lenos
# Create working directories
RUN mkdir -p /workspace /results /transcripts
# Runner entrypoint
COPY agon_bench/runner/entrypoint.sh /usr/local/bin/agon-run
RUN chmod +x /usr/local/bin/agon-run
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/agon-run"]
