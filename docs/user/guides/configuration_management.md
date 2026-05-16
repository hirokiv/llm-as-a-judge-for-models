# Configuration Management Guide

## 概要

LLM-as-a-Judgeフレームワークは**ハイブリッド設定管理**をサポートしています：

- **YAML-only モード** - 既存の動作（シンプル、Gitで管理）
- **DB-first モード** - データベースベースの設定（動的変更、監査ログ）

## 設定モードの選択

### USE_DB_CONFIG 環境変数

設定モードは `USE_DB_CONFIG` 環境変数で制御します：

```bash
# .env ファイル

# YAML-only モード（デフォルト）
USE_DB_CONFIG=false

# DB-first モード
USE_DB_CONFIG=true
```

## YAML-only モード

### 特徴

✅ **シンプル** - 設定ファイルを直接編集
✅ **Gitで管理** - バージョン管理が容易
✅ **既存の動作** - 後方互換性を維持

### 使い方

1. **設定ファイルを編集**
   ```bash
   vim config/system_defaults.yaml
   vim config/judge_llm_configs.yaml
   vim config/target_ai_system.yaml
   vim config/test_cases/test_cases.yaml
   ```

2. **アプリケーションを再起動**
   ```bash
   make run
   ```

### 利用シーン

- 開発環境
- 小規模なデプロイ
- シンプルな設定管理

## DB-first モード

### 特徴

✅ **動的変更** - 再起動なしで設定を更新
✅ **環境別管理** - development/staging/production ごとに設定
✅ **監査ログ** - すべての設定変更を記録
✅ **安全性** - YAMLフォールバックで障害時も稼働

### セットアップ

1. **データベースマイグレーション**
   ```bash
   make db-migrate
   ```

2. **設定データをシード**
   ```bash
   # 初回シード
   make db-seed

   # 強制上書き（既存データを更新）
   make db-seed-force
   ```

3. **シード確認**
   ```bash
   make db-verify
   ```

4. **USE_DB_CONFIG を有効化**
   ```bash
   echo "USE_DB_CONFIG=true" >> .env
   ```

### 設定更新方法

#### 方法1: YAMLを編集して再シード

```bash
# 1. YAMLファイルを編集
vim config/system_defaults.yaml

# 2. データベースに再シード
make db-seed-force

# 3. 即座に反映（再起動不要）
```

#### 方法2: データベースを直接更新

**Supabase Studio UI**:
1. http://localhost:54323 にアクセス
2. `system_configs`, `judge_llm_configs` 等のテーブルを編集
3. 即座に反映

**SQL クエリ**:
```sql
-- システム設定を更新
UPDATE system_configs
SET value = '9000'
WHERE config_key = 'application.api.port'
  AND environment = 'production';

-- Judge LLM設定を更新
UPDATE judge_llm_configs
SET temperature = 0.1
WHERE name = 'production';
```

### 利用シーン

- 本番環境
- ステージング環境
- 複数インスタンスのデプロイ
- A/Bテスト
- 緊急設定変更

## データベーススキーマ

### system_configs テーブル

フラット化された階層構造の設定：

| カラム | 型 | 説明 | 例 |
|--------|-----|------|-----|
| config_key | VARCHAR | ドット区切りキー | `application.api.port` |
| value | TEXT | 設定値 | `8000` |
| value_type | VARCHAR | 値の型 | `integer` |
| environment | VARCHAR | 環境名 | `production` |
| is_active | BOOLEAN | アクティブフラグ | `true` |

**例**:
```
config_key: "application.api.port"
value: "8000"
value_type: "integer"
environment: "production"
```

↓ アプリケーションで自動的に変換 ↓

```yaml
application:
  api:
    port: 8000
```

### target_ai_systems テーブル

プロキシターゲット設定：

| カラム | 型 | 説明 |
|--------|-----|------|
| name | VARCHAR | システム名 |
| url | TEXT | エンドポイントURL |
| headers | JSONB | 認証ヘッダー |
| request_config | JSONB | リクエスト設定 |
| response_config | JSONB | レスポンスパーサー設定 |

### evaluation_criteria テーブル

Rubric評価基準：

| カラム | 型 | 説明 |
|--------|-----|------|
| name | VARCHAR | 基準名 |
| version | VARCHAR | バージョン |
| hard_rules | JSONB | Hard Rules定義 |
| soft_judge_criteria | JSONB | Rubric評価項目 |
| risk_score_config | JSONB | リスクスコア計算ルール |

### test_cases テーブル

テストケース定義：

| カラム | 型 | 説明 |
|--------|-----|------|
| id | VARCHAR | テストケースID |
| name | VARCHAR | テストケース名 |
| input_text | TEXT | 入力テキスト |
| expected_safe_behavior | TEXT | 期待される安全な動作 |
| risk_level | INTEGER | リスクレベル (1-5) |

## トラブルシューティング

### 設定が反映されない

**問題**: 設定を変更したが反映されない

**解決策**:
1. `USE_DB_CONFIG` 環境変数を確認
   ```bash
   echo $USE_DB_CONFIG
   ```

2. データベース接続を確認
   ```bash
   make db-test
   ```

3. ログを確認
   ```bash
   # "Loading ... from database" または "Falling back to YAML" メッセージを確認
   tail -f logs/app.log
   ```

### データベースシードが失敗する

**問題**: `make db-seed` が失敗する

**解決策**:
1. マイグレーションが適用されているか確認
   ```bash
   make db-migrate
   ```

2. データベース接続情報を確認
   ```bash
   make check-env
   ```

3. YAMLファイルの構文エラーを確認
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/system_defaults.yaml'))"
   ```

### YAMLフォールバックの動作確認

**デバッグログを有効化**:
```bash
# .env
LOG_LEVEL=DEBUG
```

**ログ確認**:
```
INFO: Loading system defaults from database environment=default
WARNING: No system configs found in database, falling back to YAML
DEBUG: Loading system defaults from YAML (USE_DB_CONFIG=false)
```

## ベストプラクティス

### 1. 段階的ロールアウト

```
Week 1: Development環境でDB-first
Week 2: Staging環境でDB-first
Week 3: Production環境でDB-first
```

### 2. 設定変更の監査

すべての設定変更はデータベースの `updated_at` カラムで追跡されます：

```sql
SELECT config_key, value, updated_at
FROM system_configs
WHERE updated_at > NOW() - INTERVAL '7 days'
ORDER BY updated_at DESC;
```

### 3. 環境別設定の管理

```bash
# Development
make db-seed  # environment=default

# Staging
USE_DB_CONFIG=true ENVIRONMENT=staging make db-seed

# Production
USE_DB_CONFIG=true ENVIRONMENT=production make db-seed
```

### 4. バックアップ

定期的にデータベースをバックアップ：

```bash
# PostgreSQL dump
pg_dump -h localhost -U postgres -d llm_judge > backup.sql

# Supabaseの場合、自動バックアップが有効
```

## まとめ

| 機能 | YAML-only | DB-first |
|------|-----------|----------|
| 動的変更 | ❌ | ✅ |
| Gitバージョン管理 | ✅ | ⚠️ (間接的) |
| 環境別設定 | ⚠️ (手動) | ✅ |
| 監査ログ | ❌ | ✅ |
| 複数インスタンス | ❌ | ✅ |
| シンプルさ | ✅ | ⚠️ |
| 障害時の安全性 | ⚠️ | ✅ (fallback) |

**推奨**:
- **開発環境**: YAML-only モード
- **本番環境**: DB-first モード
