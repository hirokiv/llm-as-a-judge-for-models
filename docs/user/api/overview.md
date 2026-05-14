# API 概要

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## REST API

LLM-as-a-Judge for Enterprise SystemsはRESTful APIを提供します。

### ベースURL

```
http://localhost:8000/api/v1
```

### 認証

すべてのAPIエンドポイントはJWT認証が必要です。

```bash
Authorization: Bearer YOUR_JWT_TOKEN
```

### エンドポイント一覧

#### 評価API
- `POST /evaluate` - 単一評価実行
- `POST /evaluate/batch` - バッチ評価実行
- `GET /evaluations` - 評価結果一覧
- `GET /evaluations/{id}` - 評価結果詳細
- `POST /evaluations/{id}/verify-idempotency` - 冪等性検証

#### テストケース管理API
- `GET /test-cases` - テストケース一覧
- `POST /test-cases` - テストケース作成
- `GET /test-cases/{id}` - テストケース詳細
- `PUT /test-cases/{id}` - テストケース更新
- `DELETE /test-cases/{id}` - テストケース削除

#### Judge LLM設定API
- `GET /judge-llm-configs` - 設定一覧
- `POST /judge-llm-configs` - 設定作成
- その他（詳細は設計書参照）

### レスポンス形式

すべてのレスポンスはJSON形式です。

#### 成功レスポンス

```json
{
  "data": { ... },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

#### エラーレスポンス

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "エラーメッセージ",
    "details": { ... }
  }
}
```

## 次のステップ

- [認証](authentication.md)
- [評価 API](evaluate.md)
- [テストケース管理 API](test-cases.md)
