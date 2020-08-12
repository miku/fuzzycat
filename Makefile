SHELL := /bin/bash

.PHONY: deps
deps: ## Install dependencies from setup.py into pipenv
	# We need to use --pre, because e.g. black is considered a pre-release
	# version, https://github.com/microsoft/vscode-python/issues/5171
	pipenv install --pre '-e .[dev]'

.PHONY: help
help: ## Print info about all commands
	@echo "Commands:"
	@echo
	@grep -E '^[/.a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[01;32m%-40s\033[0m %s\n", $$1, $$2}'

data/release_export_expanded.json.gz: ## Download release export
	mkdir -p data
	wget -c https://archive.org/download/fatcat_bulk_exports_2020-08-05/release_export_expanded.json.gz -O $@

.PHONY: style
style: ## Apply import sorting and black source formatting on all files
	isort --atomic .
	yapf -p -i -r fuzzycat
	yapf -p -i -r tests

.PHONY: dist
dist: ## Create source distribution and wheel
	python setup.py sdist bdist_wheel

.PHONY: clean
clean: ## Clean all artifacts
	rm -rf build
	rm -rf dist
	rm -rf fuzzycat.egg-info/

# Upload requires https://github.com/pypa/twine and some configuration.
.PHONY: upload
upload: dist
	# https://pypi.org/account/register/
	# $ cat ~/.pypirc
	# [pypi]
	# username:abc
	# password:secret
	#
	# For internal repositories, name them in ~/.pypirc (e.g. "internal"), then
	# run: make upload TWINE_OPTS="-r internal" to upload to hosted pypi
	# repository.
	#
	# For automatic package deployments, also see: .gitlab-ci.yml.
	twine upload $(TWINE_OPTS) dist/*

