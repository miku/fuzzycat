SHELL := /bin/bash
PY_FILES := $(shell find fuzzycat -name '*.py')

.PHONY: help
help: ## Print info about all commands
	@echo "Commands:"
	@grep -E '^[/.a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[01;32m%-40s\033[0m %s\n", $$1, $$2}'


.PHONY: deps
deps: ## Install dependencies and dev dependencies from setup.py
	pip install -e .
	pip install -e .[dev]

.PHONY: fmt
fmt: ## Apply import sorting and yapf source formatting on all files
	isort --atomic fuzzycat/*
	yapf -p -i -r fuzzycat/*
	yapf -p -i -r tests

.PHONY: dist
dist: ## Create source distribution and wheel
	python setup.py sdist bdist_wheel

.PHONY: cov
cov: ## Run coverage report
	pytest --cov=fuzzycat fuzzycat/*.py tests/ # --cov-report annotate:cov_annotate --cov-report html

.PHONY: test
test: ## Run tests
	pytest -o log_cli=true -s -vvv fuzzycat/*.py tests/*.py

.PHONY: lint
lint: $(PY_FILES) ## Run pylint
	pylint fuzzycat

.PHONY: mypy
mypy: ## Run mypy checks
	mypy --strict $$(find fuzzycat -name "*py")

.PHONY: upload
upload: dist ## Upload to pypi, requires https://github.com/pypa/twine and some configuration.
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

.PHONY: clean
clean: ## Clean all artifacts
	rm -rf build
	rm -rf dist
	rm -rf fuzzycat.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf cov_annotate/
	rm -rf .mypy_cache/
	find . -name "__pycache__" -type d -exec rm -rf {} \;

