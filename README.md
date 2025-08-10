# csv-mcp

This project is an MCP (Model Context Protocol) server for analyzing CSV/Excel files and plotting data interactively.

## Features
- **load_csv filename**: Load a CSV file by filename.
- **plot column_name**: Plot a selected column from the loaded trace as an interactive chart.

## Setup
- Python 3.13+ required
- Uses MCP Python SDK (https://github.com/modelcontextprotocol/create-python-server)

## Usage
- Extend this server to add more data analysis and visualization features as needed.

## Development
- The main entry point is defined in `src/csv_mcp/__init__.py`.
- To run the server, use the script defined in `pyproject.toml`.

---

For more information on MCP servers, see the [official documentation](https://modelcontextprotocol.io/llms-full.txt).
