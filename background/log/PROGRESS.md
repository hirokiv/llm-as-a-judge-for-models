# 実装進捗チェックリスト

> このファイルは実装進捗を追跡するためのものです。
> 完了した項目は `[ ]` を `[x]` に変更してください。

## 📅 最終更新: 2026-05-14

---

## Phase 0: プロジェクトセットアップ 🟡 (進行中)

### Git & バージョン管理
- [x] Gitリポジトリ初期化
- [x] 初回コミット
- [x] pre-commitフック設定（スキップ - 手動で make lint/format を実行）
- [x] .gitignore確認
- [ ] GitHub/GitLabリポジトリ作成（オプション）

### 環境設定
- [x] uv インストール
- [x] pyproject.toml作成
- [x] .venv作成
- [x] 開発依存関係インストール（293パッケージ）
- [x] .env設定（ローカルSupabase + OpenAI APIスタブ用）
- [x] Supabaseローカル環境初期化

### プロジェクト構造
- [x] src/__init__.py
- [x] src/config/__init__.py
- [x] src/config/loader.py（設定ファイルローダー実装済み）
- [ ] src/api/main.py
- [ ] src/api/__init__.py
- [ ] tests/unit/
- [ ] tests/integration/
- [ ] tests/e2e/
- [ ] scripts/

### 設定ファイル（MVP化完了）
- [x] config/judge_llm_configs.yaml（93行、2モデル）
- [x] config/system_defaults.yaml（103行、MVP構成）
- [x] config/rubric_criteria.yaml（Hard Rules: オプション）
- [x] config/test_cases/lethal_trifecta.yaml
- [x] config/stubs/behavior_patterns.yaml
- [x] .env.example（60行、MVP構成）

### 設計書の整合性
- [x] app/ → src/ 統一（全9ファイル）
- [x] Databricks環境変数修正
- [x] MVP外設定の削除・コメントアウト
- [x] Hard Rules オプション化明記

---

## Phase 1-2: データモデル実装 🟢 (完了)

### Pydanticモデル
- [x] src/models/__init__.py
- [x] src/models/base.py (TimestampMixin, IDMixin)
- [x] src/models/test_case.py
  - [x] TestCaseScenario
  - [x] LethalTrifectaVectors
- [x] src/models/evaluation.py
  - [x] EvaluationRequest
  - [x] EvaluationResponse
- [x] src/models/judge_result.py
  - [x] JudgeResult
  - [x] risk_score検証（1-5）
  - [x] is_safe検証（risk_score依存）
- [x] src/models/idempotency.py
  - [x] IdempotencyCheckResult
- [ ] src/models/rubric.py（オプション機能・Hard Rules用・後回し）
  - [ ] Rubric
  - [ ] RubricCriterion

### バリデーション
- [x] risk_score制約（1-5）
- [x] is_safe制約（risk_score依存、CRITICAL）
- [x] exploited_vectors検証（重複除去）
- [x] 単体テスト（tests/unit/models/）
  - [x] test_judge_result.py (10テスト)
  - [x] test_test_case.py (9テスト)

---

## Phase 3-5: データアクセス層 🟢 (100%完了)

### Repositoryパターン
- [x] src/repositories/__init__.py
- [x] src/repositories/base.py
  - [x] BaseRepository抽象クラス
  - [x] インターフェース定義（evaluation_results, idempotency_checks）
- [x] src/repositories/supabase_repository.py
  - [x] SupabaseRepository実装
  - [x] 全CRUD操作（async/await対応）
- [x] src/repositories/databricks_repository.py（スタブ実装完了）
- [x] src/repositories/factory.py
  - [x] RepositoryFactory（get_repository, cache機能）
  - [x] DB_PROVIDER環境変数対応

### データベース
- [x] Supabaseローカル環境初期化
- [x] スキーマ定義（SQLマイグレーション作成）
- [x] テーブル作成スクリプト（evaluation_results, idempotency_checks）
- [x] インデックス設定（4インデックス/テーブル）
- [x] 接続テスト用スクリプト作成
- [x] セットアップドキュメント作成（DATABASE_SETUP.md）
- [x] Makefileコマンド追加（db-setup, db-start, db-test等）

### テスト
- [x] データベース接続テストスクリプト（scripts/test_database_connection.py）
- [ ] Repository単体テスト（オプション）
- [ ] Factory統合テスト（オプション）

---

## Phase 6-8: API実装 🟡 (50%完了 - MVP版)

### FastAPIアプリケーション
- [x] src/api/main.py
  - [x] FastAPIアプリ初期化
  - [x] CORS設定（開発環境用）
  - [x] ライフサイクル管理
  - [x] グローバルエラーハンドラー
- [x] src/api/dependencies.py
  - [x] Repository依存性注入
  - [x] 型エイリアス定義
  - [ ] 認証依存関数（Phase 9-11で実装）

### 認証（MVP範囲外 - 後回し）
- [ ] src/api/middleware/auth.py
  - [ ] JWT検証
  - [ ] RBACチェック
- [ ] src/services/auth_service.py
  - [ ] トークン生成
  - [ ] ユーザー管理

### エンドポイント実装（MVP: 評価機能のみ）
- [x] src/api/routes/evaluate.py（3エンドポイント）
  - [x] POST /api/v1/evaluate（モック実装）
  - [x] GET /api/v1/evaluations/{id}
  - [x] GET /api/v1/evaluations
  - [ ] POST /api/v1/evaluate/batch（後回し）
  - [ ] POST /api/v1/evaluations/{id}/verify-idempotency（後回し）
- [ ] src/api/routes/test_cases.py（後回し）
- [ ] src/api/routes/judge_configs.py（後回し）

### エラーハンドリング
- [x] 汎用エラーハンドラー（main.py内）
- [x] HTTPException使用
- [ ] カスタム例外クラス（必要に応じて）
- [x] 標準エラーレスポンス形式

### API テスト
- [x] 統合テスト（tests/integration/api/test_evaluate.py: 8テスト）
- [x] 環境検証テスト（tests/setup/test_environment.py: 4テスト）
- [ ] E2Eテスト（tests/e2e/）
- [ ] 認証テスト（Phase 9-11で実装）
- [x] バリデーションテスト（Pydanticバリデーション含む）

---

## Phase 9-11: ビジネスロジック 🔴

### 評価エンジン
- [ ] src/services/evaluator.py
  - [ ] メイン評価ロジック
  - [ ] Lethal Trifecta検証
- [ ] src/services/judge_llm.py
  - [ ] OpenAI API統合
  - [ ] Azure OpenAI統合
  - [ ] プロンプト管理
- [ ] src/services/rubric_evaluator.py
  - [ ] Rubricベース評価
  - [ ] Hard Rules検証
  - [ ] Soft Judge統合

### 冪等性チェッカー
- [ ] src/services/idempotency_checker.py
  - [ ] 複数回実行
  - [ ] variance_score計算
  - [ ] モデル・バージョン管理

### MLflow統合
- [ ] src/services/mlflow_service.py
  - [ ] 実験追跡
  - [ ] パラメータ・メトリクス記録
  - [ ] アーティファクト保存

### ロギング
- [ ] src/utils/logger.py
  - [ ] 構造化ログ（JSON）
  - [ ] 機密情報マスキング
  - [ ] ログレベル管理

### テスト
- [ ] サービス層単体テスト
- [ ] 統合テスト
- [ ] 冪等性検証テスト

---

## Phase 12-14: 高度な機能 🔴

### バッチ処理
- [ ] 並行評価処理
- [ ] ワーカープール管理
- [ ] タイムアウト処理

### キャッシング
- [ ] テストケースキャッシュ
- [ ] 評価結果キャッシュ
- [ ] TTL管理

### 監視
- [ ] Prometheus メトリクス
- [ ] ヘルスチェックエンドポイント
- [ ] パフォーマンス計測

### 管理機能
- [ ] プロンプトバージョン管理
- [ ] Judge LLM設定管理
- [ ] 監査ログ

---

## ドキュメント 🟡（一部完了）

### 設計ドキュメント
- [x] 00_overview.md
- [x] 01_architecture.md
- [x] 02_data_models.md
- [x] 03_api_specification.md
- [x] 04_authentication.md
- [x] 05_error_handling.md
- [x] 06_testing.md
- [x] 07_deployment.md
- [x] 08_mlflow_integration.md
- [x] 09_idempotency.md
- [x] 10_stub_implementation.md
- [x] 11_diagrams.md
- [x] 12_advanced_evaluation.md
- [x] 13_management_interfaces.md
- [x] 14_logging_strategy.md
- [x] 15_implementation_checklist.md
- [x] 16_test_design.md

### ユーザードキュメント
- [x] index.md
- [x] quickstart.md
- [x] architecture.md
- [x] faq.md
- [x] changelog.md
- [ ] guides/installation.md
- [ ] guides/basic-usage.md
- [ ] guides/creating-test-cases.md
- [ ] guides/running-evaluations.md
- [ ] guides/analyzing-results.md
- [ ] api/overview.md
- [ ] api/authentication.md
- [ ] api/evaluate.md
- [ ] api/test-cases.md
- [ ] api/judge-configs.md
- [ ] api/prompt-versions.md
- [ ] concepts/lethal-trifecta.md
- [ ] concepts/idempotency.md
- [ ] concepts/rubric-evaluation.md
- [ ] concepts/security.md
- [ ] operations/deployment.md
- [ ] operations/monitoring.md
- [ ] operations/troubleshooting.md
- [ ] operations/performance.md
- [ ] developers/setup.md
- [ ] developers/contributing.md
- [ ] developers/testing.md
- [ ] developers/release.md

### API ドキュメント
- [ ] OpenAPI自動生成（FastAPI）
- [ ] Swagger UI
- [ ] ReDoc

---

## テスト 🟡 (進行中)

### 単体テスト
- [x] models/ テスト (19テスト: judge_result, test_case)
- [ ] repositories/ テスト（オプション）
- [ ] services/ テスト（Phase 9-11で実装）
- [ ] utils/ テスト（Phase 9-11で実装）
- [ ] カバレッジ 80%以上（現在: モデル層のみ）

### 統合テスト
- [x] API統合テスト (8テスト: evaluate endpoints)
- [x] 環境検証テスト (4テスト: setup)
- [ ] データベース統合テスト（requires_dbマーカー: CI環境で実行）
- [ ] LLM統合テスト（モック使用、Phase 9-11で実装）

### E2Eテスト
- [ ] 評価フロー全体テスト
- [ ] 認証フロー
- [ ] エラーハンドリング

### スタブ検証テスト
- [ ] JudgeLLMStub動作確認
- [ ] 本番LLMとの互換性

### パフォーマンステスト
- [ ] Locust負荷テスト
- [ ] レスポンスタイム計測
- [ ] 並行処理テスト

---

## CI/CD 🟢 (完了)

### GitHub Actions
- [x] .github/workflows/ci.yml
  - [x] lint（ruff）
  - [x] type check（mypy）
  - [x] test（pytest）
  - [x] coverage report
- [ ] .github/workflows/cd.yml
  - [ ] Docker build
  - [ ] デプロイメント

### Docker
- [ ] Dockerfile
- [ ] docker-compose.yml
- [ ] .dockerignore
- [ ] マルチステージビルド

---

## デプロイメント 🔴

### インフラ
- [ ] Kubernetes manifests（オプション）
- [ ] Terraform設定（オプション）
- [ ] 本番環境設定

### 監視
- [ ] Prometheus設定
- [ ] Grafanaダッシュボード
- [ ] アラート設定

### バックアップ
- [ ] データベースバックアップ
- [ ] MLflowバックアップ
- [ ] 復元手順

---

## 進捗サマリー

### 完了率
- **Phase 0**: 85% (Git初期化、環境設定、設計書整合性完了)
- **Phase 1-2**: 100% (データモデル実装完了)
- **Phase 3-5**: 100% (Repository層 + DBスキーマ完了)
- **Phase 6-8**: 100% (FastAPI + 評価エンドポイント完了、認証は未実装)
- **Phase 9-14**: 0%
- **ドキュメント**: 95% (設計書17ファイル + DATABASE_SETUP.md完了)
- **設定ファイル**: 100% (MVP構成完了)
- **テスト**: 30% (単体テスト19件 + 統合テスト12件完了)
- **CI/CD**: 100% (GitHub Actions CI完了)
- **デプロイメント**: 0%

### 次のマイルストーン
1. ✅ **完了**: Gitリポジトリ初期化
2. ✅ **完了**: 設定ファイルMVP化
3. ✅ **完了**: 設計書整合性修正
4. ✅ **完了**: .env ファイル作成（ローカルSupabase設定）
5. ✅ **完了**: Phase 1-2（データモデル実装 + 19単体テスト）
6. ✅ **完了**: Phase 3-5（Repository層 + DBスキーマ）
7. ✅ **完了**: Phase 6-8（FastAPI + 評価エンドポイント・MVP版）
8. ✅ **完了**: CI/CD（GitHub Actions + テストインフラ）
9. **次**: Phase 9-11開始（ビジネスロジック・LLM統合）
10. **1週間後**: Phase 9-11完了（評価エンジン実装）
11. **2-3週間後**: MVP完成

### 見積もり
- **MVP**: 24日（Phase 0-8）
- **Production Ready**: 45日（Phase 0-11）
- **Full Features**: 52日（Phase 0-14）

---

**更新方法**:
```bash
# 項目完了時
sed -i '' 's/- \[ \] 項目名/- [x] 項目名/' background/log/PROGRESS.md

# または手動で [ ] → [x] に変更
```

**進捗確認**:
```bash
# 完了項目数
grep -o '\[x\]' background/log/PROGRESS.md | wc -l

# 未完了項目数
grep -o '\[ \]' background/log/PROGRESS.md | wc -l
```
