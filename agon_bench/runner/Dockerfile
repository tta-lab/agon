# Agon benchmark image — Lenos + Temenos for Terminal-Bench tasks
#
# Binary acquisition:
#   lenos   — built from source via go install (no GitHub release artifacts)
#   temenos — downloaded from pinned GitHub release
#
# Build args control version pinning:
#   TEMENOS_VERSION  — temenos release tag (default: latest known working)
#   LENOS_VERSION    — lenos git ref (tag or SHA) for go install
#   GO_VERSION       — Go toolchain version for building lenos
#
# Provider secrets are NEVER baked into this image.
# Pass them as environment variables at runtime.
FROM ubuntu:24.04
# Build args for version pinning
ARG TEMENOS_VERSION=v0.9.0
ARG LENOS_VERSION=v1.3.0+0.55.0
ARG GO_VERSION=1.26.2
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
# Install Go toolchain for building lenos
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" \
        -o /tmp/go.tar.gz && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"
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
# Build and install lenos from source (no GitHub release artifacts)
RUN go install "github.com/tta-lab/lenos@${LENOS_VERSION}" && \
    cp "$(go env GOPATH)/bin/lenos" /usr/local/bin/lenos && \
    chmod +x /usr/local/bin/lenos
# Create working directories
RUN mkdir -p /workspace /results /transcripts
# Runner adapter
COPY agon_bench/runner/runner.py /usr/local/bin/agon-runner.py
# Runner entrypoint
COPY agon_bench/runner/entrypoint.sh /usr/local/bin/agon-run
RUN chmod +x /usr/local/bin/agon-run
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/agon-run"]
