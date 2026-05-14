.PHONY: help install install-dev test lint format clean run mlflow docs-serve docs-build docs-deploy docker-up docker-down

# デフォルトターゲット
.DEFAULT_GOAL := help

# カラー出力
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ ヘルプ

help: ## このヘルプメッセージを表示
	@echo "$(BLUE)LLM-as-a-Judge for Enterprise Systems$(NC)"
	@echo ""
	@echo "$(GREEN)利用可能なコマンド:$(NC)"
	@awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ セットアップ

venv: ## 仮想環境を作成
	@echo "$(GREEN)Creating virtual environment with uv...$(NC)"
	@if [ ! -d ".venv" ]; then \
		uv venv; \
		echo "$(BLUE)Virtual environment created at .venv$(NC)"; \
		echo "$(YELLOW)Activate with: source .venv/bin/activate$(NC)"; \
	else \
		echo "$(BLUE)Virtual environment already exists$(NC)"; \
	fi

install: venv ## 依存関係をインストール
	@echo "$(GREEN)Installing dependencies with uv...$(NC)"
	uv pip install -e .

install-dev: venv ## 開発用依存関係をインストール
	@echo "$(GREEN)Installing development dependencies with uv...$(NC)"
	uv pip install -e ".[dev]"
	@if [ -d ".git" ]; then \
		echo "$(GREEN)Installing pre-commit hooks...$(NC)"; \
		. .venv/bin/activate && pre-commit install; \
	else \
		echo "$(YELLOW)Skipping pre-commit hooks (not a git repository)$(NC)"; \
	fi

install-docs: venv ## ドキュメント用依存関係をインストール
	@echo "$(GREEN)Installing documentation dependencies with uv...$(NC)"
	uv pip install -e ".[docs]"

sync: ## uv.lockから依存関係を同期
	@echo "$(GREEN)Syncing dependencies with uv...$(NC)"
	uv pip sync

lock: ## 依存関係をロック
	@echo "$(GREEN)Locking dependencies with uv...$(NC)"
	uv pip compile pyproject.toml -o requirements.lock

##@ 開発

run: ## FastAPIサーバーを起動
	@echo "$(GREEN)Starting FastAPI server...$(NC)"
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

mlflow: ## MLflowサーバーを起動
	@echo "$(GREEN)Starting MLflow server...$(NC)"
	mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns

dev: ## FastAPIとMLflowを同時に起動（tmux使用）
	@echo "$(GREEN)Starting development servers...$(NC)"
	@if ! command -v tmux > /dev/null; then \
		echo "$(RED)tmux is not installed. Please install tmux or run 'make run' and 'make mlflow' separately.$(NC)"; \
		exit 1; \
	fi
	tmux new-session -d -s llm-judge 'make mlflow'
	tmux split-window -h 'make run'
	tmux attach-session -t llm-judge

##@ ドキュメント

docs-serve: ## MkDocsドキュメントをローカルで起動
	@echo "$(GREEN)Starting MkDocs server...$(NC)"
	@echo "$(BLUE)Documentation will be available at: http://localhost:8000$(NC)"
	mkdocs serve

docs-build: ## MkDocsドキュメントをビルド
	@echo "$(GREEN)Building documentation...$(NC)"
	mkdocs build
	@echo "$(GREEN)Documentation built in site/ directory$(NC)"

docs-deploy: ## MkDocsドキュメントをGitHub Pagesにデプロイ
	@echo "$(GREEN)Deploying documentation to GitHub Pages...$(NC)"
	mkdocs gh-deploy --force

docs-open: ## ビルド済みドキュメントをブラウザで開く
	@if [ -d "site" ]; then \
		echo "$(GREEN)Opening documentation in browser...$(NC)"; \
		open site/index.html || xdg-open site/index.html; \
	else \
		echo "$(RED)Documentation not built. Run 'make docs-build' first.$(NC)"; \
		exit 1; \
	fi

##@ テスト

test: ## 全テストを実行
	@echo "$(GREEN)Running all tests...$(NC)"
	pytest

test-unit: ## ユニットテストのみ実行
	@echo "$(GREEN)Running unit tests...$(NC)"
	pytest tests/unit/

test-integration: ## 統合テストのみ実行
	@echo "$(GREEN)Running integration tests...$(NC)"
	pytest tests/integration/

test-e2e: ## E2Eテストのみ実行
	@echo "$(GREEN)Running E2E tests...$(NC)"
	pytest tests/e2e/ -m e2e

test-stub: ## Stub検証テストを実行
	@echo "$(GREEN)Running stub validation tests...$(NC)"
	pytest tests/validation/ -m stub_validation

test-cov: ## カバレッジ付きでテストを実行
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	pytest --cov=src --cov-report=html --cov-report=term
	@echo "$(BLUE)Coverage report generated in htmlcov/index.html$(NC)"

test-watch: ## テストを監視モードで実行
	@echo "$(GREEN)Running tests in watch mode...$(NC)"
	pytest-watch

##@ コード品質

lint: ## コード品質チェックを実行
	@echo "$(GREEN)Running linters...$(NC)"
	ruff check src/ tests/
	mypy src/

lint-fix: ## 自動修正可能なコード品質問題を修正
	@echo "$(GREEN)Fixing linting issues...$(NC)"
	ruff check --fix src/ tests/

format: ## コードをフォーマット
	@echo "$(GREEN)Formatting code...$(NC)"
	ruff format src/ tests/

format-check: ## フォーマットをチェック（変更なし）
	@echo "$(GREEN)Checking code format...$(NC)"
	ruff format --check src/ tests/

##@ データベース

db-setup: ## データベースをセットアップ（Supabase起動+マイグレーション）
	@echo "$(GREEN)Setting up database...$(NC)"
	./scripts/setup_database.sh

db-start: ## Supabaseローカル環境を起動
	@echo "$(GREEN)Starting Supabase...$(NC)"
	supabase start
	@echo "$(BLUE)Studio UI: http://localhost:54323$(NC)"

db-stop: ## Supabaseローカル環境を停止
	@echo "$(GREEN)Stopping Supabase...$(NC)"
	supabase stop

db-status: ## Supabase接続情報を表示
	@echo "$(GREEN)Supabase status:$(NC)"
	supabase status

db-reset: ## データベースをリセット（マイグレーション再実行）
	@echo "$(YELLOW)Resetting database...$(NC)"
	supabase db reset

db-test: ## データベース接続をテスト
	@echo "$(GREEN)Testing database connection...$(NC)"
	python scripts/test_database_connection.py

##@ Docker

docker-build: ## Dockerイメージをビルド
	@echo "$(GREEN)Building Docker images...$(NC)"
	docker-compose build

docker-up: ## Dockerコンテナを起動
	@echo "$(GREEN)Starting Docker containers...$(NC)"
	docker-compose up -d
	@echo "$(BLUE)API: http://localhost:8000$(NC)"
	@echo "$(BLUE)MLflow: http://localhost:5000$(NC)"

docker-down: ## Dockerコンテナを停止
	@echo "$(GREEN)Stopping Docker containers...$(NC)"
	docker-compose down

docker-logs: ## Dockerコンテナのログを表示
	docker-compose logs -f

docker-clean: ## Dockerイメージとボリュームを削除
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	docker-compose down -v
	docker system prune -f

##@ クリーンアップ

clean: ## 一時ファイルとキャッシュを削除
	@echo "$(GREEN)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf site/
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-all: clean ## すべての生成ファイルを削除（MLflowデータ含む）
	@echo "$(YELLOW)Cleaning all generated files...$(NC)"
	rm -rf mlruns/
	rm -rf mlflow.db
	rm -rf .env
	@echo "$(GREEN)All generated files removed!$(NC)"

##@ デプロイ

deploy-staging: ## ステージング環境にデプロイ
	@echo "$(GREEN)Deploying to staging...$(NC)"
	# ステージング環境へのデプロイコマンドを追加

deploy-production: ## 本番環境にデプロイ
	@echo "$(YELLOW)Deploying to production...$(NC)"
	@read -p "Are you sure you want to deploy to production? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(GREEN)Deploying...$(NC)"; \
		# 本番環境へのデプロイコマンドを追加 \
	else \
		echo "$(RED)Deployment cancelled.$(NC)"; \
	fi

##@ ユーティリティ

check-uv: ## uvがインストールされているか確認
	@echo "$(GREEN)Checking uv installation...$(NC)"
	@if command -v uv > /dev/null; then \
		echo "✅ uv is installed: $$(uv --version)"; \
	else \
		echo "$(RED)❌ uv is not installed$(NC)"; \
		echo "$(YELLOW)Install with: curl -LsSf https://astral.sh/uv/install.sh | sh$(NC)"; \
		echo "$(YELLOW)Or with Homebrew: brew install uv$(NC)"; \
		exit 1; \
	fi

check-env: ## 環境変数をチェック
	@echo "$(GREEN)Checking environment variables...$(NC)"
	@python -c "import os; \
	required = ['OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY', 'JWT_SECRET_KEY', 'MLFLOW_TRACKING_URI']; \
	missing = [var for var in required if not os.getenv(var)]; \
	print('✅ All required environment variables are set!' if not missing else f'❌ Missing: {missing}')"

version: ## バージョン情報を表示
	@echo "$(BLUE)LLM-as-a-Judge for Enterprise Systems$(NC)"
	@python -c "import sys; print(f'Python: {sys.version}')"
	@pip show fastapi | grep Version || echo "FastAPI: not installed"
	@pip show mkdocs-material | grep Version || echo "MkDocs Material: not installed"

show-urls: ## 起動中のサービスのURLを表示
	@echo "$(BLUE)Service URLs:$(NC)"
	@echo "  API Documentation: http://localhost:8000/docs"
	@echo "  API ReDoc:         http://localhost:8000/redoc"
	@echo "  MLflow UI:         http://localhost:5000"
	@echo "  MkDocs (dev):      http://localhost:8000 (run 'make docs-serve')"

##@ CI/CD

ci-test: ## CI環境でテストを実行
	@echo "$(GREEN)Running CI tests...$(NC)"
	pytest --cov=src --cov-report=xml --cov-report=term -v

ci-lint: ## CI環境でlintを実行
	@echo "$(GREEN)Running CI linting...$(NC)"
	ruff check src/ tests/ --output-format=github
	mypy src/ --junit-xml=mypy-report.xml

ci-build: ## CI環境でビルドを実行
	@echo "$(GREEN)Running CI build...$(NC)"
	docker-compose build --no-cache

##@ 開発ツール

shell: ## Pythonシェルを起動
	@echo "$(GREEN)Starting Python shell...$(NC)"
	python

notebook: ## Jupyter Notebookを起動
	@echo "$(GREEN)Starting Jupyter Notebook...$(NC)"
	jupyter notebook

ipython: ## IPythonを起動
	@echo "$(GREEN)Starting IPython...$(NC)"
	ipython
