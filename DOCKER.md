# Docker環境構築ガイド

## 概要

このプロジェクトはDockerコンテナ化されており、以下の3つのサービスで構成されています：

- **app**: FastAPI アプリケーション
- **postgres**: Supabase PostgreSQL データベース
- **mlflow**: MLflow トラッキングサーバー

## クイックスタート

### 本番環境（Production）

```bash
# ビルドと起動
docker-compose up -d

# ログ確認
docker-compose logs -f app

# 停止
docker-compose down

# データボリュームも削除
docker-compose down -v
```

### 開発環境（Development with Hot-Reload）

```bash
# ビルドと起動
docker-compose -f docker-compose.dev.yml up -d

# ログ確認
docker-compose -f docker-compose.dev.yml logs -f app

# 停止
docker-compose -f docker-compose.dev.yml down
```

## 環境変数

`.env`ファイルを作成して環境変数を設定：

```bash
# .env ファイル例
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
POSTGRES_PASSWORD=secure-password-here
LOG_LEVEL=INFO
DEBUG=False
```

## サービスアクセス

起動後、以下のURLでアクセス可能：

- **FastAPI アプリケーション**: http://localhost:8000
- **FastAPI ドキュメント**: http://localhost:8000/docs
- **MLflow UI**: http://localhost:5000
- **PostgreSQL**: localhost:5432

## ヘルスチェック

```bash
# アプリケーションヘルスチェック
curl http://localhost:8000/health

# MLflowヘルスチェック
curl http://localhost:5000/health
```

## トラブルシューティング

### ポート競合エラー

ポートが既に使用されている場合：

```bash
# ポート使用状況確認
lsof -i :8000
lsof -i :5000
lsof -i :5432

# docker-compose.yml のポート番号を変更
ports:
  - "8001:8000"  # 8000 -> 8001 に変更
```

### ビルドエラー

キャッシュをクリアして再ビルド：

```bash
docker-compose build --no-cache
docker-compose up -d
```

### データベース接続エラー

データベースが完全に起動するまで待機：

```bash
# データベースログ確認
docker-compose logs postgres

# ヘルスチェック確認
docker-compose ps
```

## コンテナ内での作業

### アプリケーションコンテナに入る

```bash
docker-compose exec app /bin/bash

# または開発環境
docker-compose -f docker-compose.dev.yml exec app /bin/bash
```

### データベースに接続

```bash
docker-compose exec postgres psql -U postgres -d llm_judge
```

### MLflowコマンド実行

```bash
docker-compose exec mlflow mlflow --help
```

## ボリューム管理

### データボリューム確認

```bash
docker volume ls | grep llm-judge
```

### データバックアップ

```bash
# PostgreSQL データ
docker-compose exec postgres pg_dump -U postgres llm_judge > backup.sql

# MLflow データ
docker-compose exec mlflow tar czf /tmp/mlflow-backup.tar.gz /mlflow
docker cp llm-judge-mlflow:/tmp/mlflow-backup.tar.gz ./mlflow-backup.tar.gz
```

### データリストア

```bash
# PostgreSQL データ
cat backup.sql | docker-compose exec -T postgres psql -U postgres llm_judge
```

## 開発ワークフロー

### ホットリロード開発

1. 開発環境を起動：
```bash
docker-compose -f docker-compose.dev.yml up -d
```

2. ローカルで `src/` を編集

3. 変更が自動的にコンテナに反映される（uvicorn --reload）

### テスト実行

```bash
# コンテナ内でテスト実行
docker-compose -f docker-compose.dev.yml exec app .venv/bin/pytest tests/unit/ -v
```

### リント・フォーマット

```bash
docker-compose -f docker-compose.dev.yml exec app .venv/bin/ruff check src/
docker-compose -f docker-compose.dev.yml exec app .venv/bin/mypy src/
```

## 本番デプロイ

### イメージのビルドとプッシュ

```bash
# イメージビルド
docker build -t llm-judge-api:latest .

# タグ付け
docker tag llm-judge-api:latest your-registry.com/llm-judge-api:latest

# プッシュ
docker push your-registry.com/llm-judge-api:latest
```

### Kubernetes デプロイ

Kubernetes マニフェストは `k8s/` ディレクトリを参照。

## セキュリティ

### 本番環境での注意事項

- [ ] `.env` ファイルを`.gitignore`に追加
- [ ] POSTGRES_PASSWORD を強力なパスワードに変更
- [ ] OPENAI_API_KEY などのシークレットは環境変数で管理
- [ ] 非rootユーザーでコンテナを実行（Dockerfileで設定済み）
- [ ] ヘルスチェックを有効化（設定済み）

## 参考資料

- [Docker Compose ドキュメント](https://docs.docker.com/compose/)
- [FastAPI デプロイ](https://fastapi.tiangolo.com/deployment/)
- [MLflow ドキュメント](https://mlflow.org/docs/latest/index.html)
