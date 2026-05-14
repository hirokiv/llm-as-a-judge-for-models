# データベースセットアップガイド

このドキュメントでは、LLM-as-a-JudgeプロジェクトのSupabaseローカル環境のセットアップ方法を説明します。

## 前提条件

- Docker Desktopがインストールされ、起動していること
- Supabase CLIがインストールされていること（`brew install supabase/tap/supabase`）

## クイックスタート

### 方法1: 自動セットアップスクリプト（推奨）

```bash
# Dockerを起動してから実行
./scripts/setup_database.sh
```

このスクリプトは以下を自動実行します:
1. Dockerの起動確認
2. Supabaseローカル環境の起動
3. マイグレーション状態の確認
4. データベーススキーマの作成
5. 接続情報の表示

### 方法2: 手動セットアップ

#### Step 1: Supabase起動

```bash
supabase start
```

初回起動時はDockerイメージのダウンロードに数分かかります。

#### Step 2: マイグレーション実行

```bash
# マイグレーション状態確認
supabase migration list

# マイグレーション実行（データベースリセット）
supabase db reset
```

#### Step 3: 接続確認

```bash
supabase status
```

## 接続情報

Supabase起動後、以下の情報で接続できます:

### API接続（アプリケーション用）
```bash
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
```

### データベース直接接続（psql/DBeaver等）
```bash
postgresql://postgres:postgres@localhost:54322/postgres
```

### Studio UI（ブラウザ）
```
http://localhost:54323
```

## テーブル構成

### evaluation_results

Judge LLMの評価結果を保存するテーブル。

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | UUID | プライマリキー |
| mlflow_run_id | VARCHAR(255) | MLflow Run ID（一意） |
| test_case_id | VARCHAR(50) | テストケースID |
| system_output | TEXT | 対象AIシステムの出力 |
| is_safe | BOOLEAN | 安全判定 |
| risk_score | INTEGER | リスクスコア（1-5） |
| exploited_vectors | TEXT[] | 悪用されたベクトル |
| reasoning | TEXT | 判定理由 |
| recommendation | TEXT | 改善提案 |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

**制約**:
- `risk_score`: 1-5の範囲（CHECK制約）
- `mlflow_run_id`: UNIQUE制約

**インデックス**:
- `test_case_id`
- `mlflow_run_id`
- `created_at DESC`

### idempotency_checks

冪等性チェック結果を保存するテーブル。

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | UUID | プライマリキー |
| input_hash | VARCHAR(64) | 入力のSHA-256ハッシュ |
| model_version_key | VARCHAR(200) | モデルバージョンキー |
| provider | VARCHAR(50) | LLMプロバイダー |
| model_name | VARCHAR(100) | モデル名 |
| model_version | VARCHAR(50) | モデルバージョン |
| temperature | FLOAT | Temperature設定 |
| seed | INTEGER | Seed値 |
| prompt_version | VARCHAR(50) | プロンプトバージョン |
| test_case_id | VARCHAR(50) | テストケースID |
| is_idempotent | BOOLEAN | 冪等性判定 |
| variance_score | FLOAT | 一致度（0-1） |
| executions | JSONB | 各実行の詳細 |
| message | TEXT | チェック結果メッセージ |
| created_at | TIMESTAMP | 作成日時 |

**制約**:
- `variance_score`: 0-1の範囲（CHECK制約）
- `(model_version_key, input_hash)`: UNIQUE制約

**インデックス**:
- `input_hash`
- `model_version_key`
- `test_case_id`
- `created_at DESC`

## マイグレーションファイル

マイグレーションファイルは `supabase/migrations/` ディレクトリに配置されています:

```
supabase/migrations/
└── 20240514000000_initial_schema.sql  # 初期スキーマ定義
```

## トラブルシューティング

### Dockerが起動しない

```bash
# Dockerの状態確認
docker info

# Docker Desktopを再起動
# macOS: アプリケーション > Docker > Quit Docker Desktop → 再起動
```

### マイグレーションが失敗する

```bash
# Supabaseを停止して再起動
supabase stop
supabase start

# マイグレーションを再実行
supabase db reset
```

### ポートが使用中

Supabaseは以下のポートを使用します:
- 54321: API
- 54322: PostgreSQL
- 54323: Studio
- 54324: Inbucket（メール）

他のサービスがこれらのポートを使用している場合は停止してください。

```bash
# ポート使用状況確認
lsof -i :54321
lsof -i :54322
```

## データベース停止

```bash
# Supabaseローカル環境を停止
supabase stop

# データを削除して停止（完全リセット）
supabase stop --no-backup
```

## 次のステップ

データベースセットアップ完了後:

1. **接続テスト**: Repository層の動作確認
   ```bash
   pytest tests/integration/repositories/ -v
   ```

2. **アプリケーション起動**: FastAPIサーバー起動
   ```bash
   make run
   ```

3. **Studio UIでデータ確認**: http://localhost:54323

## 参考リンク

- [Supabase Local Development](https://supabase.com/docs/guides/cli/local-development)
- [Supabase Migrations](https://supabase.com/docs/guides/cli/managing-environments)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
