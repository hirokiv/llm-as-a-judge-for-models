# Kubernetes Deployment Guide

## 概要

LLM-as-a-Judge システムのKubernetesデプロイメント設定。

## 前提条件

- Kubernetes cluster (v1.24+)
- kubectl CLI tool
- kustomize (v4.5+) or kubectl with built-in kustomize
- NGINX Ingress Controller (オプション)
- cert-manager (TLS証明書管理用、オプション)

## ディレクトリ構造

```
k8s/
├── base/                    # ベース設定（環境非依存）
│   ├── deployment.yaml      # Deployment定義
│   ├── service.yaml         # Service定義
│   ├── configmap.yaml       # ConfigMap定義
│   ├── ingress.yaml         # Ingress定義
│   ├── secret.yaml.template # Secret テンプレート
│   └── kustomization.yaml   # Kustomize設定
├── overlays/
│   ├── staging/             # ステージング環境
│   │   └── kustomization.yaml
│   └── production/          # 本番環境
│       ├── kustomization.yaml
│       ├── deployment-patch.yaml
│       └── ingress-patch.yaml
└── README.md
```

## クイックスタート

### 1. Namespace作成

```bash
# Production
kubectl create namespace production

# Staging
kubectl create namespace staging
```

### 2. Secretsの作成

**重要**: Secretsはgitにコミットしないこと！

```bash
# Production環境のSecrets作成
kubectl create secret generic llm-judge-secrets \
  --from-literal=azure-openai-api-key='YOUR_AZURE_KEY' \
  --from-literal=azure-openai-endpoint='https://your-resource.openai.azure.com' \
  --from-literal=databricks-server-hostname='your-workspace.cloud.databricks.com' \
  --from-literal=databricks-http-path='/sql/1.0/warehouses/xxxxx' \
  --from-literal=databricks-access-token='YOUR_DATABRICKS_TOKEN' \
  --namespace=production

# Staging環境のSecrets作成
kubectl create secret generic llm-judge-secrets \
  --from-literal=openai-api-key='YOUR_OPENAI_KEY' \
  --from-literal=supabase-url='https://xxx.supabase.co' \
  --from-literal=supabase-key='YOUR_SUPABASE_KEY' \
  --namespace=staging
```

### 3. デプロイ

#### Staging環境

```bash
# kustomize経由でデプロイ
kubectl apply -k k8s/overlays/staging

# または kustomize コマンド
kustomize build k8s/overlays/staging | kubectl apply -f -
```

#### Production環境

```bash
# kustomize経由でデプロイ
kubectl apply -k k8s/overlays/production

# または kustomize コマンド
kustomize build k8s/overlays/production | kubectl apply -f -
```

## 動作確認

### Pod状態確認

```bash
# Production
kubectl get pods -n production
kubectl logs -f deployment/llm-judge-api -n production

# Staging
kubectl get pods -n staging
kubectl logs -f deployment/llm-judge-api -n staging
```

### Service確認

```bash
kubectl get svc -n production
kubectl get ingress -n production
```

### ヘルスチェック

```bash
# Port-forward経由でヘルスチェック
kubectl port-forward -n production svc/llm-judge-api-service 8080:80
curl http://localhost:8080/health
```

## スケーリング

### 手動スケーリング

```bash
# Replica数を変更
kubectl scale deployment llm-judge-api --replicas=10 -n production
```

### Horizontal Pod Autoscaler (HPA)

```bash
# CPU使用率ベースの自動スケーリング
kubectl autoscale deployment llm-judge-api \
  --cpu-percent=70 \
  --min=3 \
  --max=20 \
  -n production
```

## ローリングアップデート

### 新しいバージョンのデプロイ

```bash
# イメージタグを更新
kubectl set image deployment/llm-judge-api \
  api=ghcr.io/your-org/llm-judge-api:v1.2.3 \
  -n production

# ロールアウト状態確認
kubectl rollout status deployment/llm-judge-api -n production
```

### ロールバック

```bash
# 前のバージョンに戻す
kubectl rollout undo deployment/llm-judge-api -n production

# 特定のリビジョンに戻す
kubectl rollout undo deployment/llm-judge-api --to-revision=2 -n production

# ロールアウト履歴確認
kubectl rollout history deployment/llm-judge-api -n production
```

## トラブルシューティング

### Podが起動しない

```bash
# Pod詳細確認
kubectl describe pod <pod-name> -n production

# ログ確認
kubectl logs <pod-name> -n production

# 前のコンテナのログ確認（CrashLoopBackOff時）
kubectl logs <pod-name> -n production --previous
```

### Secretsが見つからない

```bash
# Secret存在確認
kubectl get secrets -n production

# Secret内容確認（base64エンコード済み）
kubectl get secret llm-judge-secrets -n production -o yaml
```

### Ingressが機能しない

```bash
# Ingress確認
kubectl describe ingress llm-judge-api-ingress -n production

# Ingress Controller確認
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

## セキュリティベストプラクティス

### 1. Secrets管理

本番環境では、KubernetesのSecretsではなく、外部Secret Managerを使用することを推奨：

- **AWS**: AWS Secrets Manager + External Secrets Operator
- **Azure**: Azure Key Vault + External Secrets Operator
- **GCP**: Google Secret Manager + External Secrets Operator

```bash
# External Secrets Operatorのインストール例
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace
```

### 2. NetworkPolicy

```yaml
# 例: APIポッドへのアクセス制限
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: llm-judge-api-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: llm-judge-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: mlflow
    ports:
    - protocol: TCP
      port: 5000
```

### 3. RBAC

最小権限の原則に従ったServiceAccountとRoleBindingの設定。

### 4. Pod Security Standards

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## モニタリング

### Prometheus メトリクス収集

```bash
# ServiceMonitor作成（Prometheus Operator使用時）
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: llm-judge-api
  namespace: production
spec:
  selector:
    matchLabels:
      app: llm-judge-api
  endpoints:
  - port: http
    path: /metrics
EOF
```

### Grafana Dashboard

MLflow UIと統合したGrafanaダッシュボードを推奨。

## バックアップ

### ConfigMap/Secretsバックアップ

```bash
# 全リソースをYAMLでエクスポート
kubectl get all,configmaps,secrets -n production -o yaml > backup-production.yaml
```

## クリーンアップ

```bash
# Staging環境削除
kubectl delete -k k8s/overlays/staging

# Production環境削除
kubectl delete -k k8s/overlays/production

# Namespace削除
kubectl delete namespace staging production
```

## 参考資料

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [cert-manager](https://cert-manager.io/)
