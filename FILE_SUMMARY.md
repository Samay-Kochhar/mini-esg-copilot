# File Summary (Simple Words)

This file explains what each important file does in this project.

## Root Files

### `requirements.txt`
List of Python packages needed to run the app and tests.

### `README.md`
How to run the app, test it, and understand the basic flow.

### `esg_copilot.db`
Main SQLite database file created when app runs.

## App Folder (`app/`)

### `app/main.py`
Main FastAPI app.

What it does:
- Starts app and creates DB tables on startup.
- Serves UI page at `/`.
- Exposes API endpoints:
- `POST /reports`
- `GET /reports/latest`
- `POST /reports/{id}/generate-strategy`
- `GET /reports/{id}/strategy`
- Runs generation in background.
- Handles status (`pending`, `done`, `failed`).

### `app/db.py`
Database setup.

What it does:
- Creates async SQLAlchemy engine and session.
- Provides `get_db()` for API dependency injection.
- Creates tables with `init_db()`.

### `app/models.py`
Database table models.

What it does:
- Defines `reports` table (input + normalized fields).
- Defines `strategy_generations` table (strategy text, status, metadata).
- Defines enums for units and status.

### `app/schemas.py`
API request/response schemas (Pydantic).

What it does:
- Validates input shape and value types.
- Blocks unknown fields.
- Ensures numbers are numbers.
- Enforces `scope3_value` + `scope3_unit` pair rule.
- Defines response shapes for report and strategy endpoints.

### `app/settings.py`
Runtime config loader.

What it does:
- Reads environment variables.
- Sets defaults for:
- DB URL
- model name (`stub`)
- prompt version
- generation timeout

### `app/__init__.py`
Marks `app` as a Python package.

## Services Folder (`app/services/`)

### `app/services/normalization.py`
Unit conversion and rounding helpers.

What it does:
- Converts `kg_co2e` to `t_co2e`.
- Applies fixed decimal rounding (`0.001`).

### `app/services/strategy_generator.py`
Strategy text generator (stub version).

What it does:
- Builds exactly 3 variants:
- `short`
- `neutral`
- `detailed`
- Injects reporting year and normalized Scope 1/2 numbers in text.
- Returns structured strategy payload.

### `app/services/guardrails.py`
Quality checks for generated strategy.

What it does:
- Checks numbers in `numbers_used` match stored normalized values.
- Checks unit wording consistency.
- Checks for extra number claims (basic hallucination control).
- Returns per-variant result (`pass`, `warn`, `fail`) with reasons.

### `app/services/__init__.py`
Marks `services` as a package.

## UI Folder (`app/static/`)

### `app/static/index.html`
Minimal frontend for manual testing.

What it does:
- Step-based flow for user:
- Save report
- Generate strategy
- Review results
- Shows status pills and messages.
- Auto-polls strategy until done.
- Shows result panels and raw JSON.

## Tests Folder (`tests/`)

### `tests/test_api.py`
Main integration tests.

What it checks:
- Report creation and latest retrieval.
- Validation error for wrong types.
- Strategy generation and idempotency (no duplicate generation row).

### `tests/eval_cases.json`
Small evaluation dataset with sample cases.

What it contains:
- 3 payloads with different unit patterns.

### `tests/test_esg_copilot.db`
Temporary SQLite DB used by tests.

## Scripts Folder (`scripts/`)

### `scripts/run_eval.py`
Mini evaluation harness.

What it does:
- Loads cases from `tests/eval_cases.json`.
- Creates reports and runs strategy generation.
- Waits for completion.
- Checks:
- 3 variants exist
- required numbers appear in text
- guardrails are `pass` or `warn`
- Prints pass/fail summary in console.

