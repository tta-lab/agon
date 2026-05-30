# Agon benchmark image — Lenos + Temenos for Terminal-Bench tasks
#
# Binary acquisition:
#   lenos   — git clone + go build (avoids replace directive issues with go install)
#   temenos — downloaded from pinned GitHub release
#
# Build args control version pinning:
#   TEMENOS_VERSION  — temenos release tag (default: latest known working)
#   LENOS_REF        — lenos git ref (tag, branch, or SHA) for cloning
#   GO_VERSION       — Go toolchain version for building lenos
#
# Provider secrets are NEVER baked into this image.
# Pass them as environment variables at runtime.
FROM ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624
# Build args for version pinning
ARG TEMENOS_VERSION=v0.9.0
ARG LENOS_REF=main
ARG GO_VERSION=1.26.2
# Additional tools: Python for runner (tmux and asciinema come from the base image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
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
# Download and install temenos (pinned release binary from GitHub)
RUN mkdir -p /tmp/temenos && \
    curl -fsSL "https://github.com/tta-lab/temenos/releases/download/${TEMENOS_VERSION}/temenos_Linux_x86_64.tar.gz" \
        -o /tmp/temenos/temenos.tar.gz && \
    tar -xzf /tmp/temenos/temenos.tar.gz -C /tmp/temenos && \
    mv /tmp/temenos/temenos /usr/local/bin/temenos && \
    chmod +x /usr/local/bin/temenos && \
    rm -rf /tmp/temenos
# Build lenos from source (go install fails due to replace directives in go.mod)
RUN git clone --depth 1 --branch "${LENOS_REF}" https://github.com/tta-lab/lenos.git /tmp/lenos-src && \
    cd /tmp/lenos-src && \
    CGO_ENABLED=0 go build -o /usr/local/bin/lenos . && \
    chmod +x /usr/local/bin/lenos && \
    rm -rf /tmp/lenos-src
# Create working directories
RUN mkdir -p /workspace /results /transcripts
# Runner adapter
COPY agon_bench/runner/runner.py /usr/local/bin/agon-runner.py
# Runner entrypoint
COPY agon_bench/runner/entrypoint.sh /usr/local/bin/agon-run
RUN chmod +x /usr/local/bin/agon-run
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/agon-run"]
