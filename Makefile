SHELL := /bin/bash

.PHONY: deps
deps: ## Install dependencies from setup.py into pipenv
	pipenv install '-e .'

.PHONY: help
help: ## Print info about all commands
	@echo "Commands:"
	@echo
	@grep -E '^[/.a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[01;32m%-40s\033[0m %s\n", $$1, $$2}'

data/release_export_expanded.json.gz: ## Download release export
	mkdir -p data
	wget -c https://archive.org/download/fatcat_bulk_exports_2020-08-05/release_export_expanded.json.gz -O $@

.PHONY: black
black: ## Format all Python files
	find . -name "*.py" -exec black {} \;

.PHONY: dist
dist: ## Create source distribution
	python setup.py sdist

.PHONY: clean
clean: ## Clean all artifacts
	rm -rf dist
	rm -rf fuzzycat.egg-info/

