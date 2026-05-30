# Agon — Terminal-Bench arena for Lenos evaluation.
# Use `make <target>` as the primary local interface.
.PHONY: build-image run-smoke test-solution results shell fmt lint clean help
build-image:           ## Build the benchmark Docker image
	./scripts/build-image.sh
run-smoke: build-image ## Run the smoke task through the benchmark adapter (requires host Lenos config)
	./scripts/run-smoke.sh
test-solution: build-image ## Verify smoke task reference solution + pytest (no keys needed)
	./scripts/test-solution.sh
results:               ## Show latest benchmark results
	./scripts/results.sh
shell: build-image     ## Open interactive shell in the benchmark container
	./scripts/shell.sh
fmt:                   ## Format Python and shell files
	./scripts/fmt.sh
lint:                  ## Lint Python files
	./scripts/lint.sh
clean:                 ## Remove Docker image and clear results
	./scripts/clean.sh
help:                  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
