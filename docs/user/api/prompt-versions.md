# プロンプトバージョン API

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## プロンプトバージョン一覧

**エンドポイント**: `GET /api/v1/prompt-versions`

Judge LLMで使用するプロンプトのバージョン一覧を取得します。

## バージョン作成

**エンドポイント**: `POST /api/v1/prompt-versions`

新しいプロンプトバージョンを作成します。

## バージョンアクティベート

**エンドポイント**: `POST /api/v1/prompt-versions/{id}/activate`

指定したプロンプトバージョンを有効化します。

詳細は[設計書](../../design/03_api_specification.md)を参照してください。
