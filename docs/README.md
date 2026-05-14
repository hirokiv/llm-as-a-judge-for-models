# ドキュメント構造

このディレクトリには、LLM-as-a-Judge for Enterprise Systemsの全ドキュメントが格納されています。

## ディレクトリ構成

```
docs/
├── design/          # 設計ドキュメント（実装者向け）
├── user/            # ユーザードキュメント（エンドユーザー向け）
└── README.md        # このファイル
```

## 設計ドキュメント (`design/`)

実装者・開発者向けの詳細な設計仕様書です。システムの内部構造、技術的決定、実装ガイドラインが含まれます。

### アーキテクチャ・設計

| ファイル | 内容 |
|---------|------|
| `00_overview.md` | プロジェクト概要、目的、背景 |
| `01_architecture.md` | システムアーキテクチャ、設計原則 |
| `02_data_models.md` | データモデル、スキーマ定義 |
| `11_diagrams.md` | アーキテクチャ図、ER図 |

### API・インターフェース

| ファイル | 内容 |
|---------|------|
| `03_api_specification.md` | REST API仕様 |
| `04_authentication.md` | 認証・認可の実装 |
| `13_management_interfaces.md` | 管理UI仕様 |

### 実装詳細

| ファイル | 内容 |
|---------|------|
| `05_error_handling.md` | エラーハンドリング戦略 |
| `06_testing.md` | テスト戦略とカバレッジ |
| `08_mlflow_integration.md` | MLflow統合の詳細 |
| `09_idempotency.md` | 冪等性保証の実装 |
| `10_stub_implementation.md` | Stub実装とテスト用AIシステム |
| `12_advanced_evaluation.md` | Rubricベース高度評価手法 |
| `14_logging_strategy.md` | ログ管理戦略 |

### 実装ガイド

| ファイル | 内容 |
|---------|------|
| `15_implementation_checklist.md` | 網羅的な実装チェックリスト |
| `16_test_design.md` | テスト設計書 |
| `07_deployment.md` | デプロイと環境構成 |

## ユーザードキュメント (`user/`)

エンドユーザー・運用担当者向けのドキュメントです。MkDocsで配信され、Webブラウザで閲覧できます。

### 構成

```
user/
├── index.md                    # ホームページ
├── quickstart.md               # クイックスタート
├── architecture.md             # アーキテクチャ概要
├── guides/                     # ガイド
│   ├── installation.md
│   ├── basic-usage.md
│   ├── creating-test-cases.md
│   ├── running-evaluations.md
│   └── analyzing-results.md
├── api/                        # API リファレンス
│   ├── overview.md
│   ├── authentication.md
│   ├── evaluate.md
│   ├── test-cases.md
│   ├── judge-configs.md
│   └── prompt-versions.md
├── concepts/                   # 概念説明
│   ├── lethal-trifecta.md
│   ├── idempotency.md
│   ├── rubric-evaluation.md
│   └── security.md
├── operations/                 # 運用ガイド
│   ├── deployment.md
│   ├── monitoring.md
│   ├── troubleshooting.md
│   └── performance.md
├── developers/                 # 開発者向け
│   ├── setup.md
│   ├── contributing.md
│   ├── testing.md
│   └── release.md
├── faq.md                      # よくある質問
└── changelog.md                # 変更履歴
```

## ドキュメントの閲覧方法

### 設計ドキュメント

設計ドキュメントは直接Markdownファイルを開いて閲覧してください：

```bash
# VS Codeで開く
code docs/design/00_overview.md

# ブラウザで開く（Markdown Preview拡張機能推奨）
```

### ユーザードキュメント

ユーザードキュメントはMkDocsで配信されます：

#### ローカルでプレビュー

```bash
# MkDocsをインストール
pip install mkdocs-material mkdocs-git-revision-date-localized-plugin

# 開発サーバー起動
mkdocs serve

# ブラウザで http://localhost:8000 を開く
```

#### ビルドして配信

```bash
# 静的サイトをビルド
mkdocs build

# site/ ディレクトリが生成される
# Netlify, Vercel, GitHub Pages等にデプロイ可能
```

## ドキュメントの更新

### 設計ドキュメントの更新

```bash
# 該当するMarkdownファイルを直接編集
vi docs/design/03_api_specification.md

# Gitにコミット
git add docs/design/
git commit -m "Update API specification"
```

### ユーザードキュメントの更新

```bash
# ユーザードキュメントを編集
vi docs/user/guides/basic-usage.md

# プレビューで確認
mkdocs serve

# Gitにコミット
git add docs/user/
git commit -m "Update basic usage guide"
```

## ドキュメントの貢献

ドキュメントへの貢献を歓迎します！

1. **Issueで提案** - 新しいドキュメントや改善案を提案
2. **Pull Request** - 修正・追加したドキュメントを提出
3. **レビュー** - 他の貢献者のドキュメントをレビュー

詳細は [コントリビューションガイド](user/developers/contributing.md) を参照してください。

## ライセンス

ドキュメントはMITライセンスの下で公開されています。
