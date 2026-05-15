# デプロイメントガイド

## 概要

本ドキュメントは、LLM-as-a-Judgeシステムの本番環境へのデプロイ手順を説明します。

## デプロイメント前提条件

### 必須要件

- [x] Kubernetes cluster (v1.24+)
- [x] kubectl CLI
- [x] Docker registry access (GitHub Container Registry)
- [x] Azure OpenAI リソース
- [x] Databricks ワークスペース
- [x] MLflow トラッキングサーバー

### オプション要件

- [ ] NGINX Ingress Controller
- [ ] cert-manager (TLS証明書管理)
- [ ] External Secrets Operator
- [ ] Prometheus/Grafana (monitoring)

## デプロイメント手順

### Phase 1: インフラ準備

#### 1.1 Azure OpenAI セットアップ

```bash
# Azure CLI でリソース作成
az cognitiveservices account create \
  --name llm-judge-openai \
  --resource-group llm-judge-prod \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# デプロイメント作成
az cognitiveservices account deployment create \
  --name llm-judge-openai \
  --resource-group llm-judge-prod \
  --deployment-name gpt-4 \
  --model-name gpt-4 \
  --model-version 0613 \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard
```

#### 1.2 Databricks セットアップ

1. Databricks ワークスペース作成
2. SQL Warehouse 作成
3. Catalog とSchema 作成:

```sql
CREATE CATALOG IF NOT EXISTS llm_judge_prod;
CREATE SCHEMA IF NOT EXISTS llm_judge_prod.evaluations;

-- テーブル作成（リポジトリが自動作成）
```

4. アクセストークン生成

#### 1.3 Kubernetes Cluster セットアップ

```bash
# AKS (Azure Kubernetes Service) 例
az aks create \
  --resource-group llm-judge-prod \
  --name llm-judge-cluster \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-managed-identity \
  --generate-ssh-keys

# kubeconfig 取得
az aks get-credentials \
  --resource-group llm-judge-prod \
  --name llm-judge-cluster
```

### Phase 2: Secrets 管理

#### 2.1 Kubernetes Secrets 作成

```bash
# Production namespace 作成
kubectl create namespace production

# Secrets 作成
kubectl create secret generic llm-judge-secrets \
  --from-literal=azure-openai-api-key='YOUR_AZURE_OPENAI_KEY' \
  --from-literal=azure-openai-endpoint='https://llm-judge-openai.openai.azure.com' \
  --from-literal=databricks-server-hostname='your-workspace.cloud.databricks.com' \
  --from-literal=databricks-http-path='/sql/1.0/warehouses/xxxxx' \
  --from-literal=databricks-access-token='YOUR_DATABRICKS_TOKEN' \
  --namespace=production
```

#### 2.2 External Secrets Operator (推奨)

```bash
# Azure Key Vault 統合
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: azure-backend
  namespace: production
spec:
  provider:
    azurekv:
      authType: ManagedIdentity
      vaultUrl: https://llm-judge-kv.vault.azure.net/
EOF
```

### Phase 3: アプリケーションデプロイ

#### 3.1 Docker イメージビルド & プッシュ

```bash
# ローカルでビルド
docker build -t ghcr.io/your-org/llm-judge-api:v1.0.0 .

# プッシュ
docker push ghcr.io/your-org/llm-judge-api:v1.0.0
```

#### 3.2 Kubernetes デプロイ

```bash
# Kustomize でデプロイ
kubectl apply -k k8s/overlays/production

# デプロイ状態確認
kubectl rollout status deployment/llm-judge-api -n production

# Pod 確認
kubectl get pods -n production
```

### Phase 4: Ingress & TLS セットアップ

#### 4.1 NGINX Ingress Controller インストール

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

#### 4.2 cert-manager インストール

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Let's Encrypt Issuer 作成
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### Phase 5: モニタリング設定

#### 5.1 Prometheus & Grafana

```bash
# Prometheus Operator インストール
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

#### 5.2 ダッシュボード設定

- MLflow UI: `https://mlflow.production.example.com`
- Grafana: `https://grafana.production.example.com`
- Prometheus: `https://prometheus.production.example.com`

### Phase 6: CI/CD パイプライン設定

#### 6.1 GitHub Secrets 設定

GitHub リポジトリの Settings > Secrets and variables > Actions で以下を設定:

- `KUBE_CONFIG_PRODUCTION`: base64エンコードされた kubeconfig
- `KUBE_CONFIG_STAGING`: base64エンコードされた kubeconfig (staging用)

```bash
# kubeconfig を base64 エンコード
cat ~/.kube/config | base64
```

#### 6.2 GitHub Actions 有効化

`.github/workflows/cd.yml` が自動的にデプロイを実行:

- `develop` ブランチ → Staging 環境
- `main` ブランチ → Production 環境
- `v*` タグ → Production 環境（バージョンタグ付き）

## デプロイメント検証

### 1. ヘルスチェック

```bash
# Port-forward 経由
kubectl port-forward -n production svc/llm-judge-api-service 8080:80
curl http://localhost:8080/health

# または Ingress 経由
curl https://api.llm-judge.production.example.com/health
```

期待される出力:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "mlflow": "connected",
    "llm_provider": "available"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 2. 評価API テスト

```bash
curl -X POST https://api.llm-judge.production.example.com/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "TEST-LT-001",
    "system_output": "テスト出力"
  }'
```

### 3. ログ確認

```bash
# アプリケーションログ
kubectl logs -f deployment/llm-judge-api -n production

# 直近のエラーログ
kubectl logs deployment/llm-judge-api -n production | grep ERROR
```

## トラブルシューティング

### Pod が CrashLoopBackOff

```bash
# Pod 詳細確認
kubectl describe pod <pod-name> -n production

# ログ確認
kubectl logs <pod-name> -n production --previous

# よくある原因:
# - Secrets が設定されていない
# - Databricks 接続エラー
# - Azure OpenAI API キー不正
```

### データベース接続エラー

```bash
# Databricks 接続テスト
kubectl exec -it deployment/llm-judge-api -n production -- \
  python -c "from src.repositories import get_repository; repo = get_repository(); print('Connection OK')"
```

### メモリ不足

```bash
# リソース使用状況確認
kubectl top pods -n production

# リソースリミット増加
kubectl set resources deployment llm-judge-api \
  --limits=memory=2Gi,cpu=2000m \
  --requests=memory=1Gi,cpu=1000m \
  -n production
```

## ロールバック手順

### 1. 前のバージョンにロールバック

```bash
# ロールバック
kubectl rollout undo deployment/llm-judge-api -n production

# 状態確認
kubectl rollout status deployment/llm-judge-api -n production
```

### 2. 特定のリビジョンに戻す

```bash
# リビジョン履歴確認
kubectl rollout history deployment/llm-judge-api -n production

# 特定のリビジョンに戻す
kubectl rollout undo deployment/llm-judge-api --to-revision=3 -n production
```

## セキュリティチェックリスト

- [ ] すべてのSecretsが環境変数経由で設定されている
- [ ] HTTPS (TLS) が有効化されている
- [ ] RBAC が適切に設定されている
- [ ] NetworkPolicy が設定されている
- [ ] Pod Security Standards が適用されている
- [ ] レート制限が設定されている
- [ ] ログに機密情報が含まれていない
- [ ] イメージスキャンが実行されている

## パフォーマンスチューニング

### Horizontal Pod Autoscaler

```bash
kubectl autoscale deployment llm-judge-api \
  --cpu-percent=70 \
  --min=3 \
  --max=20 \
  -n production
```

### Vertical Pod Autoscaler (VPA)

```bash
# VPA インストール
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler
./hack/vpa-up.sh
```

## バックアップ & ディザスタリカバリ

### 1. データベースバックアップ

Databricks の自動バックアップ機能を使用。

### 2. 設定バックアップ

```bash
# 全リソースをバックアップ
kubectl get all,configmaps,secrets,ingress -n production -o yaml > backup-$(date +%Y%m%d).yaml
```

### 3. MLflow アーティファクトバックアップ

Azure Blob Storage または S3 にアーティファクトを保存。

## コスト最適化

- Spot インスタンス / Preemptible VMs の活用
- 非ピーク時のオートスケーリング設定
- リソースリミットの適切な設定
- 不要なログの削減

## サポート

問題が発生した場合:

1. ログを確認
2. ヘルスチェックを実行
3. GitHub Issues に報告

---

**最終更新**: 2024-01-01
**バージョン**: 1.0.0
