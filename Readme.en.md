# API Security Analysis Prototype

[Versió en català](README.md)
- [Test 01: X-Content-Type-Options header (in Catalan)](docs/prova-01-capçalera-nosniff.md)

Final degree project prototype: an API security analysis engine
integrated with MCP and language models.

## Objective

Enable an MCP-compatible client to request an analysis of a laboratory
API and receive a report based on security tool results.

## Current status

- Python virtual environment configured and dependencies recorded.
- Laboratory API implemented with FastAPI.
- GET /health returns the X-Content-Type-Options: nosniff header.
- GET /health/missing-header intentionally omits this header.
- Requests to both endpoints sent through the ZAP proxy.
- Alert 10021 observed on /health/missing-header: missing
  X-Content-Type-Options, with low risk and medium confidence.
- ZAP version and alerts retrieved through check_zap.py.
- Results saved as numbered JSON files with the query date.

Pending: automate request submission, passive scan completion checks,
and separation of results between runs; implement finding processing,
engine report generation, and MCP integration.

Currently, check_zap.py retrieves existing alerts from the ZAP session.
It does not start a new analysis.

## Environment used

- Windows 11.
- Python 3.14.8.
- Python dependencies recorded in requirements.txt.
- ZAP 2.17.0, running as a desktop application.
- Java 25.

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

## Manual test with ZAP

### Preparation

1. Start the API using the command in “Running the laboratory”.
2. Open the ZAP application.
3. Verify that the ZAP main proxy is listening on localhost:8080.
4. To repeat the test without mixing previous results, start a new
   ZAP session. Save the previous session first if you need to retain it.

The laboratory API listens on 127.0.0.1:8000.
ZAP listens on port 8080.

### Sending requests

In a second PowerShell terminal, run:

```powershell
curl.exe --% -i --noproxy "" --proxy http://127.0.0.1:8080 http://127.0.0.1:8000/health
```

```powershell
curl.exe --% -i --noproxy "" --proxy http://127.0.0.1:8080 http://127.0.0.1:8000/health/missing-header
```

The --% marker stops PowerShell from interpreting subsequent arguments.
In this procedure, it preserves the empty argument passed to --noproxy.

Verify that both requests appear in ZAP History and wait until
Passive Scan Queue reaches 0.

### Expected and observed results

Both endpoints return HTTP 200 and the body {"status":"ok"}.

| Endpoint | X-Content-Type-Options header | Alert 10021 |
|---|---|---|
| /health | nosniff | Not observed |
| /health/missing-header | Missing | Observed |

This test uses ZAP passive scanning of HTTP responses.
No active scan was performed in this experiment.

The alert has low risk and medium confidence. The result demonstrates
detection of a missing security configuration; it does not demonstrate
exploitation or prove that the other endpoint is free of vulnerabilities.

## Retrieving and saving alerts with Python

In ZAP, find the API key under Tools → Options → API
(Herramientas → Opciones → API in the Spanish interface).

Create a .env file in the repository root using the API key from
your local ZAP installation:

```dotenv
ZAP_API_KEY=your_local_key
```

The .env file must be excluded from Git through .gitignore.
The repository may include a .env.example without a real key:

```dotenv
ZAP_API_KEY=
```

With ZAP running and the manual test completed, run:

```powershell
.\.venv\Scripts\python.exe check_zap.py
```

The script queries the ZAP version and retrieves alerts for
the base URL http://127.0.0.1:8000.

Results are saved in:

```text
evidencies/resultats consulta-zap/
```

Each execution creates a numbered file: alertes-zap-1.JSON,
alertes-zap-2.JSON, and so on.

The field "consulta realitzada el dia" records when the data was
queried and saved, not necessarily when the alerts were generated.

These files contain the query response with metadata added by the
script. They are not complete exports of the ZAP session.

## Laboratory scope

The API listens only on the local address 127.0.0.1.
Security scans will target our own laboratory.

The /health response confirms that the application responds;
it does not demonstrate that it is secure.

## Documented tests

- [Test 01: X-Content-Type-Options header (in Catalan)](docs\prova-01-capçalera-nosniff.md)