# プロジェクト概要

## プロジェクト名
LLM-as-a-Judge for Enterprise Systems

## 目的
企業内で稼働する様々な生成AIシステム（LLMエージェント、RAGシステムなど）の入出力を監視し、プロンプトインジェクション等のセキュリティ攻撃に対する脆弱性を自動評価する「LLM-as-a-judge」モジュールのモックアップを作成する。

## 背景
エンタープライズシステムにおいて、LLMを活用したサービスが増加する中、以下のようなセキュリティリスクが懸念される：
- プロンプトインジェクション攻撃
- 機密データの意図しない漏洩
- 外部システムへの不正な通信
- ユーザー指示の上書き

これらのリスクを体系的に評価・監視するため、Lethal Trifecta（リーサル・トライフェクタ）の概念に基づいた評価フレームワークを構築する。

## Lethal Trifecta とは
以下の3つの条件が揃うことで、致命的なセキュリティリスクが発生する状況を指す：

1. **Private Data Access（機密データへのアクセス）**
   - 顧客データ、取引情報、個人情報などへのアクセス権限

2. **Untrusted Content Exposure（非信頼コンテンツへの曝露）**
   - メール、Webページ、ユーザー入力など、攻撃者が操作可能なコンテンツの処理

3. **External Communication（外部通信能力）**
   - Webhook、API連携、外部システムへのデータ送信能力

## 主要機能

### 1. テストケース管理
- YAMLベースのテストケース定義
- Lethal Trifectaの3要素に基づく攻撃シナリオの分類
- REST API経由でのCRUD操作

### 2. LLM-as-a-Judge 評価エンジン
- 対象AIシステムの出力を自動評価
- リスクスコア（1-5段階）の算出
- 悪用されたベクトルの特定
- 説明可能性（reasoning）の提供
- 改善提案（recommendation）の生成

### 3. MLOps 統合
- MLflowによる評価履歴の記録
- パラメータ、メトリクス、アーティファクトの管理
- Databricksへの移行を見据えた設計

### 4. データベース抽象化
- Supabase（開発環境）
- Databricks（本番環境）への容易な移行
- Repositoryパターンによる実装

## 技術スタック

### バックエンド
- **言語**: Python 3.10+
- **Webフレームワーク**: FastAPI
- **LLM抽象化**: LangChain
- **MLOps**: MLflow

### データベース
- **開発環境**: Supabase（PostgreSQL）
- **本番環境**: Databricks（Delta Lake）

### LLMプロバイダー
- **開発環境**: OpenAI API
- **本番環境**: Azure OpenAI

### その他
- **コンテナ**: Docker / Docker Compose
- **CI/CD**: GitHub Actions
- **テスト**: pytest
- **コード品質**: ruff, mypy
- **ログ収集**: Fluent Bit
- **ログ集約**: Loki
- **監視**: Prometheus / Grafana

## 非機能要件

### セキュリティ
- API認証・認可
- APIキーの安全な管理
- 監査ログの記録

### 冪等性
- 同一入力に対する同一出力の保証
- temperature=0、seed固定
- 実行ごとの冪等性チェック

### パフォーマンス
- API応答時間: 95パーセンタイルで10秒以内（LLM評価含む）
- 並行リクエスト処理

### 可用性
- エラーハンドリングとリトライ機構
- グレースフルデグラデーション

### 保守性
- マイクロサービス指向の論理境界
- プロバイダー切り替えの容易性
- 包括的なドキュメント

## プロジェクト制約

1. **マイクロサービス指向**: API層、サービスロジック層、インフラ・データ層の論理境界を明確に分ける
2. **環境移行性**: 開発環境（Supabase + OpenAI）から本番環境（Databricks + Azure OpenAI）への容易な移行
3. **監査要件**: すべての評価結果とプロセスを追跡可能にする
4. **スケーラビリティ**: 将来的な評価ケース・AIシステムの増加に対応可能な設計

## ドキュメント構成
本仕様書は以下のドキュメントで構成される：

- `00_overview.md` - 本ドキュメント（プロジェクト概要）
- `01_architecture.md` - システムアーキテクチャと設計原則
- `02_data_models.md` - データモデルとスキーマ定義
- `03_api_specification.md` - REST API仕様
- `04_authentication.md` - 認証・認可の実装
- `05_error_handling.md` - エラーハンドリング戦略
- `06_testing.md` - テスト戦略とカバレッジ
- `07_deployment.md` - デプロイと環境構成
- `08_mlflow_integration.md` - MLflow統合の詳細
- `09_idempotency.md` - 冪等性保証の実装
- `10_stub_implementation.md` - Stub実装とテスト用AIシステム
- `11_diagrams.md` - アーキテクチャ図・ER図詳細
- `12_advanced_evaluation.md` - Rubricベース高度評価手法

## 次のステップ
実装者は以下の順序でドキュメントを参照することを推奨：

1. アーキテクチャ設計（`01_architecture.md`）でシステム全体像を把握
2. データモデル（`02_data_models.md`）で扱うデータ構造を理解
3. API仕様（`03_api_specification.md`）でインターフェースを確認
4. 各専門ドキュメント（認証、エラーハンドリング等）で実装詳細を確認
