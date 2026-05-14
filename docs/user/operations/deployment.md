# デプロイメント

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## 本番環境推奨構成

### アプリケーション層

- **FastAPI**: 3インスタンス以上
- **ロードバランサー**: AWS ALB / Azure Application Gateway
- **オートスケーリング**: CPU/メモリベース

### データベース層

- **開発**: Supabase (PostgreSQL)
- **本番**: Databricks Delta Lake

### LLM層

- **Azure OpenAI**: プライベートエンドポイント推奨
- **レート制限**: 適切な設定

## Docker デプロイ

```bash
# イメージビルド
docker-compose build

# コンテナ起動
docker-compose up -d
```

## Kubernetes デプロイ

```bash
# マニフェスト適用
kubectl apply -f k8s/

# 状態確認
kubectl get pods
```

詳細は[設計書](../../design/07_deployment.md)を参照してください。
