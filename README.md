# Model Context Protocol server for Zotero

This project is a python-based server that implements the Model Context Protocol
(MCP) for Zotero.

## Relevant Documentation
## Setup

1. Create a `.env` file in the project root with your Zotero credentials:

```
ZOTERO_LIBRARY_ID=your_library_id
ZOTERO_LIBRARY_TYPE=user  # or "group"
ZOTERO_API_KEY=your_api_key
```

You can find your library ID and create an API key in your Zotero account settings: https://www.zotero.org/settings/keys

## Features

This MCP server provides the following tools:
### Tools

- `search_items`: Search for items in your Zotero library using a text query
### Resources

The server exposes these resource templates:

- `zotero://items/{item_key}/metadata`
  - Description: Get detailed information about a specific Zotero item
  - Parameter: `item_key` - The unique Zotero item identifier
  - Example: `zotero://items/ABC123XYZ/metadata`
- `zotero://items/{item_key}/fulltext`
  - Description: Get the full text of a specific Zotero item
  - Parameter: `item_key` - The unique Zotero item identifier
  - Example: `zotero://items/ABC123XYZ/fulltext`

These resources can be discovered and accessed through the MCP Inspector or any other MCP client.

Each resource returns formatted text containing metadata about the Zotero items.

## Usage

Start the server for local development with the MCP Inspector:

```bash
uv run mcp dev server.py
```

You can then use these tools through any MCP client, such as Claude Desktop or the MCP Inspector.

To install in Claude Desktop:

```bash
uv run mcp install -e . server.py
```

- https://modelcontextprotocol.io/tutorials/building-mcp-with-llms
- https://github.com/modelcontextprotocol/python-sdk
- https://pyzotero.readthedocs.io/en/latest/
