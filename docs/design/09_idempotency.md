# 冪等性保証の実装

## 概要
本システムでは、Judge LLMによる評価の冪等性（同一入力に対して同一出力）を**モデル・バージョン別**に保証する仕組みを実装する。これにより、評価の再現性と信頼性を確保する。

## 重要：モデル・バージョン別の冪等性管理

**冪等性はJudge LLMのモデルおよびバージョン毎に個別に保証される必要があります。**

理由：
1. **モデルの違い**: gpt-4とgpt-3.5-turboでは出力が異なる
2. **バージョンの違い**: 同じgpt-4でも0613と1106では挙動が変わる
3. **プロバイダーの違い**: OpenAIとAzure OpenAIで微妙な差異がある
4. **プロンプトの違い**: プロンプトバージョンが変われば出力も変わる

### モデル・バージョン識別子

冪等性の検証・記録には、以下の組み合わせで一意に識別：

```python
model_version_key = f"{provider}:{model_name}:{model_version}:{temperature}:{seed}:{prompt_version}"

# 例:
# "openai:gpt-4-turbo:0125:0.0:42:v2.1"
# "azure:gpt-4:0613:0.0:42:v2.0"
```

## 冪等性の重要性

### 1. 監査要件
- 同じテストケースを再評価した際、一貫した結果が必要
- 評価の公平性と透明性の担保
- **特定のモデル・バージョンでの評価結果の再現性**

### 2. 品質保証
- LLMの出力が安定していることの検証
- プロンプトエンジニアリングの効果測定
- **モデルアップグレード時の影響分析**

### 3. デバッグとトラブルシューティング
- 問題の再現性確保
- 評価ロジックの変更による影響の把握
- **どのモデル・バージョンで問題が発生したかの特定**

## 冪等性を実現する手法

### 1. LLMパラメータの固定

#### temperature=0
LLMの出力を最も確定的にする。

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    temperature=0,  # 確定的な出力
    model_kwargs={"seed": 42}  # シード固定
)
```

#### seed固定
OpenAI APIでは、`seed`パラメータを指定することで、さらに冪等性を高める。

### 2. 入力の正規化
同じ意図の入力は、完全に同一の文字列にする。

```python
def normalize_input(text: str) -> str:
    """入力テキストを正規化"""
    # 前後の空白を削除
    text = text.strip()
    # 連続する空白を1つに
    text = " ".join(text.split())
    # 改行コードの統一
    text = text.replace("\r\n", "\n")
    return text
```

### 3. プロンプトテンプレートのバージョン管理
プロンプトの変更履歴を管理し、同じバージョンのプロンプトを使用する。

```python
PROMPT_VERSION = "1.0.0"

judge_prompt = ChatPromptTemplate.from_messages([
    ("system", f"Version: {PROMPT_VERSION}\n{system_message}"),
    ("user", "{user_message}")
])
```

## 冪等性チェッカーの実装

### IdempotencyChecker クラス（`app/services/idempotency_checker.py`）

```python
import hashlib
import json
from typing import List, Dict, Any
from collections import Counter
from app.models.schemas import JudgeResult, IdempotencyCheckResult
from app.services.evaluator import EvaluatorService
import logging

logger = logging.getLogger(__name__)

class IdempotencyChecker:
    """冪等性チェッカー（モデル・バージョン別）"""

    def __init__(self, judge_config: Optional[JudgeLLMConfig] = None):
        """
        Args:
            judge_config: 使用するJudge LLM設定。
                         Noneの場合はデフォルト設定を使用。
        """
        self.judge_config = judge_config or self._get_default_config()
        self.evaluator = EvaluatorService(judge_config=self.judge_config)

    def _get_default_config(self) -> JudgeLLMConfig:
        """デフォルトJudge LLM設定を取得

        プロンプトバージョン管理サービスから最新のアクティブバージョンを取得し、
        デフォルト設定を構築する。

        Returns:
            JudgeLLMConfig: デフォルト設定
        """
        # プロンプトバージョン管理サービスから最新アクティブバージョンを取得
        from app.services.prompt_version_service import PromptVersionService

        prompt_version_service = PromptVersionService()
        active_version = prompt_version_service.get_active_version()

        return JudgeLLMConfig(
            provider="openai",
            model_name="gpt-4",
            model_version="0613",
            temperature=0.0,
            seed=42,
            prompt_version=active_version.version_id
        )

    def get_model_version_key(self) -> str:
        """
        モデル・バージョン識別子を生成

        Returns:
            "provider:model:version:temp:seed:prompt" 形式の文字列
        """
        config = self.judge_config
        return (
            f"{config.provider}:"
            f"{config.model_name}:"
            f"{config.model_version or 'latest'}:"
            f"{config.temperature}:"
            f"{config.seed}:"
            f"{config.prompt_version}"
        )

    def compute_input_hash(
        self,
        test_case_id: str,
        system_output: str
    ) -> str:
        """
        入力のハッシュ値を計算

        重要: モデル・バージョン情報も含めてハッシュ化
        """
        # 正規化された入力とモデル情報を結合
        model_key = self.get_model_version_key()
        normalized = f"{model_key}::{test_case_id}::{system_output.strip()}"

        # SHA-256ハッシュ
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def check_idempotency(
        self,
        test_case: Dict[str, Any],
        system_output: str,
        num_runs: int = 3
    ) -> IdempotencyCheckResult:
        """
        冪等性をチェックする

        Args:
            test_case: テストケース
            system_output: AIシステムの出力
            num_runs: 実行回数（デフォルト: 3回）

        Returns:
            IdempotencyCheckResult
        """
        logger.info(
            f"Starting idempotency check for {test_case['id']} with {num_runs} runs"
        )

        # 入力のハッシュ
        input_hash = self.compute_input_hash(test_case["id"], system_output)

        # 複数回評価を実行
        results = []
        executions = []

        for i in range(num_runs):
            try:
                eval_result = self.evaluator.evaluate_test_case(test_case, system_output)
                result = eval_result["evaluation"]
                results.append(result)

                executions.append({
                    "run": i + 1,
                    "risk_score": result.risk_score,
                    "is_safe": result.is_safe,
                    "exploited_vectors": result.exploited_vectors,
                    "mlflow_run_id": eval_result["mlflow_run_id"]
                })

                logger.info(f"Run {i+1}/{num_runs} completed: risk_score={result.risk_score}")

            except Exception as e:
                logger.error(f"Run {i+1} failed: {str(e)}")
                executions.append({
                    "run": i + 1,
                    "error": str(e)
                })

        # 冪等性の判定
        is_idempotent, variance_score, message = self._analyze_results(results)

        return IdempotencyCheckResult(
            is_idempotent=is_idempotent,
            input_hash=input_hash,
            executions=executions,
            variance_score=variance_score,
            message=message
        )

    def _analyze_results(
        self,
        results: List[JudgeResult]
    ) -> tuple[bool, float, str]:
        """
        結果を分析し、冪等性を判定

        Returns:
            (is_idempotent, variance_score, message)
        """
        if len(results) < 2:
            return False, 0.0, "評価回数が不足しています"

        # 各フィールドの一致度を計算
        risk_scores = [r.risk_score for r in results]
        is_safe_values = [r.is_safe for r in results]

        # risk_scoreの一致度
        risk_score_variance = self._calculate_variance(risk_scores)

        # is_safeの一致度
        is_safe_variance = 1.0 if len(set(is_safe_values)) == 1 else 0.0

        # exploited_vectorsの一致度
        vectors_variance = self._calculate_vectors_variance(
            [r.exploited_vectors for r in results]
        )

        # 総合的な一致度（重み付け平均）
        variance_score = (
            risk_score_variance * 0.4 +
            is_safe_variance * 0.4 +
            vectors_variance * 0.2
        )

        # 冪等性の判定（90%以上の一致で冪等とみなす）
        is_idempotent = variance_score >= 0.9

        # メッセージ生成
        if variance_score == 1.0:
            message = f"{len(results)}回の実行で完全に同一の結果が得られました"
        elif is_idempotent:
            message = f"{len(results)}回の実行でほぼ一致する結果が得られました（一致度: {variance_score:.2%}）"
        else:
            message = f"{len(results)}回の実行で結果に差異がありました（一致度: {variance_score:.2%}）"

            # 差異の詳細
            if risk_score_variance < 1.0:
                risk_score_counts = Counter(risk_scores)
                message += f"\nRisk Score: {dict(risk_score_counts)}"

            if is_safe_variance < 1.0:
                is_safe_counts = Counter(is_safe_values)
                message += f"\nis_safe: {dict(is_safe_counts)}"

        return is_idempotent, variance_score, message

    def _calculate_variance(self, values: List[int]) -> float:
        """整数値のリストの一致度を計算（0.0〜1.0）"""
        if not values:
            return 0.0

        # 最頻値の出現率を一致度とする
        counter = Counter(values)
        most_common_count = counter.most_common(1)[0][1]
        return most_common_count / len(values)

    def _calculate_vectors_variance(self, vectors_list: List[List[str]]) -> float:
        """exploited_vectorsリストの一致度を計算"""
        if not vectors_list:
            return 0.0

        # 各リストをソート済み文字列に変換して比較
        normalized = [",".join(sorted(v)) for v in vectors_list]

        # 一致度を計算
        counter = Counter(normalized)
        most_common_count = counter.most_common(1)[0][1]
        return most_common_count / len(normalized)
```

### API エンドポイント（`app/api/routes.py`）

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict
from app.api.dependencies import get_current_user
from app.services.idempotency_checker import IdempotencyChecker
from app.services.test_case_manager import TestCaseManager

router = APIRouter()
idempotency_checker = IdempotencyChecker()
test_case_manager = TestCaseManager()

class IdempotencyCheckRequest(BaseModel):
    """冪等性チェックリクエスト"""
    test_case_id: str = Field(..., description="テストケースID")
    system_output: str = Field(..., description="AIシステムの出力")
    num_runs: int = Field(3, ge=2, le=10, description="実行回数（2〜10回）")

@router.post("/api/v1/idempotency-check")
async def run_idempotency_check(
    request: IdempotencyCheckRequest,
    current_user: Dict = Depends(get_current_user)
):
    """冪等性チェックを実行"""
    # テストケースを取得
    test_case = test_case_manager.get_test_case(request.test_case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    # 冪等性チェック実行
    result = idempotency_checker.check_idempotency(
        test_case,
        request.system_output,
        request.num_runs
    )

    return {
        "status": "success",
        "data": result.model_dump()
    }
```

## 冪等性チェックのワークフロー

### 1. 手動チェック
```bash
curl -X POST http://localhost:8000/api/v1/idempotency-check \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "TEST-LT-001",
    "system_output": "テスト出力",
    "num_runs": 5
  }'
```

### 2. 自動チェック（定期実行）
```python
# scripts/run_idempotency_checks.py
"""
すべてのテストケースに対して冪等性チェックを実行
"""
from app.services.idempotency_checker import IdempotencyChecker
from app.services.test_case_manager import TestCaseManager

def main():
    checker = IdempotencyChecker()
    manager = TestCaseManager()

    test_cases = manager.list_test_cases()

    for test_case in test_cases:
        print(f"Checking {test_case['id']}...")

        # サンプル出力で冪等性チェック
        sample_output = "標準的なシステム出力"

        result = checker.check_idempotency(
            test_case,
            sample_output,
            num_runs=3
        )

        if not result.is_idempotent:
            print(f"⚠️  {test_case['id']} is NOT idempotent!")
            print(f"   Variance score: {result.variance_score:.2%}")
            print(f"   Message: {result.message}")
        else:
            print(f"✓  {test_case['id']} is idempotent")

if __name__ == "__main__":
    main()
```

### 3. CI/CDパイプラインでのチェック
```yaml
# .github/workflows/idempotency-check.yml
name: Idempotency Check

on:
  schedule:
    - cron: '0 0 * * 0'  # 毎週日曜日0時
  workflow_dispatch:  # 手動実行も可能

jobs:
  idempotency-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run idempotency checks
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python scripts/run_idempotency_checks.py

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: idempotency-results
          path: idempotency_results.json
```

## 冪等性が保たれない場合の対処

### 1. LLMプロバイダーの確認
一部のLLMは`seed`パラメータをサポートしていない場合がある。

```python
# プロバイダー別の対応
if settings.LLM_PROVIDER == "azure":
    # Azure OpenAIでのseedサポート確認
    llm = AzureChatOpenAI(
        temperature=0,
        model_kwargs={"seed": 42} if supports_seed else {}
    )
```

### 2. プロンプトの見直し
プロンプトに曖昧な表現や選択肢が含まれていないか確認。

```python
# 悪い例（曖昧）
"このシステムは安全ですか？理由を1つまたは2つ挙げてください。"

# 良い例（明確）
"このシステムは安全ですか？理由を1つ挙げてください。"
```

### 3. 複数モデルによる検証
複数のJudge LLMで評価し、多数決を取る。

```python
class EnsembleIdempotencyChecker:
    """複数モデルによる冪等性チェック"""

    def __init__(self, models: List[str]):
        self.evaluators = [
            EvaluatorService(model=model) for model in models
        ]

    def check(self, test_case, system_output):
        results = []
        for evaluator in self.evaluators:
            result = evaluator.evaluate_test_case(test_case, system_output)
            results.append(result)

        # 多数決
        risk_scores = [r.risk_score for r in results]
        most_common_score = Counter(risk_scores).most_common(1)[0][0]

        return most_common_score
```

### 4. キャッシング
同一入力に対しては、過去の評価結果をキャッシュから返す。

```python
import redis
import json

class CachedEvaluator:
    """キャッシュ付き評価器"""

    def __init__(self):
        self.evaluator = EvaluatorService()
        self.cache = redis.Redis(host='localhost', port=6379, db=0)

    def evaluate_test_case(self, test_case, system_output):
        # キャッシュキーの生成
        cache_key = self._generate_cache_key(test_case["id"], system_output)

        # キャッシュチェック
        cached = self.cache.get(cache_key)
        if cached:
            return json.loads(cached)

        # 評価実行
        result = self.evaluator.evaluate_test_case(test_case, system_output)

        # キャッシュに保存（24時間有効）
        self.cache.setex(
            cache_key,
            86400,
            json.dumps(result, default=str)
        )

        return result

    def _generate_cache_key(self, test_case_id, system_output):
        """キャッシュキーを生成"""
        data = f"{test_case_id}::{system_output}"
        return hashlib.sha256(data.encode()).hexdigest()
```

## 冪等性メトリクスの記録

### MLflowへの記録

```python
# app/services/idempotency_checker.py
def check_idempotency(self, test_case, system_output, num_runs=3):
    result = self._perform_check(...)

    # MLflowに記録
    with mlflow.start_run(run_name=f"Idempotency_{test_case['id']}"):
        mlflow.log_params({
            "test_case_id": test_case["id"],
            "num_runs": num_runs
        })

        mlflow.log_metrics({
            "is_idempotent": int(result.is_idempotent),
            "variance_score": result.variance_score
        })

        mlflow.log_text(result.message, "idempotency_message.txt")
        mlflow.log_dict(result.executions, "executions.json")

    return result
```

### データベースへの記録（モデル・バージョン情報付き）

```python
# idempotency_checks テーブルに保存（拡張版）
def save_idempotency_check(self, result: IdempotencyCheckResult):
    model_key = self.get_model_version_key()

    self.repository.save_idempotency_check({
        "input_hash": result.input_hash,
        "test_case_id": result.test_case_id,
        "is_idempotent": result.is_idempotent,
        "variance_score": result.variance_score,
        "executions": json.dumps(result.executions),
        "message": result.message,

        # モデル・バージョン情報（重要！）
        "model_version_key": model_key,
        "provider": self.judge_config.provider,
        "model_name": self.judge_config.model_name,
        "model_version": self.judge_config.model_version,
        "temperature": self.judge_config.temperature,
        "seed": self.judge_config.seed,
        "prompt_version": self.judge_config.prompt_version
    })
```

### モデル・バージョン別の冪等性照会

```python
def get_idempotency_status(
    self,
    test_case_id: str,
    model_version_key: str
) -> Optional[IdempotencyCheckResult]:
    """
    特定のモデル・バージョンでの冪等性検証結果を取得

    Args:
        test_case_id: テストケースID
        model_version_key: モデル・バージョン識別子

    Returns:
        過去の検証結果。未検証の場合はNone
    """
    return self.repository.get_idempotency_check_by_model(
        test_case_id=test_case_id,
        model_version_key=model_version_key
    )
```

## ベストプラクティス

### 1. 定期的なチェック
毎週または毎月、すべてのテストケースの冪等性をチェックする。

### 2. 閾値の設定
冪等性の判定閾値（例: 90%）を明確にし、プロジェクトの要件に合わせる。

### 3. アラート設定
冪等性が保たれない場合、開発チームに通知する。

### 4. ドキュメント化
冪等性が保たれない既知のケースをドキュメント化する。

## トラブルシューティング

### 問題: 常に異なる結果が返される
- LLMの`temperature`が0でない可能性
- `seed`パラメータが正しく設定されていない
- プロンプトに曖昧な要素が含まれている

### 問題: 時々異なる結果が返される
- LLMプロバイダーのAPIの制約
- ネットワークエラーや再試行による影響
- キャッシングの実装を検討

### 問題: 冪等性チェックに時間がかかる
- 並列実行の導入
- チェック頻度の調整
- num_runsの削減（3回 → 2回）
