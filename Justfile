# https://github.com/casey/just

# comment to not use powershell (for Linux, MacOS, and the BSDs)
# set shell := ["powershell.exe", "-c"]

@default: 
	just --list --unsorted

install:
    uv sync --all-extras --cache-dir .uv_cache

upgrade:
	uv sync --all-extras --cache-dir .uv_cache --upgrade

install-prod:
	uv sync --all-extras --no-dev --cache-dir .uv_cache

pre-commit:
	uv run pre-commit install

format:
	uv run ruff format

lint:
	uv run ruff check --fix

test:
	uv run pytest --verbose --color=yes tests

validate: format lint

doc:
	pydoc-markdown --render-toc -I src > src/README.md

lc:
	uv run wc -l **/*.py

build: validate doc
	rm -rf dist
	uv build

release: build
	uv publish