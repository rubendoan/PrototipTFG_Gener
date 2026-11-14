# API Security Analysis Prototype

[Versió en català](README.md)

Final degree project prototype: an API security analysis engine
integrated with MCP and language models.

## Objective

Enable an MCP-compatible client to request an analysis of a laboratory
API and receive a report based on security tool results.

## Current status

- Python virtual environment configured.
- Minimal API implemented with FastAPI.
- GET /health endpoint manually checked.

Pending: an insecure test case, ZAP analysis, automation,
finding processing, report generation, and MCP integration.

## Environment used

- Windows 11.
- Python 3.14.8.
- Python dependencies recorded in requirements.txt.

The current instructions target PowerShell on Windows.
Compatibility with other operating systems has not been verified.

## Installation

From the repository root directory, create the virtual environment:

```powershell
py -3.14 -m venv .venv
```

Install the dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The .venv directory is not included in Git.
Each person must create their own environment.

## Running the laboratory

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Keep the server running while using the API.
Press Ctrl + C to stop it.

## Manual check

Open http://127.0.0.1:8000/health in a browser.

Expected response:

```json
{"status":"ok"}
```

Interactive documentation: http://127.0.0.1:8000/docs

## Laboratory scope

The API listens only on the local address 127.0.0.1.
Security scans will target our own laboratory.

The /health response confirms that the application responds;
it does not demonstrate that it is secure.