# インストールガイド

!!! info "開発中"
    このページは現在作成中です。基本的なインストール手順は[クイックスタート](../quickstart.md)を参照してください。

## 概要

このガイドでは、LLM-as-a-Judge for Enterprise Systemsの詳細なインストール手順を説明します。

## 前提条件

- Python 3.10以上
- [uv](https://github.com/astral-sh/uv) - 高速なPythonパッケージマネージャー
- OpenAI APIキーまたはAzure OpenAIアカウント
- Supabaseアカウント（開発環境）またはDatabricksアクセス（本番環境）

## インストール手順

詳細は[クイックスタート](../quickstart.md)を参照してください。

## トラブルシューティング

### よくある問題

#### uvが見つからない

```bash
# インストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# または
brew install uv
```

## 次のステップ

- [基本的な使い方](basic-usage.md)
- [テストケースの作成](creating-test-cases.md)
