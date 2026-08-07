# Utilities for managing zotero-mcp

.PHONY: run run-local test lint format inspector publish-test publish publish-mcp

run:
	uv run zotero-mcp

run-local:
	ZOTERO_LOCAL=true uv run zotero-mcp

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

inspector:
	npx @modelcontextprotocol/inspector uv run zotero-mcp

inspector-local:
	ZOTERO_LOCAL=true npx @modelcontextprotocol/inspector uv run zotero-mcp

publish:
	@echo "Publishing..."
	rm -rf dist/
	uv build
	uvx twine upload \
		--password="$$(op read "op://Private/PyPi/API/token")" dist/*

# Publish server metadata to the official MCP registry. Run after `publish`,
# since the registry validates ownership against the mcp-name marker in the
# README as rendered on PyPI for the version listed in server.json. Requires
# a prior `mcp-publisher login github`.
publish-mcp:
	mcp-publisher publish

# To validate the release process/changes to it
publish-test:
	@echo "Publishing to test PyPi..."
	rm -rf dist/
	uv build
	uvx twine upload \
		--repository=testpypi \
		--password="$$(op read "op://Private/Test PyPi/API/token")" dist/*
