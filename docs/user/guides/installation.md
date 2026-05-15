# インストールガイド

このガイドでは、LLM-as-a-Judge for Enterprise Systemsを10分以内にセットアップする手順を説明します。

## 前提条件

### 必須要件

| 項目 | バージョン | 確認コマンド |
|------|-----------|-------------|
| Python | 3.10以上 | `python --version` |
| uv | 最新版 | `uv --version` |

### APIキー・アカウント

以下のいずれかが必要です:

- **OpenAI APIキー** - [OpenAI Platform](https://platform.openai.com/)で取得
- **Azure OpenAIアカウント** - Azureポータルで設定

### データベース（開発環境）

- **Supabaseアカウント** - [Supabase](https://supabase.com/)で無料アカウント作成

!!! tip "本番環境"
    本番環境ではDatabricksを使用します。詳細は[デプロイメントガイド](../deployment/production-setup.md)を参照してください。

---

## インストール手順

### 1. uvのインストール

=== "macOS / Linux"

    ```bash
    # 公式インストールスクリプト
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # または Homebrew
    brew install uv
    ```

=== "Windows"

    ```powershell
    # PowerShell
    irm https://astral.sh/uv/install.ps1 | iex

    # または winget
    winget install --id=astral-sh.uv -e
    ```

インストール確認:

```bash
uv --version
# 出力例: uv 0.5.17 (2024-01-15)
```

---

### 2. リポジトリのクローン

```bash
cd ~/project  # 任意の作業ディレクトリ
git clone https://github.com/your-org/llm-as-a-judge-for-models.git
cd llm-as-a-judge-for-models
```

!!! info "Gitリポジトリが未初期化の場合"
    現在Phase 0実装中のため、Gitリポジトリが未初期化の可能性があります。その場合は以下を実行:

    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    ```

---

### 3. 仮想環境のセットアップ

```bash
# 仮想環境作成
make venv

# 仮想環境アクティベート
source .venv/bin/activate
```

!!! warning "仮想環境のアクティベート必須"
    以降のすべての操作は仮想環境内で実行してください。プロンプトに `(.venv)` が表示されていることを確認してください。

---

### 4. 依存関係のインストール

```bash
# 開発用依存関係を含むすべてのパッケージをインストール
make install-dev
```

このコマンドは以下を実行します:

- 本番依存関係のインストール（FastAPI, Pydantic, SQLAlchemy等）
- 開発依存関係のインストール（pytest, ruff, mypy等）
- ドキュメント用依存関係のインストール（mkdocs-material等）
- pre-commitフックのインストール（Gitリポジトリが存在する場合）

インストール確認:

```bash
make check-uv
# 出力: ✅ uv is installed: uv 0.5.17
```

---

### 5. 環境変数の設定

#### .envファイルの作成

```bash
# .env.exampleをコピー
cp .env.example .env

# エディタで編集
vim .env  # または nano, code等
```

#### 必須環境変数の設定

=== "OpenAI"

    ```bash
    # LLM Provider
    OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
    LLM_PROVIDER=openai

    # Database (Development)
    SUPABASE_URL=https://xxxxx.supabase.co
    SUPABASE_KEY=eyJhbGci...（Supabaseプロジェクト設定から取得）
    DB_PROVIDER=supabase

    # MLflow
    MLFLOW_TRACKING_URI=http://localhost:5000
    MLFLOW_EXPERIMENT_NAME=llm-judge-evaluations

    # Authentication
    JWT_SECRET_KEY=$(openssl rand -hex 32)
    JWT_ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30

    # Application
    ENVIRONMENT=development
    DEBUG=True
    LOG_LEVEL=INFO
    ```

=== "Azure OpenAI"

    ```bash
    # LLM Provider
    AZURE_OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxx
    AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
    AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
    AZURE_OPENAI_API_VERSION=2023-05-15
    LLM_PROVIDER=azure_openai

    # Database (Development)
    SUPABASE_URL=https://xxxxx.supabase.co
    SUPABASE_KEY=eyJhbGci...
    DB_PROVIDER=supabase

    # MLflow
    MLFLOW_TRACKING_URI=http://localhost:5000
    MLFLOW_EXPERIMENT_NAME=llm-judge-evaluations

    # Authentication
    JWT_SECRET_KEY=$(openssl rand -hex 32)
    JWT_ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30

    # Application
    ENVIRONMENT=development
    DEBUG=True
    LOG_LEVEL=INFO
    ```

#### JWT_SECRET_KEYの生成

```bash
# ランダムな32バイトの16進数文字列を生成
openssl rand -hex 32
# 出力例: a1b2c3d4e5f6789...（64文字）
```

この値を`.env`の`JWT_SECRET_KEY`に設定してください。

環境変数確認:

```bash
make check-env
# 出力: ✅ All required environment variables are set!
```

---

### 6. データベースのセットアップ

#### Supabaseローカル環境の起動

```bash
# Supabaseローカル環境を起動
make db-start

# 出力例:
# Starting Supabase...
# Studio UI: http://localhost:54323
```

#### データベース接続テスト

```bash
make db-test
# 出力: ✅ Database connection successful
```

!!! tip "Supabase Studioでの確認"
    http://localhost:54323 にアクセスすると、Supabase Studioでデータベースを視覚的に確認できます。

---

### 7. MLflowの初期化

```bash
# MLflowサーバーを起動（別ターミナルで実行）
make mlflow

# 出力例:
# Starting MLflow server...
# [INFO] Listening at: http://0.0.0.0:5000
```

MLflow UIを確認: http://localhost:5000

---

## インストール検証

### 1. システム全体の健全性チェック

```bash
# 環境変数確認
make check-env

# uv確認
make check-uv

# データベース接続確認
make db-test
```

### 2. FastAPIサーバーの起動

新しいターミナルで:

```bash
cd /path/to/llm-as-a-judge-for-models
source .venv/bin/activate
make run
```

出力例:

```
Starting FastAPI server...
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 3. ヘルスチェックエンドポイントの確認

別ターミナルで:

```bash
curl http://localhost:8000/health
```

期待されるレスポンス:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "mlflow": "connected",
    "llm_provider": "available"
  },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### 4. API仕様の確認

ブラウザで以下のURLにアクセス:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

!!! success "インストール完了"
    すべてのチェックが成功すれば、インストール完了です！

---

## トラブルシューティング

### よくある問題と解決方法

| 問題 | 原因 | 解決方法 |
|------|------|----------|
| `uv: command not found` | uvが未インストール | [手順1](#1-uv)を再実行 |
| `make: command not found` | makeが未インストール | `sudo apt install make`（Linux）または `brew install make`（macOS） |
| `OPENAI_API_KEY not set` | 環境変数未設定 | `.env`ファイルの確認、`source .env`を実行 |
| `Database connection failed` | Supabaseが起動していない | `make db-start`を実行 |
| `Port 8000 already in use` | ポート競合 | `lsof -ti:8000 \| xargs kill -9`で既存プロセスを終了 |
| `MLflow server error` | MLflowディレクトリの権限問題 | `chmod -R 755 mlruns/`を実行 |

### パッケージが見つからない

```bash
# 仮想環境を再アクティベート
source .venv/bin/activate

# 依存関係を再インストール
uv pip install -e ".[dev]"
```

### pre-commitエラー

```bash
# Gitリポジトリ初期化後に実行
git init
make install-dev
```

### MkDocsサーバーが起動しない

```bash
# 既存のMkDocsプロセスを終了
pkill -f "mkdocs serve"

# 再起動
make docs-serve
```

### データベース接続エラー

```bash
# 環境変数の確認
make check-env

# .envファイルの確認
cat .env | grep SUPABASE

# Supabaseステータス確認
make db-status
```

---

## 次のステップ

インストールが完了したら、以下のガイドに進んでください:

1. **[基本的な使い方](basic-usage.md)** - 最初の評価を10分以内に実行
2. **[テストケースの作成](creating-test-cases.md)** - カスタムテストケースの作成方法
3. **[API概要](../api/overview.md)** - APIエンドポイントの全体像

---

## 参考リンク

- **ドキュメント**: http://localhost:8001（`make docs-serve`で起動）
- **API仕様**: http://localhost:8000/docs
- **MLflow**: http://localhost:5000
- **プロジェクトガイド**: [CLAUDE.md](https://github.com/your-org/llm-as-a-judge-for-models/blob/main/CLAUDE.md)
- **設計書**: [docs/design/](../../design/)
