# MLflow Native Autologging Guide

## 概要

LLM-as-a-Judgeフレームワークは**MLflow Native Autologging**を実装しており、LLM呼び出しを**完全自動で追跡**します。

追加設定やコード変更は一切不要で、以下の情報が自動的に記録されます：

- ✅ **トークン使用量** - input/output トークン数の詳細
- ✅ **コスト推定** - 使用量に基づくコスト計算
- ✅ **レイテンシ** - LLM呼び出しの応答時間
- ✅ **LLM入出力** - プロンプトとレスポンスの完全な記録
- ✅ **エラー追跡** - 失敗したリクエストの詳細

## 自動有効化

MLflow Autologgingは**デフォルトで有効化**されており、追加設定は不要です。

### 自動検出

`LLM_PROVIDER` 環境変数に基づいて、適切なautologgingが自動的に有効化されます：

```bash
# .env ファイル

# OpenAI の場合
LLM_PROVIDER=openai

# Azure OpenAI の場合
LLM_PROVIDER=azure_openai

# Anthropic の場合
LLM_PROVIDER=anthropic
```

### サポートプロバイダー

| プロバイダー | LLM_PROVIDER値 | Autologging |
|-------------|----------------|-------------|
| OpenAI | `openai` | ✅ mlflow.openai.autolog() |
| Azure OpenAI | `azure_openai` | ✅ mlflow.openai.autolog() |
| Anthropic | `anthropic` | ✅ mlflow.anthropic.autolog() |

## 記録される情報

### 1. メトリクス（自動）

**トークン使用量**:
- `total_tokens` - 合計トークン数
- `prompt_tokens` - 入力トークン数
- `completion_tokens` - 出力トークン数

**コスト**:
- `cost_usd` - 推定コスト（USD）

**パフォーマンス**:
- `latency_ms` - レイテンシ（ミリ秒）
- `requests_per_second` - スループット

### 2. パラメータ（自動）

**モデル情報**:
- `model` - 使用モデル（例: `gpt-4`, `claude-3-opus`）
- `temperature` - 温度パラメータ
- `max_tokens` - 最大トークン数

**設定**:
- `provider` - LLMプロバイダー
- `api_version` - APIバージョン

### 3. アーティファクト（自動）

**LLM入出力**:
- `inputs/` - プロンプト全文
- `outputs/` - レスポンス全文
- `messages.json` - 完全なメッセージ履歴

## MLflow UI での確認

### ステップ1: MLflowサーバー起動

```bash
# Makefileコマンドで起動
make mlflow

# または直接起動
mlflow server --host 127.0.0.1 --port 5555
```

### ステップ2: UIにアクセス

```bash
open http://localhost:5555
```

### ステップ3: 実験を確認

1. **Experiments** → `llm-judge-evaluations` を選択
2. 任意の**Run**をクリック
3. 以下のタブで情報を確認：

#### Metrics タブ

自動記録されたメトリクスを表示：

```
total_tokens: 523
prompt_tokens: 450
completion_tokens: 73
cost_usd: 0.0156
latency_ms: 1234
```

#### Parameters タブ

LLM設定を表示：

```
model: gpt-4
temperature: 0
max_tokens: 1000
provider: openai
```

#### Artifacts タブ

LLM入出力を表示：

```
inputs/
  └── messages.json
outputs/
  └── response.json
```

### ステップ4: コスト分析

**合計コスト確認**:
1. **Experiments** → `llm-judge-evaluations`
2. **Columns** → `Metrics` → `cost_usd` を追加
3. 全Runのコストが一覧表示される

**時系列グラフ**:
1. 任意のRun → **Metrics** タブ
2. `cost_usd` をクリック
3. 時系列グラフでコスト推移を確認

## 手動ロギングとの共存

MLflow Autologgingは**既存の手動ロギングと共存**します。

### ハイブリッドアプローチ

```python
# 自動記録（autologging）
# ✅ トークン使用量
# ✅ レイテンシ
# ✅ コスト
# ✅ LLM入出力

# 手動記録（既存実装）
# ✅ リスクスコア（risk_score）
# ✅ Rubric評価スコア
# ✅ Hard Rules違反数
# ✅ カスタムメトリクス
```

### メリット

| 機能 | Autologging | 手動ロギング |
|------|-------------|-------------|
| トークン・コスト | ✅ 自動 | - |
| LLM入出力 | ✅ 完全 | ⚠️ 部分的 |
| リスクスコア | - | ✅ カスタム |
| Rubric評価 | - | ✅ カスタム |
| 設定不要 | ✅ | ❌ |

**両方のメリットを享受**できます！

## 無効化（オプション）

特定の理由でautologgingを無効化する場合：

```python
# src/services/mlflow_tracker.py

tracker = MLflowTrackerService(
    enable_autolog=False  # autologging を無効化
)
```

または環境変数で制御：

```bash
# .env
MLFLOW_AUTOLOG_ENABLED=false
```

## トラブルシューティング

### Autologgingが動作しない

**問題**: メトリクスが記録されない

**解決策**:

1. **LLM_PROVIDER確認**:
   ```bash
   echo $LLM_PROVIDER
   # openai, azure_openai, anthropic のいずれか
   ```

2. **MLflowバージョン確認**:
   ```bash
   pip show mlflow
   # Version: 2.9.0 以上が必要
   ```

3. **ログ確認**:
   ```bash
   tail -f logs/app.log | grep autolog
   # "Enabled MLflow autologging for OpenAI" が表示されるはず
   ```

### コストが記録されない

**問題**: `cost_usd` メトリクスがない

**原因**: 一部のMLflowバージョンではコスト計算がサポートされていない

**解決策**:
```bash
# MLflow を最新版にアップデート
pip install --upgrade mlflow
```

### エラーハンドリング

Autologging初期化エラーは**グレースフルハンドリング**されます：

```
WARNING: Failed to enable OpenAI autologging, continuing without it
```

このエラーが出ても、**アプリケーションは正常に動作**します。既存の手動ロギングが動作するため、問題ありません。

## ベストプラクティス

### 1. コスト監視

定期的にMLflow UIでコストを確認：

```bash
# 月次コスト確認
# MLflow UI → Experiments → cost_usd でソート
```

**アラート設定**（推奨）:
- 1日のコストが$10を超えたら通知
- 1Runのトークン数が10,000を超えたら通知

### 2. パフォーマンス最適化

レイテンシを監視して最適化：

```bash
# 遅いRunを特定
# MLflow UI → Metrics → latency_ms でソート（降順）
```

**改善策**:
- `max_tokens` を削減
- より高速なモデルに切り替え（`gpt-4o` など）
- バッチ処理の導入

### 3. デバッグ

LLM入出力を確認してデバッグ：

```bash
# MLflow UI → Artifacts → inputs/messages.json
# プロンプトが正しいか確認

# MLflow UI → Artifacts → outputs/response.json
# レスポンスが期待通りか確認
```

## まとめ

MLflow Native Autologgingにより：

✅ **ゼロ設定** - コード変更不要で自動追跡
✅ **完全自動** - トークン・コスト・レイテンシを自動記録
✅ **既存機能と共存** - 手動ロギングと併用可能
✅ **コスト管理** - リアルタイムでコスト可視化
✅ **デバッグ支援** - 完全なLLM入出力を記録

**追加設定不要**で、即座に使い始めることができます！
