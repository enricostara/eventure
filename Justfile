# https://github.com/casey/just

# comment to not use powershell (for Linux, MacOS, and the BSDs)
# set shell := ["powershell.exe", "-c"]

@default: 
	just --list --unsorted

sync:
    uv sync --all-extras --cache-dir .uv_cache

prod-sync:
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

lc:
	uv run wc -l **/*.py