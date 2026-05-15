# デプロイメント

本番環境へのデプロイ方法を説明します。

---

## デプロイ方法

### 🐳 Docker Compose（ローカル/小規模）

**用途**: ローカル開発、小規模テスト環境

```bash
# 起動
docker-compose up -d

# 停止
docker-compose down
```

詳細: **[Docker環境構築ガイド](docker-setup.md)**

---

### ☸️ Kubernetes（本番環境推奨）

**用途**: 本番環境、スケーラブルな運用

```bash
# デプロイ
kubectl apply -k k8s/overlays/production

# 状態確認
kubectl get pods -n production
```

詳細: **[本番デプロイメントガイド](deployment-full.md)**

---

## 本番環境推奨構成

### アプリケーション層
- **FastAPI**: 3インスタンス以上
- **ロードバランサー**: AWS ALB / Azure Application Gateway
- **オートスケーリング**: CPU使用率70%でスケール

### データベース層
- **開発**: Supabase (PostgreSQL)
- **本番**: Databricks Delta Lake

### LLM層
- **Azure OpenAI**: プライベートエンドポイント推奨
- **レート制限**: 100 req/min

### モニタリング
- **Prometheus**: メトリクス収集
- **Grafana**: ダッシュボード
- **MLflow**: 評価追跡

---

## クイックスタート

### 1. Docker Composeで即座に起動

```bash
# リポジトリクローン
git clone https://github.com/your-org/llm-as-a-judge-for-models.git
cd llm-as-a-judge-for-models

# 環境変数設定
cp .env.example .env
vim .env  # APIキー等を設定

# 起動
docker-compose up -d

# アクセス
curl http://localhost:8000/health
```

詳細: [Docker環境構築ガイド](docker-setup.md)

### 2. Kubernetesで本番デプロイ

```bash
# Secretsセットアップ
kubectl create secret generic llm-judge-secrets \
  --from-literal=azure-openai-api-key='YOUR_KEY' \
  --namespace=production

# デプロイ
kubectl apply -k k8s/overlays/production

# 確認
kubectl get pods -n production
kubectl logs -f deployment/llm-judge-api -n production
```

詳細: [本番デプロイメントガイド](deployment-full.md)

---

## 環境別設定

| 環境 | Docker Compose | Kubernetes | LLM Provider | Database |
|------|---------------|-----------|--------------|----------|
| **ローカル開発** | `docker-compose.dev.yml` | - | OpenAI | Supabase |
| **ステージング** | - | `k8s/overlays/staging` | Azure OpenAI | Supabase |
| **本番** | - | `k8s/overlays/production` | Azure OpenAI | Databricks |

---

## ヘルスチェック

すべての環境で `/health` エンドポイントが利用可能です:

```bash
# ローカル
curl http://localhost:8000/health

# 本番
curl https://api.llm-judge.example.com/health
```

期待されるレスポンス:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "mlflow": "connected",
    "llm_provider": "available"
  }
}
```

---

## トラブルシューティング

### ポート競合

```bash
# 使用中のポートを確認
lsof -i :8000
lsof -i :5000

# docker-compose.ymlのポート番号を変更
ports:
  - "8001:8000"
```

### コンテナが起動しない

```bash
# ログ確認
docker-compose logs -f app

# 再ビルド
docker-compose build --no-cache
docker-compose up -d
```

### Kubernetes Pod がCrashLoop

```bash
# Pod詳細確認
kubectl describe pod <pod-name> -n production

# ログ確認
kubectl logs <pod-name> -n production --previous

# よくある原因:
# - Secrets未設定
# - データベース接続エラー
# - APIキー不正
```

---

## 次のステップ

- **[Docker環境構築ガイド](docker-setup.md)** - 開発環境のセットアップ
- **[本番デプロイメントガイド](deployment-full.md)** - Kubernetes本番デプロイ詳細
- **[設計書: デプロイ](../../design/07_deployment.md)** - アーキテクチャ設計

---

## サポート

問題が発生した場合:

1. ログを確認（`docker-compose logs` または `kubectl logs`）
2. ヘルスチェックを実行（`/health`エンドポイント）
3. [GitHub Issues](https://github.com/your-org/llm-as-a-judge-for-models/issues)に報告

---

**最終更新**: 2026-05-15
