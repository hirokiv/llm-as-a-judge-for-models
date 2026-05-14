# クイックスタート - 次セッション用

## 🚀 即座に開始する

```bash
cd /Users/hiroki16/project/llm-as-a-judge-for-models

# 仮想環境アクティベート
source .venv/bin/activate

# 現在の状態確認
make check-uv
uv pip list | wc -l  # 293パッケージ確認
```

## ✅ 現在の状態（1分で確認）

### インストール済み
- ✅ uv 0.9.2
- ✅ Python 3.10.19 (.venv/)
- ✅ 293パッケージ（FastAPI, pytest, ruff, mkdocs, mlflow等）
- ✅ pyproject.toml（完全な依存関係定義）
- ✅ Makefile（50+コマンド）

### ドキュメント
- ✅ docs/design/ - 17ファイル（設計書）
- ✅ docs/user/ - 5ファイル（ユーザーガイド）
- ✅ mkdocs.yml（Material theme、日本語対応）
- ✅ MkDocsサーバー: http://localhost:8000 起動中

### 未実施
- ❌ Gitリポジトリ未初期化
- ❌ .env未設定
- ❌ データベース未構築
- ❌ ソースコード未実装（src/__init__.pyのみ）

## 🎯 次のアクション（推奨順）

### 1. Gitリポジトリ初期化（5分）
```bash
git init
git add .
git commit -m "Initial commit: Project structure and documentation"
make install-dev  # pre-commitフックをインストール
```

### 2. 環境変数設定（10分）
```bash
cp .env.example .env
# 以下を.envに設定:
# OPENAI_API_KEY=sk-proj-xxxxx
# SUPABASE_URL=https://xxxxx.supabase.co
# SUPABASE_KEY=eyJhbGciOi...
# JWT_SECRET_KEY=$(openssl rand -hex 32)
# MLFLOW_TRACKING_URI=http://localhost:5000
```

### 3. Phase 0: プロジェクトセットアップ（1日）
チェックリスト: `docs/design/15_implementation_checklist.md`

```bash
# 0.1 ディレクトリ構造作成
mkdir -p src/{api,models,services,repositories,utils}
mkdir -p tests/{unit,integration,e2e}
mkdir -p scripts

# 0.2 設定ファイル
touch src/config.py
touch src/api/main.py

# 0.3 テスト環境
pytest --version  # 確認
```

### 4. Phase 1-2: データモデル実装（2日）
```bash
# Pydanticモデル作成
touch src/models/{__init__,test_case,evaluation,judge_result,rubric}.py

# 実装例: docs/design/02_data_models.md 参照
# テスト作成: tests/unit/models/
```

### 5. Phase 3-5: データアクセス層（3日）
```bash
# Repositoryパターン
touch src/repositories/{__init__,base,supabase_repository,factory}.py

# 設計: docs/design/01_architecture.md Section 3.3 参照
```

## 📚 重要ドキュメント

| ドキュメント | 用途 | パス |
|------------|------|------|
| 実装チェックリスト | 500+項目の作業リスト | docs/design/15_implementation_checklist.md |
| API仕様 | REST API 17エンドポイント | docs/design/03_api_specification.md |
| データモデル | Pydantic定義、ER図 | docs/design/02_data_models.md |
| テスト設計 | フェーズ別テスト戦略 | docs/design/16_test_design.md |
| アーキテクチャ | レイヤー設計、DDD | docs/design/01_architecture.md |

## 🛠️ よく使うコマンド

```bash
# 開発
make help              # コマンド一覧
make venv              # 仮想環境作成
make install-dev       # 依存関係インストール

# コード品質
make format            # コードフォーマット
make lint              # リント実行
make test              # テスト実行
make test-cov          # カバレッジ付きテスト

# サーバー起動
make run               # FastAPI (http://localhost:8000)
make mlflow            # MLflow (http://localhost:5000)
make docs-serve        # MkDocs (http://localhost:8000)

# クリーンアップ
make clean             # キャッシュ削除
make clean-all         # 全生成ファイル削除
```

## 🔍 トラブルシューティング

### Q: MkDocsサーバーが起動しない
```bash
# 既存サーバーを停止
pkill -f "mkdocs serve"

# 再起動
make docs-serve
```

### Q: pre-commitエラー
```bash
# Gitリポジトリ初期化してから実行
git init
make install-dev
```

### Q: パッケージが見つからない
```bash
# 仮想環境アクティベート確認
which python  # .venv/bin/python であること

# 再インストール
uv pip install -e ".[dev]"
```

## 📊 進捗追跡

### 実装フェーズ（15フェーズ、52日見積もり）
- [ ] Phase 0: Project Setup (2日) ← **まずはここから**
- [ ] Phase 1-2: Data Models (3日)
- [ ] Phase 3-5: Data Access (5日)
- [ ] Phase 6-8: API Implementation (8日)
- [ ] Phase 9-11: Business Logic (6日)
- [ ] Phase 12-14: Advanced Features (7日)

### MVP達成条件（24日）
- Phase 0-8完了
- 基本的な評価API動作
- テストカバレッジ50%以上
- ドキュメント更新

## 💾 バックアップ・復元

### 状態保存
```bash
# 依存関係
uv pip freeze > requirements.lock

# データベース（実装後）
# pg_dump でバックアップ
```

### セッション再開
```bash
cd /Users/hiroki16/project/llm-as-a-judge-for-models
source .venv/bin/activate
git status
make help
```

---

**詳細**: `background/log/2026-05-14_session_handover.md`
**開始推奨時刻**: いつでも可
**所要時間**: Phase 0 から 2日で基本構造完成
