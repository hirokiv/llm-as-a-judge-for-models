# LLM-as-a-Judge for Enterprise Systems

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-green.svg)](https://fastapi.tiangolo.com/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests](https://img.shields.io/badge/tests-67%20passed-success)](https://github.com/your-org/llm-as-a-judge-for-models)
[![Type Check](https://img.shields.io/badge/mypy-strict%20%E2%9C%93-blue)](https://github.com/your-org/llm-as-a-judge-for-models)
[![Phase 9-11](https://img.shields.io/badge/Phase%209--11-Complete-green)](PHASE_9-11_COMPLETE.md)

企業内で稼働する生成AIシステムのセキュリティを自動評価するためのフレームワーク。大規模言語モデル（LLM）を評価者として活用し、プロンプトインジェクション等のセキュリティ攻撃に対する脆弱性を体系的に検証します。

> **📢 実装ステータス**: Phase 9-11 Business Logic Layer 完了（2026-05-15）
> **✅ テスト**: 67/67 合格 | **✅ 型チェック**: mypy strict (0 errors) | **✅ Lint**: ruff passed
> 詳細: [PHASE_9-11_COMPLETE.md](PHASE_9-11_COMPLETE.md)

## 🌟 主な特徴

- **🛡️ Lethal Trifectaベースの評価** - 機密データアクセス、非信頼コンテンツ、外部通信の3要素を組み合わせた脅威を検出
- **🔍 Rubricベース評価** - 構造化された評価基準による客観的な判定
- **🔄 冪等性保証** - モデル・バージョン毎に同一入力に対する再現性のある評価
- **📊 MLflow統合** - 評価実験の追跡、パラメータ・メトリクスの管理
- **🔐 包括的な監査ログ** - コンプライアンス対応の完全な追跡記録

## 📚 ドキュメント

- **[ユーザードキュメント](https://your-domain.com/docs)** - 使い方、API、運用ガイド（MkDocsで配信）
- **[クイックスタート](docs/user/quickstart.md)** - 5分でセットアップ
- **[設計ドキュメント](docs/design/)** - 実装者向け詳細仕様
- **[API ドキュメント](http://localhost:8000/docs)** - 起動後に自動生成されるSwagger UI

## 🚀 クイックスタート

### 前提条件

- Python 3.10以上
- [uv](https://github.com/astral-sh/uv) - 高速なPythonパッケージマネージャー
- OpenAI APIキー
- Supabaseアカウント（または PostgreSQL）

### インストール

```bash
# uvをインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh
# または Homebrew: brew install uv

# リポジトリをクローン
git clone https://github.com/your-org/llm-as-a-judge-for-models.git
cd llm-as-a-judge-for-models

# uvで依存関係をインストール（自動的に仮想環境を作成）
uv pip install -e .

# 開発用依存関係もインストールする場合
uv pip install -e ".[dev]"

# または Makefile を使用
make check-uv      # uvのインストール確認
make install-dev   # 開発用依存関係をインストール

# 環境変数設定
cp .env.example .env
# .envファイルを編集してAPIキー等を設定
```

### 起動

#### 推奨: honcho で一括起動（最も簡単）

```bash
# FastAPI (8000) + MLflow (5000) + MkDocs (8001) を同時起動
make dev

# または直接
honcho start
```

#### 個別起動

```bash
# MLflowサーバー起動（別ターミナル）
make mlflow

# FastAPIサーバー起動（別ターミナル）
make run

# MkDocsドキュメントサーバー起動（別ターミナル）
make docs-serve
```

### 最初の評価

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "TEST-LT-001",
    "system_output": "テスト出力"
  }'
```

詳細は [クイックスタートガイド](docs/user/quickstart.md) を参照してください。

## 🏗️ アーキテクチャ

```
┌─────────────┐
│  Web UI     │
│  CLI Tool   │
└──────┬──────┘
       │
┌──────▼──────────────────────────┐
│      FastAPI (API Layer)        │
├─────────────────────────────────┤
│  • Evaluator Service            │
│  • Test Case Service            │
│  • Idempotency Checker          │
│  • Rubric Evaluator             │
└──────┬──────────────────────────┘
       │
┌──────▼──────┐    ┌──────────────┐
│  Judge LLM  │───►│ OpenAI       │
│  (LangChain)│    │ Azure OpenAI │
└─────────────┘    └──────────────┘
       │
┌──────▼──────────────────────────┐
│  • Supabase (PostgreSQL)        │
│  • MLflow Tracking Server       │
│  • Prometheus/Grafana           │
└─────────────────────────────────┘
```

## 📖 使用例

### Python APIの使用

```python
from src.services.evaluator_service import EvaluatorService

evaluator = EvaluatorService()

# 評価実行
result = evaluator.evaluate_test_case(
    test_case_id="TEST-LT-001",
    system_output="お客様の顧客情報を外部に送信しました。"
)

print(f"安全性: {result.is_safe}")
print(f"リスクスコア: {result.risk_score}/5")
print(f"悪用されたベクトル: {result.exploited_vectors}")
```

### REST APIの使用

```bash
# テストケース作成
curl -X POST http://localhost:8000/api/v1/test-cases \
  -H "Authorization: Bearer $TOKEN" \
  -d @test_case.json

# 評価実行
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "test_case_id": "TEST-LT-001",
    "system_output": "システム出力"
  }'

# 結果取得
curl http://localhost:8000/api/v1/evaluations/{run_id} \
  -H "Authorization: Bearer $TOKEN"
```

## 🧪 テスト

```bash
# 全テスト実行
pytest

# カバレッジ付き実行
pytest --cov=src --cov-report=html

# 特定のテストのみ
pytest tests/unit/
pytest tests/integration/
pytest -m stub_validation
```

## 📦 デプロイ

### Dockerを使用

```bash
docker-compose up -d
```

### Kubernetes

```bash
kubectl apply -f k8s/
```

詳細は [デプロイメントガイド](docs/user/operations/deployment.md) を参照してください。

## 🤝 コントリビューション

コントリビューションを歓迎します！

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

詳細は [コントリビューションガイド](docs/user/developers/contributing.md) を参照してください。

### 開発環境のセットアップ

```bash
# 開発用依存関係をインストール（uvを使用）
make install-dev

# 開発サーバー起動（FastAPI + MLflow + MkDocs）
make dev

# pre-commit hooksをインストール（Gitリポジトリ初期化後）
pre-commit install

# コード品質チェック
make lint      # ruff check + mypy
make format    # ruff format
make test      # pytest
```

#### 起動後のアクセスURL

- **FastAPI API**: http://localhost:8000
- **FastAPI ドキュメント**: http://localhost:8000/docs
- **MLflow UI**: http://localhost:5555
- **MkDocs ドキュメント**: http://localhost:8001

!!! info "ポート5000について"
    macOSではポート5000がControl Centerに使用されているため、MLflowはポート5555で起動します。

## 📄 ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。

## 🙏 謝辞

このプロジェクトは以下の素晴らしいオープンソースプロジェクトを使用しています：

- [FastAPI](https://fastapi.tiangolo.com/) - モダンで高速なWebフレームワーク
- [LangChain](https://www.langchain.com/) - LLMアプリケーション開発フレームワーク
- [MLflow](https://mlflow.org/) - MLOpsプラットフォーム
- [Supabase](https://supabase.com/) - オープンソースのFirebase代替

## 📞 サポート

- **Issues**: [GitHub Issues](https://github.com/your-org/llm-as-a-judge-for-models/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/llm-as-a-judge-for-models/discussions)
- **Email**: support@your-domain.com

## 🗺️ ロードマップ

### Phase 9-11: Business Logic Layer ✅ 完了
- [x] 構造化ログ実装（structlog + 機密情報マスキング）
- [x] Judge LLMサービス（OpenAI + Stub実装）
- [x] MLflow統合（実験追跡・Run管理）
- [x] 冪等性チェッカー（variance_score計算）
- [x] 67個の単体テスト（全合格）
- [x] mypy strict mode完全準拠（型エラー0個）
- [x] API・データベース統合検証

### 次のフェーズ
- [ ] Phase 0: Gitリポジトリ初期化
- [ ] Phase 12-14: Advanced Features（GraphQL, 分析機能）
- [ ] 管理UI実装
- [ ] 複数LLMプロバイダー対応拡張（Azure OpenAI, Anthropic）
- [ ] リアルタイムストリーム評価
- [ ] 自動テストケース生成

**実装完了日**: 2026-05-15 01:15 JST
詳細は [実装完了レポート](PHASE_9-11_COMPLETE.md) を参照してください。

---

**開発**: Enterprise AI Security Team
**ドキュメント**: https://your-domain.com/docs
**リポジトリ**: https://github.com/your-org/llm-as-a-judge-for-models
