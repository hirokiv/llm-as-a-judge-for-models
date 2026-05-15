# Procfile for honcho - Development multi-service startup
# Usage: honcho start
# or: make dev

api: uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
mlflow: .venv/bin/mlflow server --host 127.0.0.1 --port 5555 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns
docs: .venv/bin/mkdocs serve --dev-addr 127.0.0.1:8001
