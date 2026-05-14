# 変更履歴

このページでは、LLM-as-a-Judge for Enterprise Systemsの主要な変更を記録しています。

バージョニングは [Semantic Versioning](https://semver.org/) に従います。

## [Unreleased]

### 計画中
- 管理UI実装
- リアルタイムストリーム評価
- 自動テストケース生成

## [1.0.0] - 2024-XX-XX

### 追加
- 🎉 初回リリース
- ✅ コア評価API実装
- ✅ Lethal Trifectaベースの評価フレームワーク
- ✅ Judge LLM設定管理API
- ✅ プロンプトバージョン管理
- ✅ MLflow統合
- ✅ 冪等性保証機能（モデル・バージョン毎）
- ✅ Rubricベース評価
- ✅ Hard Rules + Soft Judge二層防御
- ✅ REST API
- ✅ JWT認証・RBAC
- ✅ 構造化ログ
- ✅ Prometheus/Grafana監視
- ✅ Supabase/Databricks対応
- ✅ OpenAI/Azure OpenAI対応

### ドキュメント
- 📚 包括的なユーザードキュメント
- 📚 詳細な設計ドキュメント
- 📚 実装チェックリスト
- 📚 テスト設計書

### インフラ
- 🐳 Docker/Docker Compose対応
- ☸️ Kubernetes対応
- 🔄 CI/CDワークフロー

---

## [0.3.0] - 2024-XX-XX (Beta)

### 追加
- Judge LLM設定管理機能
- プロンプトバージョン管理
- 冪等性検証機能

### 変更
- データモデルの更新（model_version_key追加）
- API仕様の拡張（10エンドポイント追加）

### 修正
- risk_score=2時のis_safe制約を明確化
- 機密情報の汎用表現への置換

---

## [0.2.0] - 2024-XX-XX (Alpha)

### 追加
- Rubricベース評価機能
- Hard Rules実装
- Soft Judge統合
- MLflow統合
- 冪等性チェック（基本版）

### 変更
- 評価エンジンのリファクタリング
- データベーススキーマの改善

---

## [0.1.0] - 2024-XX-XX (Preview)

### 追加
- 基本的な評価API
- テストケース管理
- Judge LLM基本実装
- Lethal Trifecta評価

### 初期実装
- FastAPIアプリケーション
- Pydanticモデル
- Supabase統合
- OpenAI API統合

---

## フォーマットについて

- `Added`: 新機能
- `Changed`: 既存機能の変更
- `Deprecated`: 非推奨（将来削除予定）
- `Removed`: 削除された機能
- `Fixed`: バグ修正
- `Security`: セキュリティ関連

---

**最新版のダウンロード**: [Releases](https://github.com/your-org/llm-as-a-judge-for-models/releases)
