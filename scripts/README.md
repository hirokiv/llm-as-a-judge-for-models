# Scripts Directory

評価実行とMLflowエクスポート用のスクリプト集

## 📁 ディレクトリ構造

```
scripts/
├── run_input_evaluation.py      # INPUT評価実行スクリプト
├── export_evaluation_results.py # MLflow評価結果エクスポート（基本版）
├── export_detailed_results.py   # MLflow評価結果エクスポート（詳細版、Artifacts含む）
└── README.md                     # このファイル
```

## 🚀 使い方

### 1. INPUT評価の実行

実際のLLM（OpenAI GPT）を使ってINPUT評価を実行します。

```bash
# Makefileコマンド（推奨）
make run-evaluation

# 直接実行
python scripts/run_input_evaluation.py
```

**出力例**:
- テストケースベースの評価（TEST-PI-001等）
- 直接プロンプトでの評価
- 評価結果（is_safe、risk_score、exploited_vectors、reasoning等）

### 2. 評価結果のエクスポート

#### 基本版エクスポート

メトリクスとパラメータのみをエクスポート（軽量、高速）

```bash
# Makefileコマンド（推奨）
make export-results

# 直接実行
python scripts/export_evaluation_results.py
```

**出力先**: `exports/evaluations/evaluation_results.csv`

**含まれる情報**:
- run_id、start_time
- test_case_id、model
- is_safe、risk_score、exploited_vectors
- reasoning（200文字まで）、recommendation（200文字まで）

#### 詳細版エクスポート（推奨）

MLflow Artifactsから完全な詳細データを取得してエクスポート

```bash
# Makefileコマンド（推奨）
make export-detailed

# 直接実行
python scripts/export_detailed_results.py
```

**出力先**: `exports/evaluations/detailed_evaluation_results.csv`

**含まれる情報**:
- ✅ **完全なreasoning**（全文）
- ✅ **完全なrecommendation**（全文）
- ✅ **input_text**（システムへの入力）
- ✅ **system_output**（システムからの出力）
- ✅ 実行時間（duration_sec）
- ✅ トークン使用量（prompt_tokens、completion_tokens、total_tokens）

### 3. エクスポートファイルのクリーンアップ

```bash
make clean-exports
```

## 📊 エクスポートファイルの場所

すべてのエクスポートファイルは `exports/evaluations/` ディレクトリに保存されます。

```
exports/
└── evaluations/
    ├── evaluation_results.csv          # 基本版
    └── detailed_evaluation_results.csv # 詳細版（推奨）
```

## 💡 Tips

### Excelで開く

```bash
# macOS
open exports/evaluations/detailed_evaluation_results.csv

# または
open -a "Microsoft Excel" exports/evaluations/detailed_evaluation_results.csv
```

### 特定の列だけ抽出

```bash
# csvkitを使う（要インストール: pip install csvkit）
csvcut -c test_case_id,is_safe,risk_score,reasoning exports/evaluations/detailed_evaluation_results.csv
```

### CSVをJSONに変換

```python
import pandas as pd

df = pd.read_csv('exports/evaluations/detailed_evaluation_results.csv')
df.to_json('exports/evaluations/results.json', orient='records', indent=2)
```

## 🔧 カスタマイズ

### エクスポート件数を変更

スクリプトを編集して `max_results` パラメータを変更:

```python
# scripts/export_detailed_results.py
runs = client.search_runs(
    experiment_ids=[experiment.experiment_id],
    max_results=100,  # ← ここを変更（デフォルト: 100）
    order_by=["start_time DESC"]
)
```

### エクスポート先を変更

スクリプトの `output_file` パラメータを変更:

```python
export_detailed_results("exports/custom_path/my_results.csv")
```

## ⚠️ 注意事項

1. **MLflowサーバー起動が必要**
   - エクスポート前に `make mlflow` でMLflowサーバーを起動してください

2. **.env設定が必要**
   - `MLFLOW_TRACKING_URI` などの環境変数が設定されている必要があります

3. **Artifactsダウンロード時間**
   - 詳細版エクスポートは全Artifactsをダウンロードするため、runの数に応じて時間がかかります

4. **Git管理外**
   - `exports/` ディレクトリは `.gitignore` に含まれており、Git管理外です

## 🐛 トラブルシューティング

### エラー: "実験が見つかりません"

```bash
# MLflowサーバーが起動しているか確認
ps aux | grep mlflow

# 起動していない場合
make mlflow
```

### エラー: "No module named 'src'"

```bash
# プロジェクトルートから実行してください
cd /path/to/llm-as-a-judge-for-models
python scripts/export_detailed_results.py
```

### エクスポート結果が空

```bash
# 評価が実行されているか確認
make run-evaluation

# MLflow UIで確認
open http://localhost:5555
```

## 📚 関連ドキュメント

- [MLflow Tracking](https://mlflow.org/docs/latest/tracking.html)
- [評価実行ガイド](../docs/user/guides/running-evaluations.md)
- [プロジェクトREADME](../README.md)
