# 認証

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## JWT認証

すべてのAPIエンドポイントはJWT（JSON Web Token）認証が必要です。

### トークンの取得

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-username",
    "password": "your-password"
  }'
```

### レスポンス

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### トークンの使用

```bash
curl -X GET http://localhost:8000/api/v1/test-cases \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## ロールベースアクセス制御（RBAC）

以下の3つのロールがあります：

- **admin**: すべての操作が可能
- **evaluator**: 評価の実行と結果の参照
- **viewer**: 結果の参照のみ

詳細は[設計書](../../design/04_authentication.md)を参照してください。
