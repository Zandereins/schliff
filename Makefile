.PHONY: test test-unit test-self test-proof test-all score lint install install-dev clean help collect-traffic

SKILL_DIR := skills/schliff

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

test-unit: ## Run the pytest unit suite (1100+ tests)
	/usr/bin/python3 -m pytest skills/schliff/tests -q

test: test-unit ## Run unit tests (pytest) then integration tests
	cd $(SKILL_DIR) && bash scripts/test-integration.sh --no-runtime-auto

test-self: ## Run self-tests (20 tests)
	cd $(SKILL_DIR) && bash scripts/test-self.sh

test-proof: ## Run proof tests (6 tests)
	cd $(SKILL_DIR) && bash tests/proof/test-proof.sh

test-all: test test-self test-proof ## Run all test suites

score: ## Score Schliff's own SKILL.md
	cd $(SKILL_DIR) && python3 scripts/score-skill.py SKILL.md

score-json: ## Score with JSON output
	cd $(SKILL_DIR) && python3 scripts/score-skill.py SKILL.md --json

lint: ## Run ruff on scripts + markdownlint on tracked docs (same as CI)
	ruff check $(SKILL_DIR)/scripts/ || echo "Install ruff: pip install ruff"
	git ls-files '*.md' | xargs npx --yes markdownlint-cli2@0.23.2 \
	  || echo "markdown lint needs node (npx); see .markdownlint-cli2.jsonc"

collect-traffic: ## Snapshot GitHub traffic (run >=1x/14d or the data expires)
	bash scripts/collect-traffic.sh

install: ## Install Schliff (copy mode)
	bash install.sh

install-dev: ## Install Schliff (symlink mode for development)
	bash install.sh --link

clean: ## Remove __pycache__ and .pyc files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
