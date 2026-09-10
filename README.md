# e2e-verifier

MCP server that reproduces and verifies website bug tickets in a real browser and hands back
evidence: an annotated video, a Playwright trace, screenshots, logs and a verdict per acceptance
criterion.

- **Input:** a structured `BugTicket` (steps, expected behaviour, acceptance criteria) or a plain
  `Scenario`. The MCP client (for example Claude Code) turns free-text bug reports into tickets;
  the server itself never calls an LLM.
- **Execution:** Playwright, Chromium headless by default, one isolated browser context per run.
- **Evidence:** `video.webm` with a HUD overlay (step banner, red frame around the failing
  element), `trace.zip` for the Playwright trace viewer, per-step screenshots, `console.jsonl`,
  `network.jsonl`, `chapters.vtt`, `report.md` and `result.json`.
- **Modes:** `reproduce` before a fix (a failing assertion means *reproduced*) and `verify` after
  it (all criteria met means *fixed*).

The full design is in [spec.md](spec.md).

## Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Chromium for Playwright (`uv run playwright install chromium`)
- Optional: `ffmpeg` on the path for an additional mp4 export (`E2E_FFMPEG_PATH`)

## Setup

```bash
uv sync
uv run playwright install chromium
```

## Run the server

```bash
uv run e2e-verifier                 # stdio transport (default)
E2E_TRANSPORT=http uv run e2e-verifier   # Streamable HTTP on 127.0.0.1:8765
```

Claude Code configuration (`.mcp.json` in the project that contains the website under test):

```json
{
  "mcpServers": {
    "e2e-verifier": {
      "command": "uv",
      "args": ["run", "e2e-verifier"],
      "env": {
        "E2E_ARTIFACT_DIR": "artifacts",
        "E2E_ALLOWED_HOSTS": "localhost,127.0.0.1"
      }
    }
  }
}
```

The paths are relative to the project root, which is the working directory Claude Code uses for a
project-scoped `.mcp.json`. When the server is started from another directory, add
`"--directory", "<absolute path to end_to_end_testmcp>"` after `"run"` and use an absolute
`E2E_ARTIFACT_DIR`. The HTTP alternative is `E2E_TRANSPORT=http uv run e2e-verifier` and a client
entry `{"type": "http", "url": "http://127.0.0.1:8765/mcp"}`.

## Typical session

1. `probe_target("http://127.0.0.1:5173/")` – is the site up?
2. `discover_elements(url, query="Save")` – which targets exist? Returns suggested `Target`s.
3. Build a `BugTicket` (prompt `ticket_from_report`), then `validate_ticket`.
4. `run_ticket(ticket, options={"mode": "reproduce"})` – attach `video.webm` to the ticket.
5. After the fix: `run_ticket(ticket, options={"mode": "verify"})`.

Minimal ticket:

```json
{
  "id": "WEB-142",
  "title": "Save button does nothing",
  "url": "http://127.0.0.1:5173/settings",
  "steps": [
    {"id": "s1", "action": "fill", "target": {"label": "Name"}, "value": "Anna"},
    {"id": "s2", "action": "click", "target": {"role": {"role": "button", "name": "Save"}}},
    {"id": "s3", "action": "expect_visible", "target": {"role": {"role": "status", "name": "Saved"}}},
    {"id": "s4", "action": "expect_request", "method": "POST", "url_pattern": "**/api/settings", "status": 200}
  ],
  "expected": "A toast 'Saved' appears and the settings are posted.",
  "actual": "Nothing happens.",
  "acceptance_criteria": [
    {"id": "AC1", "description": "Toast appears", "step_ids": ["s3"]},
    {"id": "AC2", "description": "Settings are posted", "step_ids": ["s4"]}
  ]
}
```

## Interactive sessions: letting an agent operate the site

An agent that does not know the site yet can drive it step by step. Every session is recorded
(video with HUD banners, trace, screenshots, logs), and every tool result comes with a screenshot
the agent can look at.

```
session_open(url)                         -> session id, first navigation result, screenshot
session_inspect(session_id, query="Save") -> ARIA snapshot + candidate targets with suggested Target JSON
session_act(session_id, step)             -> step result + screenshot; step = any action/assertion,
                                             e.g. {"id":"s1","action":"click","target":{"test_id":"save"}}
session_annotate(session_id, message, target?, tone?) -> callout/frame drawn into the video + screenshot
session_screenshot(session_id, full_page?) -> screenshot
session_close(session_id, verdict?, summary?) -> RunResult with video.webm, trace.zip, report.md ...
```

Failed assertions do not end a session; they are marked with a red frame in the video and the
agent can keep going. `get_schema(kind="step")` returns the schema of all step types. Sessions are
closed automatically after `E2E_SESSION_IDLE_TIMEOUT_S` (default 600 s); at most
`E2E_MAX_SESSIONS` (default 3) are open at once. The session id doubles as run id for
`get_artifact` and the `runs://` resources.

## Tools

| Tool | Purpose |
|---|---|
| `session_open` / `session_act` / `session_inspect` / `session_annotate` / `session_screenshot` / `session_close` / `session_list` | Interactive, recorded browser sessions (see above) |
| `get_schema` | JSON schema for `ticket`, `scenario`, `run_options`, `run_result` |
| `validate_ticket` | Semantic validation without a browser (host allowlist, criteria coverage, brittle selectors) |
| `run_ticket` / `run_scenario` | Execute in the browser, record artifacts, return `RunResult` with verdict |
| `get_run` / `list_runs` / `delete_run` | Manage stored runs |
| `get_artifact` | Fetch video, trace, report, screenshots, logs (inline up to `E2E_MAX_INLINE_ARTIFACT_MB`) |
| `probe_target` | Reachability, status, title, load time, console errors of a URL |
| `discover_elements` | ARIA snapshot plus candidate targets for a query, optional `steps_before` |
| `server_info` | Versions, configuration, run counts |

Resources: `schema://ticket`, `schema://scenario`, `schema://run-options`, `schema://run-result`,
`runs://index`, `runs://{run_id}/{result,ticket,report,video,trace,console,network,chapters,har}`,
`runs://{run_id}/screenshots/{index}`.

Prompts: `ticket_from_report`, `analyze_run`, `refine_target`.

## Configuration

All settings are environment variables with the prefix `E2E_` (a `.env` file is read too).

| Variable | Default | Meaning |
|---|---|---|
| `E2E_ARTIFACT_DIR` | `artifacts` | Root directory for runs |
| `E2E_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Hosts the browser may navigate to (`*.example.test` wildcards allowed) |
| `E2E_ALLOW_ANY_HOST` | `false` | Disable the allowlist |
| `E2E_BROWSER` | `chromium` | `chromium`, `firefox`, `webkit` |
| `E2E_HEADLESS` | `true` | Headed mode for local debugging |
| `E2E_DEFAULT_STEP_TIMEOUT_MS` | `10000` | Timeout per action/assertion |
| `E2E_DEFAULT_RUN_TIMEOUT_S` | `120` | Hard limit per run (capped by `E2E_MAX_RUN_TIMEOUT_S`, default 600) |
| `E2E_MAX_PARALLEL_RUNS` | `1` | Concurrent runs |
| `E2E_MAX_RUNS_RETAINED` | `50` | Retention by count |
| `E2E_MAX_ARTIFACT_AGE_H` | `168` | Retention by age |
| `E2E_MAX_INLINE_ARTIFACT_MB` | `8` | Larger artifacts are returned as a path |
| `E2E_FIXTURE_DIR` | unset | Root for `upload_file` paths and `storage_state_path` |
| `E2E_FFMPEG_PATH` | unset | Optional mp4 export |
| `E2E_TRANSPORT` | `stdio` | `stdio` or `http` |
| `E2E_HTTP_HOST` / `E2E_HTTP_PORT` | `127.0.0.1` / `8765` | HTTP transport bind address |
| `E2E_HUD_LANGUAGE` | `en` | `en` or `de` for fixed HUD texts |

## Artifacts

```
artifacts/runs/<run_id>/
  result.json  report.md  ticket.json  options.json
  video.webm   chapters.vtt   trace.zip
  console.jsonl  network.jsonl  [network.har]  [video.mp4]
  screenshots/001_passed.png ... 003_failed.png 003_failure_fullpage.png
```

Open a trace with:

```bash
uv run playwright show-trace artifacts/runs/<run_id>/trace.zip
```

## Development

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src tests
uv run pytest tests/unit
uv run pytest tests/integration/test_run_ticket_broken_button.py -x --timeout=120
```

Integration tests start a real Chromium against a fixture site under `tests/fixtures/site`; run them
per file. The code base follows a no-comments, no-docstrings rule that is enforced by a unit test;
tool descriptions live in decorator arguments and `Field(description=...)`.
