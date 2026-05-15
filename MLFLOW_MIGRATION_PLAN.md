# MLflow Native機能への移行プラン

**作成日**: 2026-05-15
**現状**: MLflowの基本機能のみ使用（log_param, log_metric, log_artifact）
**目標**: MLflow Native機能を最大限活用し、責任分離を明確化

---

## 現状 vs 推奨実装の比較

### 1. プロンプト管理

| 観点 | 現状 ❌ | 推奨 ✅ | 優先度 |
|------|---------|---------|--------|
| **保存方法** | テキストArtifact | Prompt Registry | 🔴 高 |
| **バージョン管理** | なし（Gitのみ） | MLflowネイティブ | 🔴 高 |
| **再利用性** | 困難 | 容易（UIから選択） | 🔴 高 |
| **変更追跡** | Gitコミット | MLflow UI | 🔴 高 |
| **実装コスト** | - | 小（数時間） | - |

**現在のコード**:
```python
# src/services/mlflow_tracker.py:221-225
artifacts = {
    "system_output.txt": system_output,
    "reasoning.txt": judge_result.reasoning,
}
self._log_text_artifacts(artifacts)
```

**推奨コード**:
```python
# Prompt Registryに登録
from mlflow.prompts import PromptTemplate

prompt = PromptTemplate(
    name="judge_evaluation_prompt",
    template=self.judge_llm.system_prompt,
    version="1.0.0"
)
mlflow.log_prompt(prompt)
```

---

### 2. テストケース管理

| 観点 | 現状 ❌ | 推奨 ✅ | 優先度 |
|------|---------|---------|--------|
| **保存場所** | YAML + Supabase | MLflow Evaluation Datasets | 🟡 中 |
| **バージョン管理** | Gitのみ | MLflow自動追跡 | 🟡 中 |
| **変更追跡** | 手動 | 自動 | 🟡 中 |
| **評価との紐付け** | test_case_id（文字列） | Dataset オブジェクト | 🟡 中 |
| **実装コスト** | - | 中（1-2日） | - |

**現在のコード**:
```python
# src/utils/test_case_loader.py
def load_test_case(test_case_id: str) -> TestCaseScenario:
    # YAMLファイルから読み込み
    with open(yaml_file) as f:
        data = yaml.safe_load(f)
```

**推奨コード**:
```python
# Evaluation Datasetとして管理
import mlflow

dataset = mlflow.data.from_pandas(
    test_cases_df,
    source="config/test_cases/lethal_trifecta.yaml",
    name="lethal_trifecta_test_suite"
)
mlflow.log_input(dataset, context="evaluation")
```

---

### 3. LLM呼び出しのトレーシング

| 観点 | 現状 ❌ | 推奨 ✅ | 優先度 |
|------|---------|---------|--------|
| **トレース方法** | 手動ログ（structlog） | MLflow Tracing（自動） | 🔴 高 |
| **標準準拠** | なし | OpenTelemetry | 🔴 高 |
| **記録内容** | カスタム | latency/tokens/cost自動 | 🔴 高 |
| **可視化** | ログファイル | MLflow UI | 🔴 高 |
| **実装コスト** | - | 極小（1行追加） | - |

**現在のコード**:
```python
# src/services/judge_llm.py:253-260
logger.info(
    "Starting OpenAI evaluation",
    test_case_id=test_case.id,
    output_length=len(system_output),
)

response = await self.client.chat.completions.create(...)

logger.info(
    "OpenAI evaluation completed",
    tokens_used=response.usage.total_tokens,
)
```

**推奨コード**:
```python
# 1行追加で自動トレーシング
mlflow.openai.autolog()

# 以降のOpenAI APIコールは自動的にトレース
response = await self.client.chat.completions.create(...)
# → latency、tokens、costが自動記録
```

---

### 4. 評価結果の保存

| 観点 | 現状 ❌ | 推奨 ✅ | 優先度 |
|------|---------|---------|--------|
| **保存先** | MLflow + Supabase（重複） | MLflow（開発）+ Supabase（本番のみ） | 🟡 中 |
| **評価方法** | 手動ループ | `mlflow.evaluate()` | 🟢 低 |
| **メトリクス** | カスタム | 組み込み + カスタム | 🟢 低 |
| **一括評価** | 未実装 | ネイティブサポート | 🟢 低 |
| **実装コスト** | - | 大（3-5日） | - |

**現在のコード**:
```python
# src/services/evaluator.py:135-139
self.mlflow_tracker.log_evaluation_result(
    test_case=test_case,
    judge_result=judge_result,
    system_output=system_output,
)

# src/services/evaluator.py:144-150
result_id = await self.repository.save_evaluation_result(
    mlflow_run_id=mlflow_run_id,
    test_case_id=test_case_id,
    system_output=system_output,
    judge_result=judge_result,
)
# → MLflowとSupabaseの両方に保存（重複）
```

**推奨コード**:
```python
# mlflow.evaluate()で評価
results = mlflow.evaluate(
    model=judge_evaluation_fn,
    data=test_cases_df,
    model_type="text",
    evaluators=["default"],
)

# 開発時: MLflowのみに記録
# 本番時: MLflow + Supabase（監査用）
if is_production:
    await self.repository.save_evaluation_result(...)
```

---

## データ保存先の責任分離

### 現状の問題点

```
┌─────────────────────────────────────┐
│         MLflow (開発・本番)          │
│  - 評価結果（すべて）                 │
│  - メトリクス（すべて）               │
│  - Artifacts（プロンプト、出力）       │
└─────────────────────────────────────┘
                 ↓ 重複
┌─────────────────────────────────────┐
│        Supabase (開発・本番)         │
│  - 評価結果（すべて）                 │
│  - テストケース                       │
│  - ユーザー管理                       │
└─────────────────────────────────────┘
                 ↓ 手動
┌─────────────────────────────────────┐
│   Observability (structlog)         │
│  - LLM呼び出しログ（手動）            │
│  - アプリケーションログ               │
└─────────────────────────────────────┘
```

**問題**:
1. ❌ 評価結果がMLflowとSupabaseで重複
2. ❌ プロンプト管理がGitとArtifactで分散
3. ❌ LLM呼び出しのトレーシングが手動
4. ❌ テストケースがYAML/Supabaseで分散

### 推奨アーキテクチャ

```
┌─────────────────────────────────────┐
│      MLflow (開発・実験・分析)        │
│  ✅ Prompt Registry                  │
│    - プロンプトバージョン管理          │
│    - 再利用・最適化                   │
│  ✅ Evaluation Datasets              │
│    - テストケース管理                 │
│    - バージョニング                   │
│  ✅ Tracing (OpenTelemetry)          │
│    - LLM呼び出し自動トレース          │
│    - latency/tokens/cost記録         │
│  ✅ Experiment Tracking              │
│    - 開発時の評価結果                 │
│    - メトリクス・比較                 │
└─────────────────────────────────────┘
                 ↓ 本番のみ
┌─────────────────────────────────────┐
│     Supabase (本番運用・監査)         │
│  ✅ 本番評価結果の永続化               │
│    - 監査ログ（7年保持）              │
│    - コンプライアンス記録              │
│  ✅ ユーザー管理                      │
│    - 認証・認可                       │
│  ✅ テストケースCRUD                  │
│    - 承認フロー                       │
│    - ビジネスロジック                 │
└─────────────────────────────────────┘
                 ↓ インフラ
┌─────────────────────────────────────┐
│   Observability (structlog等)        │
│  ✅ アプリケーションログ               │
│    - エラー、警告                     │
│  ✅ インフラ監視                      │
│    - CPU、メモリ、レイテンシ          │
│  ✅ アラート                          │
│    - 異常検知、通知                   │
└─────────────────────────────────────┘
```

---

## 移行プラン（Phase別）

### Phase 1: Tracing導入（最優先・最小工数）

**期間**: 0.5日
**優先度**: 🔴 高
**実装コスト**: 極小

**タスク**:
1. `src/services/judge_llm.py`に1行追加
   ```python
   # OpenAIJudgeLLM.__init__()
   mlflow.openai.autolog()
   ```
2. 動作確認（MLflow UIでトレース表示）

**効果**:
- ✅ LLM呼び出しのlatency、tokens、costが自動記録
- ✅ OpenTelemetry準拠のトレーシング
- ✅ ボトルネック分析が容易

**リスク**: なし（既存機能に影響なし）

---

### Phase 2: Prompt Registry導入

**期間**: 1-2日
**優先度**: 🔴 高
**実装コスト**: 小

**タスク**:
1. Judge LLM評価プロンプトをPromptTemplateに変換
2. Rubric評価プロンプトをPromptTemplateに変換
3. `mlflow.log_prompt()`で記録
4. プロンプトバージョニング戦略を確立
   - バージョンフォーマット: `v{major}.{minor}.{patch}`
   - 変更時はバージョンアップ

**実装例**:
```python
# src/services/judge_llm.py
from mlflow.prompts import PromptTemplate

class OpenAIJudgeLLM(BaseJudgeLLM):
    def __init__(self, config: dict[str, Any]):
        # ...existing code...

        # Prompt Registryに登録
        prompt_template = PromptTemplate(
            name="judge_evaluation_prompt",
            template=self.system_prompt,
            parameters=["test_case", "system_output"],
            version="1.0.0"
        )
        mlflow.log_prompt(prompt_template)
```

**効果**:
- ✅ プロンプトの変更履歴を追跡
- ✅ UIでプロンプトを比較・最適化
- ✅ プロンプトを複数の実験で再利用

**リスク**: 小（既存のArtifact保存と併用可能）

---

### Phase 3: Evaluation Datasets導入

**期間**: 1-2日
**優先度**: 🟡 中
**実装コスト**: 中

**タスク**:
1. `src/utils/test_case_loader.py`を拡張
   - YAMLからDataFrame変換を追加
2. `mlflow.log_input()`で記録
3. テストケースのバージョニング

**実装例**:
```python
# src/utils/test_case_loader.py
import mlflow
import pandas as pd

def load_test_cases_as_dataset(yaml_file: str) -> mlflow.data.dataset.Dataset:
    # YAMLからDataFrame作成
    test_cases = []
    with open(yaml_file) as f:
        data = yaml.safe_load(f)
        for tc in data["test_cases"]:
            test_cases.append({
                "test_case_id": tc["test_case_id"],
                "name": tc["name"],
                "input_text": tc["input_text"],
                # ...
            })

    df = pd.DataFrame(test_cases)

    # Datasetとして登録
    dataset = mlflow.data.from_pandas(
        df,
        source=yaml_file,
        name="lethal_trifecta_test_suite",
        targets="expected_safe_behavior"
    )

    return dataset

# 使用例
dataset = load_test_cases_as_dataset("config/test_cases/lethal_trifecta.yaml")
mlflow.log_input(dataset, context="evaluation")
```

**効果**:
- ✅ テストケースの変更履歴を自動追跡
- ✅ UIでテストスイートを一覧表示
- ✅ 評価結果とテストケースの紐付け

**リスク**: 中（既存のYAMLローダーとの互換性維持が必要）

---

### Phase 4: 評価結果保存の最適化

**期間**: 1日
**優先度**: 🟡 中
**実装コスト**: 中

**タスク**:
1. 開発環境: MLflowのみに保存
2. 本番環境: MLflow + Supabase（監査用）
3. 環境変数で切り替え

**実装例**:
```python
# src/services/evaluator.py
import os

async def _save_results(self, ...):
    # MLflowには常に記録
    # （既存のlog_evaluation_result()）

    # Supabaseには本番のみ保存
    if os.getenv("ENVIRONMENT") == "production":
        result_id = await self.repository.save_evaluation_result(...)
        logger.info("Saved to Supabase for audit", result_id=result_id)
    else:
        logger.info("Development mode: Skipping Supabase save")
        result_id = mlflow_run_id  # MLflow Run IDを返す
```

**効果**:
- ✅ 開発時の重複保存を排除
- ✅ 本番時は監査用にSupabase保存
- ✅ データフローの明確化

**リスク**: 小（環境変数で制御、ロールバック容易）

---

### Phase 5: mlflow.evaluate()導入（将来的）

**期間**: 3-5日
**優先度**: 🟢 低
**実装コスト**: 大

**タスク**:
1. 評価ロジックを`mlflow.evaluate()`形式に変換
2. 組み込みメトリクス（LLM-as-a-Judge）の活用
3. 一括評価フローの構築

**実装例**:
```python
# 評価関数を定義
async def judge_evaluation_fn(inputs: pd.DataFrame) -> pd.DataFrame:
    results = []
    for _, row in inputs.iterrows():
        result = await judge_llm.evaluate(
            test_case=row["test_case"],
            system_output=row["system_output"]
        )
        results.append({
            "risk_score": result.risk_score,
            "is_safe": result.is_safe,
        })
    return pd.DataFrame(results)

# mlflow.evaluate()で一括評価
results = mlflow.evaluate(
    model=judge_evaluation_fn,
    data=test_cases_df,
    model_type="text",
    evaluators=["default"],
)
```

**効果**:
- ✅ 評価の標準化
- ✅ 組み込みメトリクス（faithfulness等）
- ✅ 一括評価のパフォーマンス向上

**リスク**: 大（評価ロジックの大幅な変更が必要）

---

## 実装優先順位

### 最優先（Phase 1-2）

1. **Tracing導入** - 0.5日、工数極小、効果大
2. **Prompt Registry導入** - 1-2日、工数小、効果大

**理由**: 最小工数で最大の効果、既存コードへの影響が小さい

### 次に実施（Phase 3-4）

3. **Evaluation Datasets導入** - 1-2日、工数中
4. **評価結果保存の最適化** - 1日、工数中

**理由**: データフローの明確化、重複排除

### 将来的に検討（Phase 5）

5. **mlflow.evaluate()導入** - 3-5日、工数大

**理由**: 評価ロジックの大幅な変更が必要、ROIは低め

---

## 期待される効果

### 開発効率の向上

- ✅ プロンプトの変更履歴を簡単に追跡
- ✅ LLM呼び出しのコスト・レイテンシを自動分析
- ✅ テストケースのバージョニング自動化

### 運用コストの削減

- ✅ 重複保存の排除（ストレージコスト削減）
- ✅ 自動トレーシング（手動ログ記録不要）
- ✅ 責任分離の明確化（データフロー理解が容易）

### コンプライアンス対応

- ✅ MLflow: 開発・実験記録
- ✅ Supabase: 本番・監査記録（7年保持）
- ✅ 明確な証跡管理

---

## まとめ

### 現状の課題

1. ❌ MLflow nativeの機能を活用していない
2. ❌ MLflowとSupabaseで評価結果を重複保存
3. ❌ プロンプト管理がArtifact保存（バージョン管理不足）
4. ❌ LLM呼び出しのトレーシングが手動

### 推奨アクション

**Phase 1-2を最優先で実施**（合計1.5-2.5日）:

1. ✅ Tracing導入（0.5日） - `mlflow.openai.autolog()`
2. ✅ Prompt Registry導入（1-2日） - プロンプトバージョン管理

**Phase 3-4を次に実施**（合計2-3日）:

3. ✅ Evaluation Datasets導入（1-2日）
4. ✅ 評価結果保存の最適化（1日）

**Phase 5は将来的に検討**（3-5日）:

5. ⏸️ mlflow.evaluate()導入（優先度低）

### 期待される成果

- 🎯 開発効率向上（プロンプト・テストケース管理の自動化）
- 💰 運用コスト削減（重複排除、自動トレーシング）
- 🔒 コンプライアンス対応強化（責任分離の明確化）
