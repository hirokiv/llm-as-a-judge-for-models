# テストケース管理 API

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## テストケース一覧取得

**エンドポイント**: `GET /api/v1/test-cases`

### クエリパラメータ

- `category`: カテゴリでフィルター
- `severity`: 深刻度でフィルター
- `skip`: オフセット
- `limit`: 取得件数

## テストケース作成

**エンドポイント**: `POST /api/v1/test-cases`

### リクエスト

```json
{
  "test_case_id": "TEST-LT-001",
  "category": "prompt_injection",
  "prompt": "テストプロンプト",
  "expected_behavior": "拒否",
  "risk_category": "confidential_data_access",
  "severity": 5
}
```

## テストケース更新・削除

- **更新**: `PUT /api/v1/test-cases/{id}`
- **削除**: `DELETE /api/v1/test-cases/{id}`

詳細は[設計書](../../design/03_api_specification.md)を参照してください。
