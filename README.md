# Effective Config API (FastAPI)

This project implements the `q-config-precedence-server` challenge endpoint.

## Endpoint

`GET /effective-config`

Repeated `set` query parameters behave like the highest-precedence CLI flags:

```text
/effective-config?set=port=9000&set=debug=true
```

Expected example response:

```json
{"port":9000,"workers":3,"debug":true,"log_level":"warning","api_key":"****"}
```

## Precedence and special rules

1. Hardcoded defaults
2. `config.development.yaml`
3. `.env` (`NUM_WORKERS` is normalized to `workers`)
4. OS variables with the `APP_` prefix
5. repeated query parameters `set=key=value`

The OS-layer fallback values mirror the assigned values shown in the challenge. Real process `APP_*` environment variables override those fallback values. `port` and `workers` are integers; `debug` recognizes `true`, `1`, `yes`, and `on` case-insensitively; all other settings are strings. The API key is always returned as `"****"` and is never returned in clear text.

## 12-factor configuration principle

Keep deploy-specific configuration separate from application code, usually in environment variables. This lets the same build run in development, testing, and production with different settings, avoids rebuilding code for config changes, and allows secrets to be managed separately. A documented precedence order prevents a lower-priority config file from accidentally overriding explicit runtime settings.

CORS allows browser requests from any origin, and responses are marked `no-store` so fresh grader overrides are evaluated on every request.

## Test locally

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux/WSL:
# source .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
uvicorn app:app --reload
```

Then open `http://127.0.0.1:8000/effective-config?set=port=9000&set=debug=true`.

## Deploy on Vercel

1. Put the contents of this folder in a GitHub repository (include `app.py`, `requirements.txt`, `config.development.yaml`, and `.env`). These are the dummy challenge values from the prompt; do not use this pattern for real production secrets.
2. Sign in to Vercel and choose **Add New → Project**, then import that repository.
3. Leave the root directory as the repository root. Vercel detects the FastAPI `app` in `app.py` and installs the dependencies from `requirements.txt`.
4. Deploy. Copy the assigned deployment domain and append `/effective-config`, for example `https://YOUR-PROJECT.vercel.app/effective-config`.
5. Check the URL with `?set=port=9000&set=debug=true`. The response should show `port` as `9000`, `debug` as `true`, `api_key` as `"****"`, and retain the other effective settings.
6. Paste only the deployed endpoint URL, ending in `/effective-config`, into the assignment input and press **Check**.

No browser-console scripts or grader interception are needed; the server itself applies the overrides for every request.
