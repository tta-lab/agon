# Agon — Terminal-Bench 2.0 arena for Lenos evaluation via Harbor.
# Harbor handles container orchestration, task provisioning, and results.
# The only Agon-specific code is the Lenos agent adapter.
.PHONY: harbor-run fmt lint help venv

HARBOR ?= .venv/bin/harbor
AGENT_PATH = agon_bench.adapters.lenos:LenosAgent
DATASET ?= terminal-bench-2.0==head
LENOS_CONFIG = $(CURDIR)/agon_bench/lenos/config.json

harbor-run:          ## Run Lenos against a TB 2.0 task (usage: make harbor-run MODEL=m TASK=org/name)
	@if [ -z "$(MODEL)" ] || [ -z "$(TASK)" ]; then \
		echo "Usage: make harbor-run MODEL=<model> TASK=<org/task>"; \
		echo "Example: make harbor-run MODEL=deepseek-v4-pro TASK=terminal-bench/hello-world"; \
		exit 1; \
	fi
	$(HARBOR) run -d "$(DATASET)" \
		--agent-import-path $(AGENT_PATH) \
		-m $(MODEL) \
		-t $(TASK) \
		--mounts '[{"type":"bind","source":"$(LENOS_CONFIG)","target":"/root/.config/lenos/config.json","read_only":true},{"type":"bind","source":"$(HOME)/.local/share/lenos","target":"/root/.local/share/lenos","read_only":true}]' \
		-y

fmt:                 ## Format Python files
	./scripts/fmt.sh

lint:                ## Lint Python files
	./scripts/lint.sh

help:                ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
