# Agent-to-agent test: reproducing customer bug reports with the e2e-verifier MCP server

This folder is the hand-over point between two agents:

- the **author agent** built the `e2e-verifier` MCP server (this repository) and wrote nothing
  into the tickets except the customers' own words;
- the **testing agent** receives the tickets, has never seen the site, and must find out with the
  MCP server whether the reports are reproducible, producing video, screenshots and a verdict.

The test is blind on purpose. The testing agent proves that the server is enough to operate an
unknown website, not that it can read source code.

## 1. Folder layout

```
bugreport/
  README.md                 this document
  targets.json              site under test and control build per ticket
  tickets/
    TICKET-101-coupon-no-discount.md
    TICKET-102-total-lags-behind.md
    TICKET-103-item-not-added.md
  a2a_test_output/          written by the testing agent, one folder per ticket id
    README.md
```

Every ticket file contains only the customer's message. There are no steps, no selectors, no
expected/actual sections, no severity and no hints about the cause. The file name is the ticket id
plus a short symptom slug.

## 2. Ground rules for the testing agent

1. Work only with three inputs: the ticket text, the live site in the browser, and the tools of the
   `e2e-verifier` MCP server. Do not open the `shopdesk/` folder, its README or its sources, and do
   not read `artifacts/` of runs you did not create. Either would reveal the answers.
2. Do not change the site, its data or its configuration. The site is a demo with seeded data; a
   fresh browser context starts with an empty cart.
3. One recorded session or run per experiment. Close sessions with `session_close`; the artifacts
   are written only then.
4. Every verdict must be backed by at least one assertion step that ran in the browser and by a
   control run on the working build (see section 5).
5. Write in English. Do not put anything personal into the output: no names, no e-mail addresses,
   no local paths of other people. The tickets contain none; keep it that way.

## 3. Environment

The site under test is a small web shop. The operator starts both instances before the test; the
testing agent only needs the URLs.

| Ticket | Site under test (all reported problems present) | Control build (same site without them) |
|---|---|---|
| TICKET-101-coupon-no-discount | `http://127.0.0.1:5175/` | `http://127.0.0.1:5173/` |
| TICKET-102-total-lags-behind | `http://127.0.0.1:5175/` | `http://127.0.0.1:5173/` |
| TICKET-103-item-not-added | `http://127.0.0.1:5175/` | `http://127.0.0.1:5173/` |

The same mapping is in `targets.json`. Notes:

- Append `?motion=off` to the URL to disable animations; screenshots are stable then.
- Navigation is hash based (`#/`, `#/cart`, `#/checkout`, ...); the query string survives the
  hash changes.
- The cart lives in memory only. Every `session_open` starts empty, which makes experiments
  repeatable.
- The server's host allowlist permits `127.0.0.1` and `localhost` only. Any other host is
  rejected before a browser starts.
- Check availability first: `probe_target(url="http://127.0.0.1:5175/")` must return
  `reachable: true` with an empty `page_errors` list.

## 4. Working with the server

The server offers two ways of working. Start interactively; switch to a batch ticket once the steps
are known.

### 4.1 Interactive session (recommended for unknown pages)

```
session_open(url="http://127.0.0.1:5175/?motion=off#/")
```

Returns `SessionOpened` JSON (session id, first navigation result, page title, artifacts
directory) and a screenshot as image content. The session id is also the run id of the artifacts.

```
session_inspect(session_id=..., query="add to cart")
```

Returns the ARIA snapshot of the page and candidate elements matching the query. Each candidate
carries a `suggested_target` that can be pasted into a step, for example
`{"test_id": "add-to-cart"}` or `{"role": {"role": "button", "name": "Apply", "exact": true}}`.
Prefer `role` and `test_id` targets. Scope a target with `within` and `has_text` when several
elements match: `{"test_id": "add-to-cart", "within": {"test_id": "product-card", "has_text":
"Morgenrot"}}`.

```
session_act(session_id=..., step={"id": "s1", "action": "click", "target": {"test_id": "nav-cart"}})
session_act(session_id=..., step={"id": "s2", "action": "expect_text", "target": {"test_id": "summary-total"}, "text": "149.00"})
session_act(session_id=..., step={"id": "s3", "action": "expect_count", "target": {"test_id": "cart-line"}, "count": 3})
session_act(session_id=..., step={"id": "s4", "action": "expect_request", "method": "POST", "url_pattern": "**/api/**", "timeout_ms": 3000})
```

Every call returns an `ActResult` (step status `passed`, `failed` or `error`, the error message,
which element was highlighted, new console or page errors, the number of requests since the
previous step, and a hint) plus a screenshot. Assertions that fail do not end the session; the
video shows a red frame around the element in question and the session continues. Use
`get_schema(kind="step")` for the full list of actions (`goto`, `click`, `fill`, `check`,
`select_option`, `hover`, `press`, `wait_for`, `reload`, ...) and assertions (`expect_visible`,
`expect_hidden`, `expect_text`, `expect_value`, `expect_count`, `expect_enabled`, `expect_url`,
`expect_request`, `expect_no_request`, `expect_no_console_errors`, `expect_storage`, ...).

```
session_annotate(session_id=..., message="Badge shows 2 after three clicks", target={"test_id": "cart-badge"}, tone="failure", hold_ms=2000)
session_screenshot(session_id=..., full_page=true)
```

Annotations are drawn into the video (frame around the target plus a callout with your message)
and saved as screenshots. Use them to mark the decisive observation.

```
session_close(session_id=..., verdict="reproduced", summary="Third add-to-cart click was lost; badge stayed at 2 while the toast confirmed the add.")
```

Stops the recording and writes `video.webm`, `trace.zip`, `chapters.vtt`, `report.md`,
`result.json`, `console.jsonl`, `network.jsonl` and `screenshots/` into the artifacts directory.
Without `verdict` and `summary` they are derived from the executed assertions.

### 4.2 Batch run (once the steps are known)

```
get_schema(kind="ticket")
validate_ticket(ticket={...})
run_ticket(ticket={...}, options={"mode": "reproduce"})
run_ticket(ticket={...}, options={"mode": "reproduce", "base_url_override": "http://127.0.0.1:5173"})
```

`run_ticket` executes a structured `BugTicket` (steps plus acceptance criteria) end to end and
returns a `RunResult` with a verdict per acceptance criterion. The second call runs the identical
ticket against the control build; `base_url_override` swaps only scheme, host and port.

### 4.3 Fetching artifacts

```
get_artifact(run_id=<session id or run id>, kind="video")
get_artifact(run_id=..., kind="trace")
get_artifact(run_id=..., kind="report")
get_artifact(run_id=..., kind="screenshot", index=0)
```

Files up to 8 MB are returned inline; larger ones come back as an `ArtifactLocation` with the
absolute path to copy from. The artifacts directory is also part of every `session_close` and
`run_ticket` result (`artifacts.dir`).

## 5. Method

1. Read the ticket and turn it into observable claims: which element, which number, which message.
2. Open a session on the site under test and inspect the start page before acting.
3. Record a baseline before the action that the customer describes (for example read a total
   with `expect_text`, count lines with `expect_count`).
4. Perform the customer's action step by step and assert what should have happened. Assert
   numbers and counts, not only that a message appeared; several reports describe a message that
   appears although the underlying change did not happen.
5. For intermittent reports repeat the action several times inside one session and count.
6. Annotate the decisive observation, then close the session with your verdict.
7. Run the same steps against the control build. Expected: the assertions that failed on the site
   under test pass on the control build. If they fail there too, the steps are wrong or the report
   describes normal behaviour; the verdict is then `inconclusive` or `not_reproduced` and the
   verdict file must say why.
8. Compare `requests_after_step` in `result.json` when a report claims that "nothing happens";
   an action that triggers no request is strong evidence.

## 6. Expected output

Create `a2a_test_output/<ticket-id>/` for every ticket, for example
`a2a_test_output/TICKET-101-coupon-no-discount/`, containing:

```
verdict.md
reproduce/      artifacts of the run against the site under test
control/        artifacts of the run against the control build
ticket.json     only when a structured BugTicket was executed with run_ticket
```

`verdict.md` template:

```markdown
# <ticket id> - <one-line symptom in your words>

## Verdict
reproduced | not_reproduced | inconclusive

## What the customer reported
Two or three sentences in your words.

## What I did
Numbered list of the steps, one per session_act call, with the target used.

## What I observed
The facts: values before and after, counts, messages, requests, console errors. Refer to the
screenshot files and to the video offset (chapters.vtt) of the decisive moment.

## Control run
Same steps on the control build: what passed there that failed on the site under test.

## Evidence
- reproduce/video.webm, reproduce/trace.zip, reproduce/report.md, reproduce/result.json
- control/video.webm, control/report.md
- screenshots that show the finding

## Notes
Anything that limited the test: ambiguous elements, timeouts, assumptions.
```

Copy the artifact folders from the directory named in `artifacts.dir` of the close or run result,
or fetch the files with `get_artifact`. Keep the file names produced by the server.

## 7. Definition of done

- Every ticket has a `verdict.md` with one of the three verdicts and a control run.
- Every verdict is supported by at least one assertion step and one annotation in the video.
- The output contains no personal data and no absolute paths to other people's machines.
- Sessions are closed; `session_list()` returns an empty list at the end.

## 8. Limits and troubleshooting

| Symptom | Meaning | What to do |
|---|---|---|
| `host_not_allowed` | URL outside `127.0.0.1` / `localhost` | Use the URLs from section 3. |
| `ambiguous_target` with candidates | Several elements match | Add `within`, `has_text`, `exact` or `nth`. |
| `element_not_found` / timeout | Wrong target or page not ready | `session_inspect` again; use `wait_for`. |
| `TooManySessionsError` | 3 sessions already open | `session_list`, then `session_close` the old ones. |
| Session disappeared | Idle for 10 minutes | Sessions are closed automatically; artifacts were written. |
| Step timeout | Default 10 s per step, batch run limit 120 s | Set `timeout_ms` on the step or `run_timeout_s` in options. |

## 9. MCP server configuration

Project-scoped `.mcp.json` (already present in the repository root):

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

Paths are relative to the repository root. When Claude Code is started elsewhere, add
`"--directory", "<absolute path of the repository>"` after `"run"` and use an absolute
`E2E_ARTIFACT_DIR`. The HTTP alternative is a running `E2E_TRANSPORT=http uv run e2e-verifier`
and the client entry `{"type": "http", "url": "http://127.0.0.1:8765/mcp"}`.
