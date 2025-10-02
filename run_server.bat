@echo off
set PYTHONPATH=src
set GCP_PROJECT=adnovum-gm-cai

echo Starting Conversation Evaluator Server...
echo Server will be available at http://127.0.0.1:8080
echo Press Ctrl+C to stop
echo.
uv run uvicorn src.main:app --host 127.0.0.1 --port 8080 --reload

