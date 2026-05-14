# Judge LLM 設定 API

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## Judge LLM設定一覧

**エンドポイント**: `GET /api/v1/judge-llm-configs`

使用可能なJudge LLM設定の一覧を取得します。

## 設定作成

**エンドポイント**: `POST /api/v1/judge-llm-configs`

### リクエスト

```json
{
  "model_name": "gpt-4",
  "model_version": "0613",
  "temperature": 0,
  "seed": 42,
  "system_prompt": "Judge LLM用プロンプト"
}
```

## 冪等性検証

**エンドポイント**: `POST /api/v1/judge-llm-configs/{id}/verify-idempotency`

指定したJudge LLM設定の冪等性を検証します。

詳細は[設計書](../../design/03_api_specification.md)を参照してください。
