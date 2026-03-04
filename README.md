# Mini AI ESG Copilot Pipeline

This is a simple backend prototype for:
- saving ESG report input,
- normalizing emission units,
- generating 3 strategy variants,
- running guardrails,
- and returning results by API.

It also has a small demo UI to test the flow quickly.

## 1) Simple flow (what happens)
1. Save report input (`POST /reports`)
2. System converts units to `tCO2e` and stores both raw + normalized values
3. Generate strategy (`POST /reports/{id}/generate-strategy`)
4. System creates exactly 3 variants: `short`, `neutral`, `detailed`
5. Guardrails check number consistency and unit consistency
6. Fetch result (`GET /reports/{id}/strategy`)

## 2) Run the app
```bash
cd /Users/samaykochhar/Desktop/COBACK_prep/mini-esg-copilot-pipeline
/opt/anaconda3/envs/coback_prep/bin/python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- UI: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## 3) How to test quickly in UI
1. Open UI.
2. Fill report fields.
3. Click `Save Report`.
4. Click `Generate Strategy` (or `Run Full Flow`).
5. Wait for status `done`.
6. Check:
- 3 variants appear,
- numbers are shown in results,
- guardrail summary is shown.

## 4) API list
- `POST /reports`
- `GET /reports/latest`
- `POST /reports/{id}/generate-strategy`
- `GET /reports/{id}/strategy`

## 5) Run checks
Run tests:
```bash
cd /Users/samaykochhar/Desktop/COBACK_prep/mini-esg-copilot-pipeline
/opt/anaconda3/envs/coback_prep/bin/python -m pytest -q
```

Run mini eval harness:
```bash
cd /Users/samaykochhar/Desktop/COBACK_prep/mini-esg-copilot-pipeline
/opt/anaconda3/envs/coback_prep/bin/python scripts/run_eval.py
```

## 6) AI usage
- Current generation is a deterministic `stub` (no external LLM call).
- `model_name` is stored as `"stub"` in metadata.
- Later, you can swap in an LLM while keeping the same output schema and guardrails.

## 7) File-by-file explanation
For simple explanation of each file, see:
- `FILE_SUMMARY.md`
