# 実装チェックリスト

## 概要
本ドキュメントは、LLM-as-a-Judgeシステムの完全な実装チェックリストを提供する。全15個の仕様書を統合し、実装順序と依存関係を考慮した網羅的なタスクリストとして整理している。

## ドキュメント整合性分析の結果

### 検出された不整合と対応方針

#### 1. API仕様の不完全性 🔴 **Critical**
**問題**: `/api/v1/judge-llm-configs/*` および `/api/v1/prompt-versions/*` エンドポイントが `03_api_specification.md` に欠落

**対応**:
- [ ] 03_api_specification.md にJudge LLM設定管理API（6エンドポイント）を追加
- [ ] 03_api_specification.md にプロンプトバージョン管理API（3エンドポイント）を追加
- [ ] 認可テーブルを更新

#### 2. データモデルの曖昧性 🟡 **Medium**
**問題**: `risk_score=2` の場合の `is_safe` 値が制約されていない

**対応**:
- [ ] 02_data_models.md の JudgeResult バリデーションを修正
- [ ] risk_score と is_safe の対応表を明示

#### 3. 認証・認可の不完全性 🟡 **Medium**
**問題**: Judge LLM設定APIの認可テーブルが `04_authentication.md` に欠落

**対応**:
- [ ] 04_authentication.md に `/judge-llm-configs/*` の認可テーブルを追加
- [ ] `/prompt-versions/*` の認可テーブルを追加

#### 4. 機密情報の残存 🟡 **Medium**
**問題**: 「残高」「口座」等の金融業界特有表現が複数ドキュメントに残存

**対応**:
- [ ] 全ドキュメントで「残高」→「データ値」等に置換
- [ ] 「口座」→「顧客情報」等に置換
- [ ] または例示用であることを明記

#### 5. 技術スタックの記載漏れ 🟢 **Low**
**問題**: Loki、Fluentd等のログ基盤が `00_overview.md` に記載されていない

**対応**:
- [ ] 00_overview.md の技術スタックセクションを更新

#### 6. プロンプトバージョン管理の不整合 🟡 **Medium**
**問題**: `09_idempotency.md` では固定バージョン、`13_management_interfaces.md` では動的管理

**対応**:
- [ ] 09_idempotency.md でプロンプトバージョンの動的取得ロジックを追加
- [ ] デフォルトバージョンの扱いを明示

---

## 実装フェーズ別チェックリスト

### Phase 0: プロジェクトセットアップ（推定: 1-2日）

#### 0.1 開発環境構築
- [ ] Python 3.10+ のインストール確認
- [ ] pyenv / venv による仮想環境作成
- [ ] Git リポジトリの初期化
- [ ] .gitignore の設定（.env, __pycache__, .venv等）

#### 0.2 依存パッケージインストール
```bash
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
langchain==0.1.0
langchain-openai==0.0.2
mlflow==2.9.2
supabase==2.3.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
ruff==0.1.8
mypy==1.7.1
```

- [ ] `pip install -r requirements.txt` の実行
- [ ] 開発ツールのインストール（ruff, mypy）
- [ ] pre-commit hooks の設定

#### 0.3 ディレクトリ構造作成
```
llm-as-a-judge-for-models/
├── src/
│   ├── api/              # FastAPI エンドポイント
│   ├── services/         # ビジネスロジック
│   ├── models/           # Pydanticモデル
│   ├── repositories/     # データアクセス
│   ├── llm/              # LLM抽象化
│   ├── auth/             # 認証・認可
│   ├── utils/            # ユーティリティ
│   └── config.py         # 設定管理
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── prompts/              # テストケースYAML
├── stubs/                # Stub実装
├── docs/                 # 仕様書
├── scripts/              # ユーティリティスクリプト
├── .env.example          # 環境変数テンプレート
├── docker-compose.yml    # 開発環境
└── README.md
```

- [ ] ディレクトリ構造の作成
- [ ] `__init__.py` ファイルの配置

#### 0.4 環境変数設定
- [ ] `.env.example` の作成
- [ ] `.env` の作成（実際の認証情報）
```ini
# LLM Provider
OPENAI_API_KEY=sk-...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...

# Database
SUPABASE_URL=https://...
SUPABASE_KEY=...
DATABRICKS_TOKEN=...
DATABRICKS_HOST=...

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=llm-judge-evaluations

# Auth
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=INFO
```

- [ ] 環境変数の検証スクリプト作成

---

### Phase 1: データモデル実装（推定: 2-3日）

**参照**: `02_data_models.md`

#### 1.1 Pydanticモデル実装
- [ ] `src/models/lethal_trifecta.py` - LethalTrifectaVectors
- [ ] `src/models/test_case.py` - TestCaseScenario
- [ ] `src/models/judge_result.py` - JudgeResult
  - [ ] is_safe と risk_score のバリデーション実装
  - [ ] risk_score=2 の場合の制約を追加 🔴
- [ ] `src/models/evaluation.py` - EvaluationRequest, EvaluationResponse
- [ ] `src/models/idempotency.py` - IdempotencyCheckResult
- [ ] `src/models/judge_config.py` - JudgeLLMConfig（from 13_management_interfaces.md）
- [ ] `src/models/prompt_version.py` - PromptVersion

#### 1.2 バリデーションテスト
- [ ] `tests/unit/test_models.py` - 各モデルのバリデーション
- [ ] エッジケース（境界値、不正値）のテスト
- [ ] サンプルデータでの動作確認

---

### Phase 2: データベース構築（推定: 2-3日）

**参照**: `02_data_models.md`, `09_idempotency.md`

#### 2.1 Supabaseセットアップ（開発環境）
- [ ] Supabaseプロジェクトの作成
- [ ] `evaluation_results` テーブル作成（SQL実行）
- [ ] `idempotency_checks` テーブル作成
  - [ ] model_version_key カラムの追加確認 ✅
  - [ ] UNIQUE制約 (model_version_key, input_hash) の確認
- [ ] `users` テーブル作成（from 04_authentication.md）
- [ ] `api_keys` テーブル作成
- [ ] インデックスの作成
- [ ] トリガーの作成（updated_at自動更新）

#### 2.2 マイグレーションスクリプト
- [ ] `scripts/migrations/001_create_tables.sql`
- [ ] `scripts/migrations/002_create_indexes.sql`
- [ ] `scripts/migrations/003_create_triggers.sql`
- [ ] ロールバックスクリプトの作成

#### 2.3 Databricks準備（本番環境）
- [ ] Databricksワークスペースの確認
- [ ] Delta Lakeテーブル定義のスクリプト作成
- [ ] パーティショニング戦略の確認

#### 2.4 データアクセス層実装
- [ ] `src/repositories/base.py` - BaseRepository（抽象クラス）
- [ ] `src/repositories/supabase_repository.py` - Supabase実装
- [ ] `src/repositories/databricks_repository.py` - Databricks実装（スタブ）
- [ ] Repositoryパターンのファクトリー実装

---

### Phase 3: LLM抽象化層（推定: 2日）

**参照**: `01_architecture.md`, `08_mlflow_integration.md`

#### 3.1 LLMプロバイダー抽象化
- [ ] `src/llm/base_llm.py` - BaseLLM（抽象クラス）
- [ ] `src/llm/openai_llm.py` - OpenAI実装
- [ ] `src/llm/azure_openai_llm.py` - Azure OpenAI実装
- [ ] `src/llm/factory.py` - LLMFactory（プロバイダー選択）

#### 3.2 Judge LLM実装
- [ ] `src/llm/judge_llm.py` - JudgeLLM クラス
- [ ] プロンプトテンプレート管理
  - [ ] `prompts/judge_prompt_v1.0.txt`
  - [ ] プロンプトバージョン管理機能 🔴
- [ ] JSON出力のパース・バリデーション
- [ ] リトライ機構の実装

#### 3.3 LLMテスト
- [ ] `tests/unit/test_llm_factory.py`
- [ ] `tests/integration/test_judge_llm.py`
- [ ] モックLLMレスポンスでのテスト

---

### Phase 4: コアサービス実装（推定: 3-4日）

**参照**: `01_architecture.md`, `09_idempotency.md`, `12_advanced_evaluation.md`

#### 4.1 テストケース管理サービス
- [ ] `src/services/test_case_service.py`
- [ ] YAMLファイルの読み込み
- [ ] テストケースのCRUD操作
- [ ] キャッシング機構

#### 4.2 評価サービス
- [ ] `src/services/evaluator_service.py`
- [ ] Judge LLM呼び出し
- [ ] 評価結果の生成
- [ ] エラーハンドリング

#### 4.3 冪等性チェックサービス
- [ ] `src/services/idempotency_checker.py`
- [ ] `get_model_version_key()` 実装 ✅
- [ ] `compute_input_hash()` 実装（モデルバージョン含む）
- [ ] 複数回実行・比較ロジック
- [ ] variance_score 計算
- [ ] DBへの保存

#### 4.4 Rubricベース評価（Advanced）
- [ ] `src/services/rubric_evaluator.py`
- [ ] EvaluationCriterion モデル
- [ ] Hard Rules 実装（正規表現、スキーマ検証）※ オプション機能、デフォルト無効
- [ ] Soft Judge 実装（LLM評価）
- [ ] 複合評価ロジック

---

### Phase 5: MLflow統合（推定: 2日）

**参照**: `08_mlflow_integration.md`, `14_logging_strategy.md`

#### 5.1 MLflowセットアップ
- [ ] MLflow Tracking Serverの起動（Docker）
- [ ] Experiment作成
- [ ] Backend Store（PostgreSQL）設定
- [ ] Artifact Store（S3/ローカル）設定

#### 5.2 MLflowロギング実装
- [ ] `src/services/mlflow_logger.py`
- [ ] Run管理（start_run, end_run）
- [ ] パラメータ記録（test_case_id, model_config）
- [ ] メトリクス記録（risk_score, is_safe）
- [ ] アーティファクト記録（reasoning, recommendation）
- [ ] タグ設定（exploited_vectors, environment）

#### 5.3 MLflow統合テスト
- [ ] `tests/integration/test_mlflow_integration.py`
- [ ] Run作成・記録の検証
- [ ] アーティファクトの取得確認

---

### Phase 6: API実装（推定: 4-5日）

**参照**: `03_api_specification.md`, `13_management_interfaces.md`

#### 6.1 FastAPIアプリケーション初期化
- [ ] `src/api/main.py` - FastAPIアプリ作成
- [ ] CORS設定
- [ ] ミドルウェア設定（リクエストID、ログ）
- [ ] 例外ハンドラー登録

#### 6.2 評価API
- [ ] `src/api/routes/evaluate.py`
- [ ] `POST /api/v1/evaluate` - 評価実行
- [ ] `GET /api/v1/evaluations/{run_id}` - 結果取得
- [ ] `GET /api/v1/evaluations` - 一覧取得

#### 6.3 テストケース管理API
- [ ] `src/api/routes/test_cases.py`
- [ ] `GET /api/v1/test-cases` - 一覧取得
- [ ] `GET /api/v1/test-cases/{id}` - 詳細取得
- [ ] `POST /api/v1/test-cases` - 新規作成
- [ ] `PUT /api/v1/test-cases/{id}` - 更新
- [ ] `DELETE /api/v1/test-cases/{id}` - 削除

#### 6.4 冪等性チェックAPI
- [ ] `src/api/routes/idempotency.py`
- [ ] `POST /api/v1/idempotency-check` - チェック実行
- [ ] `GET /api/v1/idempotency-checks/{hash}` - 結果取得

#### 6.5 Judge LLM設定管理API 🔴 **新規追加必要**
- [ ] `src/api/routes/judge_configs.py`
- [ ] `GET /api/v1/judge-llm-configs` - 一覧取得
- [ ] `GET /api/v1/judge-llm-configs/{config_id}` - 詳細取得
- [ ] `POST /api/v1/judge-llm-configs` - 新規作成
- [ ] `PUT /api/v1/judge-llm-configs/{config_id}` - 更新
- [ ] `DELETE /api/v1/judge-llm-configs/{config_id}` - 削除
- [ ] `POST /api/v1/judge-llm-configs/{config_id}/verify-idempotency` - 冪等性検証

#### 6.6 プロンプトバージョン管理API 🔴 **新規追加必要**
- [ ] `src/api/routes/prompt_versions.py`
- [ ] `GET /api/v1/prompt-versions` - 一覧取得
- [ ] `POST /api/v1/prompt-versions` - 新規作成
- [ ] `PUT /api/v1/prompt-versions/{version_id}/activate` - アクティブ化

#### 6.7 03_api_specification.md の更新 🔴
- [ ] Judge LLM設定管理API（6エンドポイント）の追加
- [ ] プロンプトバージョン管理API（3エンドポイント）の追加
- [ ] リクエスト/レスポンススキーマの記載

---

### Phase 7: 認証・認可（推定: 3日）

**参照**: `04_authentication.md`

#### 7.1 JWT認証実装
- [ ] `src/auth/jwt_handler.py`
- [ ] トークン生成（create_access_token）
- [ ] トークン検証（verify_token）
- [ ] リフレッシュトークン対応

#### 7.2 ユーザー管理
- [ ] `src/auth/user_service.py`
- [ ] ユーザー登録
- [ ] ログイン処理
- [ ] パスワードハッシュ化（bcrypt）

#### 7.3 ロールベース認可
- [ ] `src/auth/authorization.py`
- [ ] `require_role()` デコレータ実装
- [ ] `require_permission()` デコレータ実装
- [ ] 各エンドポイントへの適用

#### 7.4 認可テーブルの更新 🔴
- [ ] 04_authentication.md に Judge LLM設定APIの認可テーブル追加
- [ ] プロンプトバージョン管理APIの認可テーブル追加

#### 7.5 認証テスト
- [ ] `tests/unit/test_auth.py`
- [ ] `tests/integration/test_authentication.py`
- [ ] 不正トークンのテスト
- [ ] 権限不足のテスト

---

### Phase 8: エラーハンドリング（推定: 2日）

**参照**: `05_error_handling.md`

#### 8.1 カスタム例外クラス
- [ ] `src/exceptions.py`
- [ ] `LLMProviderError`
- [ ] `TestCaseNotFoundError`
- [ ] `IdempotencyCheckFailedError`
- [ ] `AuthenticationError`
- [ ] `AuthorizationError`

#### 8.2 例外ハンドラー
- [ ] `src/api/exception_handlers.py`
- [ ] グローバル例外ハンドラー
- [ ] HTTPExceptionハンドラー
- [ ] バリデーションエラーハンドラー

#### 8.3 リトライ機構
- [ ] `src/utils/retry.py`
- [ ] LLM APIコール用リトライ
- [ ] データベース接続用リトライ
- [ ] 指数バックオフ実装

---

### Phase 9: ログ・モニタリング（推定: 3-4日）

**参照**: `14_logging_strategy.md`

#### 9.1 構造化ログ実装
- [ ] `src/utils/logging.py` - StructuredLogger
- [ ] JSON形式ログ出力
- [ ] リクエストIDの伝播（ContextVar）
- [ ] 機密情報マスキング（SensitiveDataMasker）

#### 9.2 ログ種別の実装
- [ ] アプリケーションログ
- [ ] 評価実行ログ
- [ ] 冪等性チェックログ
- [ ] 監査ログ（AuditLogger）
- [ ] エラーログ
- [ ] パフォーマンスログ

#### 9.3 ログ収集基盤（オプション）
- [ ] Fluent Bit / Fluentd セットアップ
- [ ] Loki セットアップ
- [ ] Grafana ダッシュボード作成

#### 9.4 監視・アラート
- [ ] Prometheus メトリクス実装
- [ ] アラートルール定義（AlertManager）
- [ ] 通知チャネル設定（Slack/PagerDuty）

#### 9.5 00_overview.md の更新 🔴
- [ ] 技術スタックにLoki、Fluentd等を追加

---

### Phase 10: テスト実装（推定: 4-5日）

**参照**: `06_testing.md`, `10_stub_implementation.md`

#### 10.1 Stub実装
- [ ] `stubs/stub_target_system.py`
- [ ] VulnerabilityLevel enum
- [ ] StubTargetAISystem クラス
- [ ] 3つの脆弱性レベル実装（HIGH, MEDIUM, LOW）
- [ ] ファクトリー関数（create_vulnerable_system等）

#### 10.2 Stub検証テスト
- [ ] `tests/validation/test_stub_behavior.py`
- [ ] High脆弱性Stubの検証（risk_score >= 4）
- [ ] Medium脆弱性Stubの検証（risk_score 2-4）
- [ ] Low脆弱性Stubの検証（risk_score <= 2）
- [ ] Stub一貫性テスト

#### 10.3 ユニットテスト
- [ ] `tests/unit/test_services/` - 各サービスのテスト
- [ ] `tests/unit/test_repositories/` - リポジトリのテスト
- [ ] `tests/unit/test_llm/` - LLM抽象化のテスト
- [ ] モック・フィクスチャの整備

#### 10.4 統合テスト
- [ ] `tests/integration/test_evaluation_flow.py` - E2E評価フロー
- [ ] `tests/integration/test_api_endpoints.py` - APIテスト
- [ ] `tests/integration/test_database.py` - DB操作テスト
- [ ] `tests/integration/test_mlflow.py` - MLflow統合テスト

#### 10.5 E2Eテスト
- [ ] `tests/e2e/test_complete_workflow.py`
- [ ] テストケース作成→評価→結果確認の完全フロー
- [ ] 冪等性チェックの完全フロー

#### 10.6 テストカバレッジ
- [ ] pytest-cov セットアップ
- [ ] カバレッジ80%以上の達成
- [ ] カバレッジレポート生成

---

### Phase 11: 管理UI（推定: 5-7日）

**参照**: `13_management_interfaces.md`

#### 11.1 フロントエンド環境構築
- [ ] Next.js 14 プロジェクト作成
- [ ] TypeScript設定
- [ ] shadcn/ui セットアップ
- [ ] React Query セットアップ
- [ ] Tailwind CSS 設定

#### 11.2 テストケース管理UI
- [ ] `/test-cases` ページ - 一覧表示
- [ ] `/test-cases/new` ページ - 新規作成
- [ ] `/test-cases/[id]` ページ - 詳細・編集
- [ ] Lethal Trifecta ベクトルの視覚化

#### 11.3 Judge LLM設定管理UI
- [ ] `/judge-configs` ページ - 一覧表示
- [ ] `/judge-configs/new` ページ - 新規作成
- [ ] `/judge-configs/[id]` ページ - 詳細・編集
- [ ] 冪等性検証ボタン・結果表示

#### 11.4 プロンプトバージョン管理UI
- [ ] `/prompt-versions` ページ - 一覧表示
- [ ] バージョン比較機能
- [ ] アクティブ化トグル

#### 11.5 評価結果ビューア
- [ ] `/evaluations` ページ - 評価履歴一覧
- [ ] `/evaluations/[run_id]` ページ - 詳細表示
- [ ] MLflow UI へのリンク

---

### Phase 12: CI/CD（推定: 2-3日）

**参照**: `07_deployment.md`, `10_stub_implementation.md`

#### 12.1 GitHub Actions ワークフロー
- [ ] `.github/workflows/test.yml` - テスト実行
- [ ] `.github/workflows/lint.yml` - Linter実行
- [ ] `.github/workflows/stub-validation.yml` - Stub検証 🔴
- [ ] `.github/workflows/deploy.yml` - デプロイ

#### 12.2 Stub検証CI
- [ ] Stub動作の自動検証
- [ ] 脆弱性レベル別テスト
- [ ] レポート生成

#### 12.3 Pre-commit hooks
- [ ] `.pre-commit-config.yaml` 作成
- [ ] ruff（Linter）
- [ ] mypy（型チェック）
- [ ] black（フォーマッター）

---

### Phase 13: Docker化（推定: 2日）

**参照**: `07_deployment.md`

#### 13.1 Dockerfile作成
- [ ] `Dockerfile` - FastAPIアプリケーション
- [ ] `Dockerfile.frontend` - Next.jsアプリケーション
- [ ] マルチステージビルド

#### 13.2 Docker Compose
- [ ] `docker-compose.yml` - 開発環境
  - [ ] FastAPI サービス
  - [ ] MLflow サービス
  - [ ] PostgreSQL サービス
  - [ ] Frontend サービス
- [ ] `docker-compose.prod.yml` - 本番環境

#### 13.3 動作確認
- [ ] `docker-compose up` での起動確認
- [ ] ヘルスチェック実装
- [ ] ログ出力確認

---

### Phase 14: デプロイメント（推定: 3-4日）

**参照**: `07_deployment.md`

#### 14.1 Kubernetes準備（オプション）
- [ ] Kubernetes マニフェスト作成
  - [ ] Deployment（API、MLflow）
  - [ ] Service（ClusterIP、LoadBalancer）
  - [ ] ConfigMap（設定）
  - [ ] Secret（認証情報）
  - [ ] Ingress（外部公開）
- [ ] Helm Chart作成（推奨）

#### 14.2 本番環境設定
- [ ] Databricks接続設定
- [ ] Azure OpenAI 設定
- [ ] S3 / Azure Blob Storage 設定
- [ ] 本番用環境変数の設定

#### 14.3 セキュリティ対策
- [ ] APIキーのSecrets Manager管理
- [ ] ネットワークポリシー設定
- [ ] HTTPSの有効化
- [ ] レート制限の設定

---

### Phase 15: ドキュメント修正（推定: 1日）

#### 15.1 不整合の修正 🔴

##### 02_data_models.md
- [ ] JudgeResult の risk_score=2 時の制約を追記
```python
@validator('risk_score', 'is_safe')
def validate_consistency(cls, v, values):
    if 'risk_score' in values and 'is_safe' in values:
        risk = values.get('risk_score')
        safe = values.get('is_safe')

        # risk_score=1 は必ず is_safe=True
        if risk == 1 and not safe:
            raise ValueError('risk_score=1 の場合、is_safe は True であるべきです')

        # risk_score=2 は is_safe=True または False（どちらも許容）
        # ※軽微なリスクの判断は文脈依存

        # risk_score>=3 は必ず is_safe=False
        if risk >= 3 and safe:
            raise ValueError('risk_score>=3 の場合、is_safe は False であるべきです')
    return v
```

##### 03_api_specification.md
- [ ] Judge LLM設定管理APIの追加（L400以降に追加）
```markdown
### 9. Judge LLM設定管理API

#### 9.1 設定一覧取得
GET /api/v1/judge-llm-configs
...（13_management_interfaces.md L330-386 の内容を転記）
```

- [ ] プロンプトバージョン管理APIの追加

##### 04_authentication.md
- [ ] Judge LLM設定APIの認可テーブル追加（L98以降）
```markdown
| GET /judge-llm-configs | ✓ | ✓ | ✓ |
| POST /judge-llm-configs | ✓ | - | - |
| PUT /judge-llm-configs/{id} | ✓ | - | - |
| DELETE /judge-llm-configs/{id} | ✓ | - | - |
| GET /prompt-versions | ✓ | ✓ | ✓ |
| POST /prompt-versions | ✓ | - | - |
```

##### 09_idempotency.md
- [ ] プロンプトバージョンの動的取得ロジック追加（L79-88を修正）
```python
class IdempotencyChecker:
    def __init__(
        self,
        repository: EvaluationRepository,
        judge_config: Optional[JudgeLLMConfig] = None
    ):
        self.repository = repository
        self.judge_config = judge_config or self._get_default_config()

    def _get_default_config(self) -> JudgeLLMConfig:
        """デフォルトJudge LLM設定を取得"""
        # プロンプトバージョン管理サービスから最新アクティブバージョンを取得
        prompt_version_service = PromptVersionService()
        active_version = prompt_version_service.get_active_version()

        return JudgeLLMConfig(
            provider="openai",
            model_name="gpt-4",
            temperature=0.0,
            seed=42,
            prompt_version=active_version.version_id
        )
```

##### 00_overview.md
- [ ] 技術スタックにログ基盤を追加（L70以降）
```markdown
### その他
- **コンテナ**: Docker / Docker Compose
- **CI/CD**: GitHub Actions
- **テスト**: pytest
- **コード品質**: ruff, mypy
- **ログ収集**: Fluent Bit
- **ログ集約**: Loki
- **監視**: Prometheus / Grafana
```

#### 15.2 機密情報の置換 🔴
全ドキュメントで以下を置換：

| 現在の表現 | 置換後 |
|-----------|--------|
| 残高 | データ値 / 重要データ |
| 口座 | 顧客情報 / アカウント情報 |
| 口座残高 | 顧客データ |
| トランザクション | 取引情報 / 処理履歴 |
| お客様のデータ（ID: 12345, 残高: ...） | 顧客情報（ID: 12345, データ値: ...） |

対象ドキュメント：
- [ ] 02_data_models.md
- [ ] 03_api_specification.md
- [ ] 06_testing.md
- [ ] 10_stub_implementation.md
- [ ] 12_advanced_evaluation.md
- [ ] 14_logging_strategy.md

または、各例示箇所に以下を追記：
```markdown
**注**: 以下の例は金融業界のユースケースを想定していますが、本システムは任意のエンタープライズ領域に適用可能です。
```

---

## 実装優先度マトリクス

### 🔴 Critical（Phase 0-7まで）
システムの基本機能に必要な実装。これがないと動作しない。

### 🟡 High（Phase 8-12）
運用・保守に必要な実装。本番環境で必須。

### 🟢 Medium（Phase 13-14）
拡張機能。段階的に追加可能。

### ⚪ Low（Phase 15）
最適化・改善項目。

---

## 実装時の注意事項

### 1. 段階的実装の推奨
Phase 0 → Phase 1 → ... の順序で実装することで、依存関係の問題を回避できる。

### 2. テスト駆動開発（TDD）
各Phaseで実装前にテストを書くことで、仕様の理解と品質向上を図る。

### 3. コードレビューポイント
- [ ] Pydanticバリデーションの網羅性
- [ ] 例外ハンドリングの適切性
- [ ] ログ出力の十分性
- [ ] 機密情報のマスキング
- [ ] 認証・認可の実装

### 4. パフォーマンス検証
- [ ] API応答時間（P95 < 10秒）
- [ ] LLM呼び出しレイテンシー
- [ ] データベースクエリ最適化
- [ ] 並行リクエスト処理

### 5. セキュリティ検証
- [ ] OWASP Top 10 対策
- [ ] プロンプトインジェクション防御
- [ ] APIキーの安全な管理
- [ ] ログからの機密情報除外

---

## 完成基準

### Minimum Viable Product (MVP)
- [ ] Phase 0-7 完了（コアAPI機能）
- [ ] 評価実行・結果取得が動作
- [ ] MLflow統合完了
- [ ] 基本的な認証・認可
- [ ] ユニットテスト（カバレッジ60%以上）

### Production Ready
- [ ] Phase 0-12 完了
- [ ] 管理UI実装
- [ ] CI/CD構築
- [ ] ログ・モニタリング完備
- [ ] 統合テスト完了
- [ ] カバレッジ80%以上

### Enterprise Grade
- [ ] 全Phase完了
- [ ] Kubernetes対応
- [ ] 本番環境デプロイ
- [ ] 監査ログ完備
- [ ] パフォーマンステスト合格
- [ ] セキュリティ監査合格

---

## 推定工数サマリー

| Phase | 内容 | 推定工数 | 累積 |
|-------|------|---------|------|
| 0 | プロジェクトセットアップ | 1-2日 | 2日 |
| 1 | データモデル | 2-3日 | 5日 |
| 2 | データベース | 2-3日 | 8日 |
| 3 | LLM抽象化 | 2日 | 10日 |
| 4 | コアサービス | 3-4日 | 14日 |
| 5 | MLflow統合 | 2日 | 16日 |
| 6 | API実装 | 4-5日 | 21日 |
| 7 | 認証・認可 | 3日 | 24日 |
| 8 | エラーハンドリング | 2日 | 26日 |
| 9 | ログ・モニタリング | 3-4日 | 30日 |
| 10 | テスト | 4-5日 | 35日 |
| 11 | 管理UI | 5-7日 | 42日 |
| 12 | CI/CD | 2-3日 | 45日 |
| 13 | Docker化 | 2日 | 47日 |
| 14 | デプロイメント | 3-4日 | 51日 |
| 15 | ドキュメント修正 | 1日 | 52日 |

**合計**: 約2ヶ月（1人月 x 2.5人相当）

**MVP**: 約24日（Phase 0-7）
**Production Ready**: 約45日（Phase 0-12）

---

## 参考リンク

- [プロジェクト概要](./00_overview.md)
- [アーキテクチャ](./01_architecture.md)
- [データモデル](./02_data_models.md)
- [API仕様](./03_api_specification.md)
- [テスト戦略](./06_testing.md)
- [デプロイメント](./07_deployment.md)
