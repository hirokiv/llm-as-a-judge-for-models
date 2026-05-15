# LLM-as-a-Judge FastAPI Application
FROM python:3.10-slim

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# uv のインストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# プロジェクトファイルのコピー
COPY pyproject.toml ./
COPY README.md ./

# 仮想環境作成と依存関係インストール（本番依存関係のみ）
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e "."

# アプリケーションコードのコピー
COPY src/ ./src/
COPY config/ ./config/

# 非rootユーザーでの実行（セキュリティベストプラクティス）
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# ポート公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# アプリケーション起動
CMD [".venv/bin/uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
