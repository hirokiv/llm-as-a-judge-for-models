# 評価 API

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## 単一評価実行

**エンドポイント**: `POST /api/v1/evaluate`

### リクエスト

```json
{
  "test_case_id": "TEST-LT-001",
  "system_output": "システムからの出力",
  "judge_config_id": "config-001"
}
```

### レスポンス

```json
{
  "data": {
    "evaluation_id": "eval-123",
    "is_safe": false,
    "risk_score": 4,
    "exploited_vectors": ["confidential_data_access"],
    "reasoning": "判定理由",
    "recommendation": "推奨事項"
  }
}
```

## バッチ評価実行

**エンドポイント**: `POST /api/v1/evaluate/batch`

複数のテストケースをまとめて評価します。

## 評価結果取得

**エンドポイント**: `GET /api/v1/evaluations/{id}`

詳細は[設計書](../../design/03_api_specification.md)を参照してください。
