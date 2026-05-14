# Claude Code プロジェクトガイド

## プロジェクト概要

**LLM-as-a-Judge for Enterprise Systems**

大規模言語モデル（LLM）を評価者として活用し、生成AIシステムのセキュリティを自動評価するフレームワーク。Lethal Trifecta（機密データアクセス + 非信頼コンテンツ + 外部通信）に基づく脅威検出。

## Ground Rules

### コミット時の注意
- ❌ コミット時に、Claudeを共同作業者（Co-Authored-By）として言及しないこと
- ✅ テストケースの通過を確認してからコミットすること
- ✅ コミット前に必ず `make lint` と `make format` を実行

### 依存関係管理
- **必須**: 依存関係は**uvで管理**すること
- `pip`や`pip install`は使用禁止
- 新しいパッケージ追加時は`pyproject.toml`を編集してから`uv pip install -e ".[dev]"`

## インストール済みスキル

このプロジェクトでは以下のAgent Skillsがインストール済みです。これらは自動的に利用可能です。

### 1. **fastapi-python** ✅
**場所**: `~/.agents/skills/fastapi-python`
**提供元**: mindrally/skills
**セキュリティ**: Safe（低リスク）

**機能**:
- FastAPI アプリケーション設計のベストプラクティス
- Pydantic モデル設計パターン
- 依存性注入（Dependency Injection）パターン
- 認証・認可の実装ガイド
- API エンドポイント設計
- エラーハンドリング戦略

**活用フェーズ**:
- Phase 1-2: Pydanticモデル実装
- Phase 6-8: FastAPI実装
- Phase 9-11: ビジネスロジック実装

### 2. **python-testing-patterns** ✅
**場所**: `~/.agents/skills/python-testing-patterns`
**提供元**: wshobson/agents
**セキュリティ**: Safe（低リスク）

**機能**:
- pytest ベストプラクティス
- テストピラミッド戦略（60% unit / 30% integration / 10% E2E）
- モック・フィクスチャパターン
- 統合テスト設計
- カバレッジ最適化
- テストの構造化とモジュール化

**活用フェーズ**:
- 全フェーズ: テスト実装
- Phase 6: API統合テスト
- Phase 9-11: サービス層テスト

### スキルの確認

```bash
# インストール済みスキル一覧
npx skills list

# スキルのアップデート確認
npx skills check

# スキルのアップデート
npx skills update
```

### 追加のスキル探索

```bash
# スキルを検索
npx skills find [query]

# 例: データベーステストスキルを探す
npx skills find database testing

# 例: MLflowスキルを探す
npx skills find mlflow
```

詳細: https://skills.sh/

## プロジェクト構造

```
llm-as-a-judge-for-models/
├── src/                    # ソースコード（実装中）
│   ├── api/               # FastAPI アプリケーション
│   ├── models/            # Pydantic データモデル
│   ├── services/          # ビジネスロジック
│   ├── repositories/      # データアクセス層（Repository pattern）
│   └── utils/             # ユーティリティ
├── tests/                 # テストコード
│   ├── unit/             # 単体テスト（60%）
│   ├── integration/      # 統合テスト（30%）
│   └── e2e/              # E2Eテスト（10%）
├── docs/
│   ├── design/           # 設計ドキュメント（17ファイル）
│   └── user/             # ユーザードキュメント（28ファイル）
├── background/log/       # セッション引き継ぎログ
├── pyproject.toml        # uv依存関係管理
├── Makefile              # 開発タスク自動化（50+コマンド）
└── mkdocs.yml            # ドキュメントサイト設定
```

## 重要な設計原則

### 1. アーキテクチャ
- **レイヤー構造**: API → Service → Repository → Database
- **Repository Pattern**: Supabase/Databricks切り替え可能
- **依存性注入**: FastAPI Dependsを活用
- **クリーンアーキテクチャ**: ビジネスロジックとインフラを分離

### 2. データモデル制約
- `risk_score`: 1-5の整数（必須）
- `is_safe`: boolean
  - `risk_score=1` → `is_safe=True` のみ
  - `risk_score=4,5` → `is_safe=False` のみ
  - `risk_score=2,3` → `True/False` どちらも許容（文脈依存）

### 3. 冪等性保証
- モデル・バージョン毎に保証
- `temperature=0`, `seed`固定
- 複数回実行して`variance_score`を計算
- 目標: `variance_score >= 0.9`

### 4. セキュリティ
- **機密情報の汎用化**: 「残高」「口座」等の金融用語は使用禁止 → 「データ値」「顧客情報」
- **ログマスキング**: メールアドレス、APIキー、クレジットカード番号を自動マスキング
- **認証**: JWT認証、RBAC（admin/evaluator/viewer）
- **監査ログ**: 全操作を記録、7年間保持

## 開発ワークフロー

### 環境セットアップ
```bash
# 仮想環境アクティベート
source .venv/bin/activate

# 状態確認
make check-uv
make check-env
```

### 日常開発
```bash
# コード変更
vim src/...

# フォーマット（必須）
make format

# リント（必須）
make lint

# テスト
make test

# コミット
git add .
git commit -m "feat: Add feature"
```

### よく使うコマンド
```bash
make help              # 全コマンド一覧
make install-dev       # 開発依存関係インストール
make run               # FastAPIサーバー起動
make mlflow            # MLflowサーバー起動
make docs-serve        # MkDocsサーバー起動
make test              # 全テスト実行
make test-cov          # カバレッジ付きテスト
make lint              # リント実行
make format            # コードフォーマット
make clean             # キャッシュクリーンアップ
```

## テスト要件

### テストピラミッド
- **単体テスト**: 60%（モデル、サービス、ユーティリティ）
- **統合テスト**: 30%（API、データベース、LLM統合）
- **E2Eテスト**: 10%（全体フロー）

### カバレッジ目標
- **全体**: 80%以上
- **重要モジュール**: 90%以上（evaluator, judge_llm, idempotency_checker）

### テストマーカー
```python
@pytest.mark.unit           # 単体テスト
@pytest.mark.integration    # 統合テスト
@pytest.mark.e2e            # E2Eテスト
@pytest.mark.stub_validation # スタブ検証
```

## コード品質基準

### Linting
- **ruff**: `ruff check src/ tests/`
- **mypy**: `mypy src/`
- **エラー0**: CIでブロック

### フォーマット
- **ruff format**: 自動フォーマット
- **line-length**: 100文字
- **Python**: 3.10+

### 型ヒント
- すべての関数に型ヒントを記述
- Pydanticモデルを積極活用
- `mypy --strict`準拠

## API設計原則

### REST API（Primary）
- **17エンドポイント**: テストケース管理、評価実行、Judge LLM設定、プロンプトバージョン
- **認証**: すべてのエンドポイントでJWT必須
- **レスポンス**: 統一フォーマット（status, data, error）
- **エラーコード**: 標準化されたエラーコード体系

### GraphQL（将来的にオプション）
- Phase 12-14で検討
- 用途: 複雑な分析クエリ、ダッシュボード
- RESTは維持（ハイブリッドアプローチ）

## 重要なドキュメント

### 設計書（必読）
- `docs/design/00_overview.md` - プロジェクト概要
- `docs/design/01_architecture.md` - アーキテクチャ設計
- `docs/design/02_data_models.md` - データモデル定義
- `docs/design/03_api_specification.md` - API仕様（17エンドポイント）
- `docs/design/15_implementation_checklist.md` - 実装チェックリスト（500+項目）
- `docs/design/16_test_design.md` - テスト設計

### 引き継ぎログ
- `background/log/QUICKSTART.md` - クイックスタートガイド
- `background/log/2026-05-14_session_handover.md` - 詳細セッションログ
- `background/log/PROGRESS.md` - 実装進捗チェックリスト

## 技術スタック

### Backend
- **FastAPI** 0.136.1 - WebフレームワークWeb
- **Pydantic** 2.13.4 - データ検証
- **SQLAlchemy** 2.0.49 - ORM

### LLM
- **OpenAI API** 2.36.0 - GPT-4
- **Anthropic** 0.102.0 - Claude（オプション）

### Database
- **Supabase** 2.30.0 - 開発環境（PostgreSQL）
- **Databricks** - 本番環境（Delta Lake）

### MLflow
- **MLflow** 3.12.0 - 実験追跡

### Testing
- **pytest** 9.0.3
- **pytest-cov** 7.1.0
- **pytest-asyncio** 1.3.0

### Linting & Formatting
- **ruff** 0.15.12 - Linter & Formatter
- **mypy** 2.1.0 - 型チェック

### Documentation
- **mkdocs-material** 9.7.6 - ドキュメントサイト

## 環境変数（必須設定）

```bash
# LLM Provider
OPENAI_API_KEY=sk-proj-xxxxx
LLM_PROVIDER=openai  # openai | azure_openai

# Database (Development)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGci...
DB_PROVIDER=supabase  # supabase | databricks

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=llm-judge-evaluations

# Authentication
JWT_SECRET_KEY=<openssl rand -hex 32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
ENVIRONMENT=development  # development | staging | production
DEBUG=True
LOG_LEVEL=INFO
```

## 実装フェーズ（15フェーズ、52日見積もり）

1. **Phase 0**: Project Setup（2日）
2. **Phase 1-2**: Data Models（3日）
3. **Phase 3-5**: Data Access（5日）
4. **Phase 6-8**: API Implementation（8日）← MVP達成ライン（24日）
5. **Phase 9-11**: Business Logic（6日）
6. **Phase 12-14**: Advanced Features（7日）

詳細: `docs/design/15_implementation_checklist.md`

## 禁止事項

### コード
- ❌ `pip install` 使用（uvのみ）
- ❌ ハードコードされたAPIキー
- ❌ 金融用語（残高、口座等）の使用
- ❌ `print()`デバッグ（structlogを使用）
- ❌ 型ヒントなしの関数定義
- ❌ テストなしのコミット

### ドキュメント
- ❌ 機密情報の記載
- ❌ 金融データの具体例
- ❌ 実際のAPIキーの記載

### Git
- ❌ `.env`ファイルのコミット
- ❌ `__pycache__/`のコミット
- ❌ 大きなバイナリファイル
- ❌ 直接mainブランチへのpush

## トラブルシューティング

### MkDocsサーバーが起動しない
```bash
pkill -f "mkdocs serve"
make docs-serve
```

### パッケージが見つからない
```bash
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### pre-commitエラー
```bash
# Gitリポジトリ初期化後に実行
git init
make install-dev
```

### データベース接続エラー
```bash
make check-env
# .envファイルの設定を確認
```

## 参考リンク

- **ドキュメント**: http://localhost:8000 (MkDocs)
- **API仕様**: http://localhost:8000/docs (Swagger UI)
- **MLflow**: http://localhost:5000
- **設計書**: docs/design/
- **実装チェックリスト**: docs/design/15_implementation_checklist.md

## セッション開始時のチェックリスト

```bash
cd /Users/hiroki16/project/llm-as-a-judge-for-models
source .venv/bin/activate
cat background/log/QUICKSTART.md  # 前回からの変更を確認
make check-uv
make check-env
git status
```

---

**最終更新**: 2026-05-14
**次のマイルストーン**: Phase 0 完了 → Gitリポジトリ初期化