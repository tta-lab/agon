# Agon — Terminal-Bench 2.0 arena for Lenos evaluation via Harbor.
# Harbor handles container orchestration, task provisioning, and results.
# The only Agon-specific code is the Lenos agent adapter.
.PHONY: harbor-run scoreboard release-proxy-install release-proxy-start release-proxy-status release-proxy-prefetch fmt lint help venv

HARBOR ?= $(if $(wildcard .venv/bin/harbor),.venv/bin/harbor,harbor)
LIBSTDCXX_OUT ?= $(shell nix eval --raw nixpkgs#stdenv.cc.cc.lib.outPath 2>/dev/null)
LENOS_VERSION ?= latest
ORGANON_VERSION ?= latest
EINAI_VERSION ?= v0.1.0
EINAI_MODEL ?= deepseek/deepseek-v4-flash
LENOS_REASONING_EFFORT ?=
TIMEOUT_MULTIPLIER ?=
LENOS_RELEASE_BASE ?= http://host.containers.internal:8765/tta-lab/lenos/releases
ORGANON_RELEASE_BASE ?= http://host.containers.internal:8765/tta-lab/organon/releases
EINAI_RELEASE_BASE ?= http://host.containers.internal:8765/tta-lab/einai/releases
LOCAL_NO_PROXY = host.containers.internal,host.docker.internal,169.254.1.2,127.0.0.1,localhost
HARBOR_ENV = LENOS_VERSION=$(LENOS_VERSION) LENOS_RELEASE_BASE=$(LENOS_RELEASE_BASE) ORGANON_VERSION=$(ORGANON_VERSION) ORGANON_RELEASE_BASE=$(ORGANON_RELEASE_BASE) EINAI_VERSION=$(EINAI_VERSION) EINAI_RELEASE_BASE=$(EINAI_RELEASE_BASE) EINAI_MODEL=$(EINAI_MODEL) $(if $(LENOS_REASONING_EFFORT),LENOS_REASONING_EFFORT=$(LENOS_REASONING_EFFORT),) NO_PROXY=$(LOCAL_NO_PROXY),$(NO_PROXY) no_proxy=$(LOCAL_NO_PROXY),$(no_proxy) $(if $(LIBSTDCXX_OUT),LD_LIBRARY_PATH=$(LIBSTDCXX_OUT)/lib:$(LD_LIBRARY_PATH),)
AGENT_PATH = agon_bench.adapters.lenos:LenosAgent
DATASET ?= terminal-bench@2.0
MODEL ?= deepseek-v4-flash
N_CONCURRENT ?= 2
LENOS_CONFIG = $(CURDIR)/agon_bench/lenos/config.json
TASK_JOURNAL_NAME = $(if $(TASK),$(subst /,_,$(TASK)),manual)
LENOS_JOURNAL_DIR ?= $(CURDIR)/agon_bench/results/lenos-journals/$(TASK_JOURNAL_NAME)
RELEASE_PROXY_URL ?= http://127.0.0.1:8765
RELEASE_ARCH ?= x86_64
EINAI_RELEASE_GOARCH ?= amd64
LENOS_MOUNTS = {"type":"bind","source":"$(LENOS_CONFIG)","target":"/root/.config/lenos/config.json","read_only":true},{"type":"bind","source":"$(HOME)/.local/share/lenos","target":"/root/.local/share/lenos","read_only":true},{"type":"bind","source":"$(LENOS_JOURNAL_DIR)","target":"/app/.lenos/journals","read_only":false}
LENOS_MOUNTS_JSON = [$(LENOS_MOUNTS)]

harbor-run:          ## Run Lenos against TB 2.0 (TASK=org/name for one task, N_TASKS=n for subset)
	@if [ -z "$(TASK)" ] && [ -z "$(N_TASKS)" ]; then \
		echo "Usage: make harbor-run [MODEL=<model>] TASK=<org/task>"; \
		echo "   or: make harbor-run [MODEL=<model>] N_TASKS=<n> [N_CONCURRENT=<n>]"; \
		echo "Example: make harbor-run TASK=terminal-bench/headless-terminal"; \
		echo "Example: make harbor-run N_TASKS=4 N_CONCURRENT=2"; \
		exit 1; \
	fi
	mkdir -p "$(LENOS_JOURNAL_DIR)"
	$(HARBOR_ENV) $(HARBOR) run -d "$(DATASET)" \
		--agent-import-path $(AGENT_PATH) \
		-m $(MODEL) \
		-n $(N_CONCURRENT) \
		$(if $(TIMEOUT_MULTIPLIER),--timeout-multiplier $(TIMEOUT_MULTIPLIER),) \
		$(if $(TASK),-t $(TASK),) \
		$(if $(N_TASKS),--n-tasks $(N_TASKS),) \
		--mounts '$(LENOS_MOUNTS_JSON)' \
		-y

scoreboard:          ## Rebuild local TB2 scoreboard from jobs/
	python3 scripts/update_scoreboard.py

release-proxy-install: ## Install the local release cache proxy as a systemd user service
	chmod +x scripts/release_proxy.py
	mkdir -p $(HOME)/.config/systemd/user
	install -m 0644 systemd/user/agon-release-proxy.service $(HOME)/.config/systemd/user/agon-release-proxy.service
	systemctl --user daemon-reload
	systemctl --user enable --now agon-release-proxy.service

release-proxy-start:   ## Start the local release cache proxy
	systemctl --user start agon-release-proxy.service

release-proxy-status:  ## Show local release cache proxy status
	systemctl --user status agon-release-proxy.service --no-pager

release-proxy-prefetch: ## Cache Lenos plus Organon tools used by Lenos prompts
	@for i in $$(seq 1 50); do \
		if curl -fsS "$(RELEASE_PROXY_URL)/healthz" -o /dev/null 2>/dev/null; then \
			break; \
		fi; \
		sleep 0.1; \
	done
	curl -fsSL "$(RELEASE_PROXY_URL)/tta-lab/lenos/releases/$(if $(filter latest,$(LENOS_VERSION)),latest/download,download/$(LENOS_VERSION))/lenos_Linux_$(RELEASE_ARCH).tar.gz" -o /dev/null
	curl -fsSL "$(RELEASE_PROXY_URL)/tta-lab/organon/releases/latest/download/organon_Linux_$(RELEASE_ARCH).tar.gz" -o /dev/null
	curl -fsSL "$(RELEASE_PROXY_URL)/tta-lab/einai/releases/download/$(EINAI_VERSION)/ei_$(patsubst v%,%,$(EINAI_VERSION))_linux_$(EINAI_RELEASE_GOARCH).tar.gz" -o /dev/null

fmt:                 ## Format Python files
	./scripts/fmt.sh

lint:                ## Lint Python files
	./scripts/lint.sh

help:                ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
