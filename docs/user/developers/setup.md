# 開発環境構築

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## 前提条件

- Python 3.10以上
- uv (高速パッケージマネージャー)
- Git
- VSCode または PyCharm（推奨）

## セットアップ手順

### 1. リポジトリクローン

```bash
git clone https://github.com/your-org/llm-as-a-judge-for-models.git
cd llm-as-a-judge-for-models
```

### 2. 依存関係インストール

```bash
# uvがインストールされていない場合
curl -LsSf https://astral.sh/uv/install.sh | sh

# 開発依存関係をインストール
make install-dev
```

### 3. 環境変数設定

```bash
cp .env.example .env
# .envファイルを編集
```

### 4. データベースセットアップ

```bash
# Supabaseプロジェクト作成
# スキーマ作成
make db-setup
```

### 5. 動作確認

```bash
# テスト実行
make test

# サーバー起動
make run
```

## IDEセットアップ

### VSCode

推奨拡張機能：

- Python
- Pylance
- Ruff
- Even Better TOML

### PyCharm

- Python interpreterを`.venv/bin/python`に設定
- Ruffをlinterとして設定

詳細は[クイックスタート](../quickstart.md)を参照してください。
