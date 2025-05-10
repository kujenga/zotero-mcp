# Model Context Protocol server for Zotero

[![GitHub branch status](https://img.shields.io/github/check-runs/kujenga/zotero-mcp/main)](https://github.com/kujenga/zotero-mcp/actions)
[![PyPI - Version](https://img.shields.io/pypi/v/zotero-mcp)](https://pypi.org/project/zotero-mcp/)

This project is a python server that implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) for [Zotero](https://www.zotero.org/), giving you access to your Zotero library within AI assistants. It is intended to implement a small but maximally useful set of interactions with Zotero for use with [MCP clients](https://modelcontextprotocol.io/clients).

<a href="https://glama.ai/mcp/servers/jknz38ntu4">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/jknz38ntu4/badge" alt="Zotero Server MCP server" />
</a>

## Features

This MCP server provides the following tools:

- `zotero_search_items`: Search for items in your Zotero library using a text query
- `zotero_item_metadata`: Get detailed metadata information about a specific Zotero item
- `zotero_item_fulltext`: Get the full text of a specific Zotero item (i.e. PDF contents)

These can be discovered and accessed through any MCP client or through the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector).

Each tool returns formatted text containing relevant information from your Zotero items, and AI assistants such as Claude can use them sequentially, searching for items then retrieving their metadata or text content.

## Installation

This server can either run against either a [local API offered by the Zotero desktop application](https://groups.google.com/g/zotero-dev/c/ElvHhIFAXrY/m/fA7SKKwsAgAJ)) or through the [Zotero Web API](https://www.zotero.org/support/dev/web_api/v3/start). The local API can be a bit more responsive, but requires that the Zotero app be running on the same computer with the API enabled. To enable the local API, do the following steps:

1. Open Zotero and open "Zotero Settings"
1. Under the "Advanced" tab, check the box that says "Allow other applications on this computer to communicate with Zotero".

> [!IMPORTANT]
> For access to the `/fulltext` endpoint on the local API which allows retrieving the full content of items in your library, you'll need to install a [Zotero Beta Build](https://www.zotero.org/support/beta_builds) (as of 2025-03-30). Once 7.1 is released this will no longer be the case. See https://github.com/zotero/zotero/pull/5004 for more information. If you do not want to do this, use the Web API instead.

To use the Zotero Web API, you'll need to create an API key and find your Library ID (usually your User ID) in your Zotero account settings here: <https://www.zotero.org/settings/keys>

These are the available configuration options:

- `ZOTERO_LOCAL=true`: Use the local Zotero API (default: false, see note below)
- `ZOTERO_API_KEY`: Your Zotero API key (not required for the local API)
- `ZOTERO_LIBRARY_ID`: Your Zotero library ID (your user ID for user libraries, not required for the local API)
- `ZOTERO_LIBRARY_TYPE`: The type of library (user or group, default: user)

### [`uvx`](https://docs.astral.sh/uv/getting-started/installation/) with Local Zotero API

To use this with Claude Desktop and a direct python install with [`uvx`](https://docs.astral.sh/uv/getting-started/installation/), add the following to the `mcpServers` configuration:

```json
{
  "mcpServers": {
    "zotero": {
      "command": "uvx",
      "args": ["--upgrade", "zotero-mcp"],
      "env": {
        "ZOTERO_LOCAL": "true",
        "ZOTERO_API_KEY": "",
        "ZOTERO_LIBRARY_ID": ""
      }
    }
  }
}
```

The `--upgrade` flag is optional and will pull the latest version when new ones are available. If you don't have `uvx` installed you can use `pipx run` instead, or clone this repository locally and use the instructions in [Development](#development) below.

### Docker with Zotero Web API

If you want to run this MCP server in a Docker container, you can use the following configuration, inserting your API key and library ID:

```json
{
  "mcpServers": {
    "zotero": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e", "ZOTERO_API_KEY=PLACEHOLDER",
        "-e", "ZOTERO_LIBRARY_ID=PLACEHOLDER",
        "ghcr.io/kujenga/zotero-mcp:main"
      ],
    }
  }
}
```

To update to a newer version, run `docker pull ghcr.io/kujenga/zotero-mcp:main`. It is also possible to use the docker-based installation to talk to the local Zotero API, but you'll need to modify the above command to ensure that there is network connectivity to the Zotero application's local API interface.

## Development

Information on making changes and contributing to the project.

1. Clone this repository
1. Install dependencies with [uv](https://docs.astral.sh/uv/) by running: `uv sync`
1. Create a `.env` file in the project root with the environment variables above

Start the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) for local development:

```bash
npx @modelcontextprotocol/inspector uv run zotero-mcp
```

To test the local repository against Claude Desktop, run `echo $PWD/.venv/bin/zotero-mcp` in your shell within this directory, then set the following within your Claude Desktop configuration
```json
{
  "mcpServers": {
    "zotero": {
      "command": "/path/to/zotero-mcp/.venv/bin/zotero-mcp"
      "env": {
        // Whatever configuration is desired.
      }
    }
  }
}
```

### Running Tests

To run the test suite:

```bash
uv run pytest
```

### Docker Development

Build the container image with this command:

```sh
docker build . -t zotero-mcp:local
```

To test the container with the MCP inspector, run the following command:

```sh
npx @modelcontextprotocol/inspector \
    -e ZOTERO_API_KEY=$ZOTERO_API_KEY \
    -e ZOTERO_LIBRARY_ID=$ZOTERO_LIBRARY_ID \
    docker run --rm -i \
        --env ZOTERO_API_KEY \
        --env ZOTERO_LIBRARY_ID \
        zotero-mcp:local
```

## Relevant Documentation

- https://modelcontextprotocol.io/tutorials/building-mcp-with-llms
- https://github.com/modelcontextprotocol/python-sdk
- https://pyzotero.readthedocs.io/en/latest/
- https://www.zotero.org/support/dev/web_api/v3/start
- https://modelcontextprotocol.io/llms-full.txt can be utilized by LLMs
