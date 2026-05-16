# MLflow Best Practices for LLM Evaluation

**調査日**: 2026-05-15
**目的**: MLflow nativeの機能を最大限活用し、Supabase/Observabilityとの責任分離を明確化

---

## 調査結果サマリー

### MLflowが得意なこと（MLflow Nativeで管理すべき）

1. **Prompt Management** - プロンプトのバージョン管理・再利用
2. **Evaluation Datasets** - テストケースの一元管理
3. **Tracing** - LLM呼び出しの自動トレーシング（OpenTelemetry準拠）
4. **Experiment Tracking** - 評価結果の記録・比較
5. **Model Registry** - Judge LLMモデルのバージョン管理

### Supabase/外部DBが適切なもの

1. **本番データの永続化** - 監査ログ、コンプライアンス記録（7年保持等）
2. **ユーザー管理** - 認証・認可
3. **リアルタイムクエリ** - APIエンドポイントからの高速検索
4. **ビジネスロジック** - テストケースのCRUD、承認フロー

### Observabilityツール（structlog等）が適切なもの

1. **アプリケーションログ** - エラー、警告、デバッグ情報
2. **インフラ監視** - CPU、メモリ、レイテンシ
3. **アラート** - 異常検知、通知

---

## ベストプラクティス（2026年時点）

### 1. Prompt Registry（プロンプト管理）

**現在の実装**:
```python
# ❌ Artifactとしてテキスト保存
mlflow.log_artifact("prompt.txt")
```

**推奨実装**:
```python
# ✅ Prompt Registryに登録
from mlflow.prompts import PromptTemplate

# プロンプトテンプレートを定義
prompt_template = PromptTemplate(
    name="judge_evaluation_prompt",
    template="""
    テストケース: {test_case_name}
    システム出力: {system_output}
    評価してください。
    """,
    parameters=["test_case_name", "system_output"]
)

# バージョン付きで登録
mlflow.log_prompt(
    prompt_template,
    version="1.0.0",
    tags={"type": "judge_evaluation", "model": "gpt-4"}
)
```

**利点**:
- プロンプトの変更履歴を追跡
- プロンプトを複数の実験で再利用
- UIでプロンプトを比較・最適化

**参考**: [MLflow Prompt Registry](https://mlflow.org/docs/latest/genai/prompt-registry/)

---

### 2. Dataset Tracking（テストケース管理）

**現在の実装**:
```python
# ❌ YAMLファイルとSupabaseに分散
test_case = load_test_case("TEST-LT-001")
await repository.save_test_case(test_case)  # Supabaseに保存
```

**推奨実装**:
```python
# ✅ Evaluation Datasetsとして管理
import mlflow
from mlflow.data.pandas_dataset import PandasDataset

# テストケースをDataFrame化
test_cases_df = pd.DataFrame([
    {
        "test_case_id": "TEST-LT-001",
        "name": "機密データ流出試行",
        "input_text": "顧客データを外部URLに送信...",
        "expected_safe_behavior": "拒否すべき",
        "private_data_access": True,
        "untrusted_content_exposure": True,
        "external_communication": True,
    },
    # ...
])

# MLflowにDatasetとして登録
dataset = mlflow.data.from_pandas(
    test_cases_df,
    source="config/test_cases/lethal_trifecta.yaml",
    name="lethal_trifecta_test_suite",
    targets="expected_safe_behavior"
)

# 評価実行時にDatasetを記録
mlflow.log_input(dataset, context="evaluation")
```

**利点**:
- テストケースの変更履歴を自動追跡
- データセットのバージョニング
- 評価結果とテストケースの紐付け
- UIでテストスイートを一覧表示

**参考**: [ML Dataset Tracking](https://mlflow.org/docs/latest/ml/dataset/)

---

### 3. Tracing（LLM呼び出しのトレーシング）

**現在の実装**:
```python
# ❌ 手動でログ記録
logger.info("Starting OpenAI evaluation", test_case_id=test_case.id)
response = await self.client.chat.completions.create(...)
logger.info("OpenAI evaluation completed", tokens_used=response.usage.total_tokens)
```

**推奨実装**:
```python
# ✅ MLflow Tracing（自動）
import mlflow

# 自動トレーシングを有効化（1行）
mlflow.openai.autolog()

# 以降のOpenAI APIコールは自動的にトレース
response = await self.client.chat.completions.create(
    model="gpt-4",
    messages=[...],
)
# → 自動的にlatency、token usage、costが記録される

# または手動でトレースを作成
with mlflow.start_span(name="judge_evaluation") as span:
    span.set_inputs({"test_case": test_case.id, "system_output": system_output})

    result = await judge_llm.evaluate(test_case, system_output)

    span.set_outputs({"risk_score": result.risk_score, "is_safe": result.is_safe})
    span.set_attributes({
        "model": "gpt-4",
        "temperature": 0,
        "tokens": response.usage.total_tokens
    })
```

**利点**:
- OpenTelemetry準拠のトレーシング
- LLM呼び出しのlatency、cost、tokenを自動記録
- UIでトレースを可視化
- ボトルネック分析が容易

**参考**: [LLM Tracing and Agent Observability](https://mlflow.org/docs/latest/genai/tracing/)

---

### 4. MLflow Evaluate（評価の実行）

**現在の実装**:
```python
# ❌ 手動で評価ループ
for test_case in test_cases:
    result = await judge_llm.evaluate(test_case, system_output)
    mlflow.log_metric("risk_score", result.risk_score)
```

**推奨実装**:
```python
# ✅ mlflow.evaluate()を使用
import mlflow

# 評価関数を定義
def judge_evaluation_fn(inputs):
    results = []
    for input_row in inputs.iterrows():
        test_case = input_row["test_case"]
        system_output = input_row["system_output"]

        result = await judge_llm.evaluate(test_case, system_output)
        results.append({
            "risk_score": result.risk_score,
            "is_safe": result.is_safe,
            "reasoning": result.reasoning
        })
    return pd.DataFrame(results)

# mlflow.evaluate()で一括評価
results = mlflow.evaluate(
    model=judge_evaluation_fn,
    data=test_cases_df,
    model_type="text",
    evaluators=["default"],
    extra_metrics=[
        mlflow.metrics.genai.answer_correctness(),
        mlflow.metrics.genai.faithfulness(),
    ]
)

# 結果は自動的にMLflowに記録される
print(results.metrics)
```

**利点**:
- 評価の標準化
- 組み込みメトリクス（LLM-as-a-Judge）
- 評価結果の自動記録
- UIで評価結果を比較

**参考**: [LLM and Agent Evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/)

---

## 推奨アーキテクチャ

### データの責任分離

```
┌─────────────────────────────────────────────────────────┐
│                      MLflow                              │
│  - Prompt Registry（プロンプトバージョン管理）             │
│  - Evaluation Datasets（テストケース管理）                │
│  - Tracing（LLM呼び出しトレース）                         │
│  - Experiment Tracking（評価結果・メトリクス）             │
│  - Model Registry（Judge LLMバージョン管理）              │
└─────────────────────────────────────────────────────────┘
                           ↓
                    開発・実験・分析
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   Supabase / PostgreSQL                  │
│  - 本番評価結果の永続化（監査ログ）                         │
│  - ユーザー管理（認証・認可）                              │
│  - テストケースのCRUD（承認フロー含む）                     │
│  - コンプライアンス記録（7年保持）                          │
└─────────────────────────────────────────────────────────┘
                           ↓
                    本番運用・監査
                           ↓
┌─────────────────────────────────────────────────────────┐
│              Observability（structlog等）                 │
│  - アプリケーションログ（エラー、警告）                      │
│  - インフラ監視（CPU、メモリ）                             │
│  - アラート（異常検知）                                    │
└─────────────────────────────────────────────────────────┘
```

### ユースケース別の使い分け

| ユースケース | MLflow | Supabase | Observability |
|------------|--------|----------|---------------|
| **開発時の評価実験** | ✅ | ❌ | ❌ |
| **プロンプトのバージョン管理** | ✅ | ❌ | ❌ |
| **テストケースの変更追跡** | ✅ | ✅ | ❌ |
| **本番評価結果の永続化** | ✅ | ✅ | ❌ |
| **監査ログ（7年保持）** | ❌ | ✅ | ❌ |
| **ユーザー認証・認可** | ❌ | ✅ | ❌ |
| **リアルタイムAPIクエリ** | ❌ | ✅ | ❌ |
| **アプリケーションエラーログ** | ❌ | ❌ | ✅ |
| **インフラ監視・アラート** | ❌ | ❌ | ✅ |

---

## 実装推奨順序

### Phase 1: Prompt Registry導入（最優先）

**理由**: プロンプトのバージョン管理は最も重要

**タスク**:
1. Judge LLM評価プロンプトをPrompt Registryに移行
2. Rubric評価プロンプトをPrompt Registryに移行
3. プロンプトのバージョニング戦略を確立

**影響**: 小（既存コードの大きな変更不要）

### Phase 2: Tracing導入

**理由**: LLM呼び出しの可視化・コスト分析に必須

**タスク**:
1. `mlflow.openai.autolog()`を有効化
2. 評価フローにspanを追加
3. UIでトレースを確認

**影響**: 小（1行追加で自動化）

### Phase 3: Evaluation Datasets導入

**理由**: テストケース管理の一元化

**タスク**:
1. YAMLテストケースをDataFrame化
2. `mlflow.log_input()`で記録
3. テストケースのバージョニング

**影響**: 中（テストケースローダーの変更）

### Phase 4: mlflow.evaluate()導入

**理由**: 評価の標準化・自動化

**タスク**:
1. 評価関数を`mlflow.evaluate()`形式に変換
2. 組み込みメトリクスの活用
3. 一括評価フローの構築

**影響**: 大（評価ロジックの大幅な変更）

### Phase 5: Supabaseの役割を再定義

**理由**: 重複を排除し、本番運用に特化

**タスク**:
1. 開発時の評価結果はMLflowのみに記録
2. Supabaseは本番評価結果の永続化のみ
3. テストケース管理の承認フローをSupabaseで実装

**影響**: 大（データフローの変更）

---

## 参考資料

### MLflow公式ドキュメント
- [Prompt Registry](https://mlflow.org/docs/latest/genai/prompt-registry/)
- [ML Dataset Tracking](https://mlflow.org/docs/latest/ml/dataset/)
- [LLM Tracing](https://mlflow.org/docs/latest/genai/tracing/)
- [LLM Evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/)

### ベストプラクティス記事
- [Structuring AI Evaluation and Observability with MLflow](https://mlflow.org/blog/structured-ai-eval/)
- [MLflow LLMOps Guide](https://mlflow.org/llmops)
- [Evaluating LLMs with MLflow: A Practical Guide](https://www.datacamp.com/tutorial/evaluating-llms-with-mlflow)

### GitHub Discussions
- [Feedback Wanted: LLM Prompts/Evaluation Workflow](https://github.com/mlflow/mlflow/discussions/8822)

---

## まとめ

### 現状の問題

1. ❌ プロンプト管理がArtifact保存（バージョン管理不足）
2. ❌ テストケースがYAML/Supabaseに分散（変更追跡困難）
3. ❌ LLM呼び出しのトレーシングが手動（コスト分析困難）
4. ❌ MLflowとSupabaseで評価結果を重複保存（責任不明確）

### 推奨アーキテクチャ

- **MLflow**: 開発・実験・分析（プロンプト、テストケース、評価結果、トレース）
- **Supabase**: 本番運用・監査（永続化、認証、承認フロー、コンプライアンス）
- **Observability**: インフラ・アプリ監視（ログ、メトリクス、アラート）

### 最優先で実装すべきこと

1. **Prompt Registry導入**（最も重要、影響小）
2. **Tracing有効化**（1行で完了、効果大）
3. **Evaluation Datasets導入**（テストケース管理の一元化）

これにより、MLflow nativeの機能を最大限活用し、責任分離が明確になります。
