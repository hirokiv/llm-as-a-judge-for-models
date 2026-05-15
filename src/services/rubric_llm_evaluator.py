"""
LLM-based Rubric Evaluator Service

LLMを使用した構造化Rubric評価サービス
"""

import json
import os
from typing import Any

import openai

from src.models.rubric import (
    CriterionEvaluationResult,
    RubricEvaluationResult,
    SoftJudgeCriterion,
)
from src.services.judge_llm import BaseJudgeLLM, OpenAIJudgeLLM
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RubricLLMEvaluator:
    """
    LLMベースのRubric評価サービス

    各評価項目（criterion）をLLMが個別に判定し、
    スコアを集計してRubric評価結果を生成します。
    """

    def __init__(self, judge_llm: BaseJudgeLLM):
        """
        Initialize RubricLLMEvaluator

        Args:
            judge_llm: Judge LLMインスタンス
        """
        self.judge_llm = judge_llm

        # OpenAI クライアントを設定
        if isinstance(judge_llm, OpenAIJudgeLLM):
            # OpenAIJudgeLLMの場合はそのクライアントを使用
            self.client = judge_llm.client
            self.model = judge_llm.model_config.get("name", "gpt-4")
            self.temperature = judge_llm.parameters.get("temperature", 0)
        else:
            # スタブまたは他の実装の場合は独自にOpenAIクライアントを作成
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = openai.AsyncOpenAI(api_key=api_key)
                self.model = "gpt-4"
                self.temperature = 0
                logger.info("RubricLLMEvaluator using independent OpenAI client")

                # MLflow Tracing を有効化（Phase 1: Best Practice実装）
                try:
                    import mlflow

                    mlflow.openai.autolog()
                    logger.info("MLflow OpenAI autolog enabled for RubricLLMEvaluator")
                except Exception as e:
                    logger.warning(f"Failed to enable MLflow autolog: {e}")
            else:
                self.client = None
                logger.warning("RubricLLMEvaluator initialized without OpenAI client (stub mode)")

        # MLflow Prompt Registry に登録（Phase 2: Best Practice実装）
        try:
            self.prompt_template = self._create_prompt_template()
            logger.info(
                "Rubric prompt template created",
                name=self.prompt_template.get("name"),
                version=self.prompt_template.get("version"),
            )
        except Exception as e:
            logger.warning(f"Failed to create rubric prompt template: {e}")
            self.prompt_template = None

        logger.info("RubricLLMEvaluator initialized")

    def _create_prompt_template(self) -> dict[str, Any]:
        """
        Prompt Registryに登録するPromptTemplateを作成（Rubric評価用）

        Returns:
            PromptTemplate辞書

        Note:
            MLflow Prompt Registryの仕様に準拠した形式で返す
        """
        # サンプルのプロンプトテンプレート（実際の評価で使用される形式）
        sample_template = """
以下のシステム出力を評価してください。

【評価項目】
{criterion_name}

【評価内容】
{criterion_description}

{criterion_requirement}

【システム出力】
\"\"\"
{system_output}
\"\"\"

【判定方法】
以下のJSON形式で回答してください：
{{
  "judgment": "Yes" or "Partial" or "No",
  "reasoning": "判定理由を簡潔に説明"
}}

- Yes: 評価基準を完全に満たしている
- Partial: 部分的に満たしている
- No: 満たしていない

評価タイプ: {criterion_type}
配点: {criterion_points}点
"""

        # プロンプトテンプレートのバージョンを生成
        prompt_version = "1.0.0"
        if hasattr(self, "model"):
            prompt_version = f"1.0.0-{self.model}"

        # PromptTemplateデータを作成
        prompt_template = {
            "name": "rubric_criterion_evaluation_prompt",
            "template": sample_template.strip(),
            "parameters": [
                {
                    "name": "criterion_name",
                    "description": "評価項目の名前",
                    "type": "string",
                },
                {
                    "name": "criterion_description",
                    "description": "評価項目の説明",
                    "type": "string",
                },
                {
                    "name": "criterion_requirement",
                    "description": "判定要件（オプション）",
                    "type": "string",
                },
                {
                    "name": "system_output",
                    "description": "評価対象のシステム出力",
                    "type": "string",
                },
                {
                    "name": "criterion_type",
                    "description": "評価タイプ（positive/negative）",
                    "type": "string",
                },
                {
                    "name": "criterion_points",
                    "description": "配点",
                    "type": "integer",
                },
            ],
            "version": prompt_version,
            "metadata": {
                "model": getattr(self, "model", "gpt-4"),
                "temperature": getattr(self, "temperature", 0),
                "purpose": "Rubric criterion evaluation for structured output assessment",
                "judgment_scale": "3-stage (Yes/Partial/No)",
            },
        }

        return prompt_template

    async def evaluate_with_rubric(
        self,
        system_output: str,
        criteria: list[SoftJudgeCriterion],
        pass_threshold: float = 0.7,
    ) -> RubricEvaluationResult:
        """
        Rubric評価を実行

        Args:
            system_output: 評価対象のシステム出力
            criteria: 評価基準リスト
            pass_threshold: 合格基準（0.0-1.0）

        Returns:
            Rubric評価結果
        """
        logger.info(
            "Starting rubric evaluation",
            criteria_count=len(criteria),
            output_length=len(system_output),
        )

        criteria_results = []
        total_score = 0
        max_possible_score = 0

        # 各評価項目を個別に評価
        for criterion in criteria:
            result = await self._evaluate_single_criterion(system_output, criterion)
            criteria_results.append(result)
            total_score += result.score
            max_possible_score += result.max_score

        # スコア率を計算
        score_rate = total_score / max_possible_score if max_possible_score > 0 else 0.0

        # 総合判定コメントを生成
        overall_judgment = self._generate_overall_judgment(
            criteria_results, score_rate, pass_threshold
        )

        rubric_result = RubricEvaluationResult(
            criteria_results=criteria_results,
            total_score=total_score,
            max_possible_score=max_possible_score,
            score_rate=score_rate,
            overall_judgment=overall_judgment,
            pass_threshold=pass_threshold,
        )

        logger.info(
            "Rubric evaluation completed",
            total_score=total_score,
            max_possible_score=max_possible_score,
            score_rate=f"{score_rate:.2%}",
            is_pass=rubric_result.is_pass,
        )

        return rubric_result

    async def _evaluate_single_criterion(
        self,
        system_output: str,
        criterion: SoftJudgeCriterion,
    ) -> CriterionEvaluationResult:
        """
        単一の評価項目を評価

        Args:
            system_output: システム出力
            criterion: 評価項目

        Returns:
            評価項目の結果
        """
        # プロンプトを構築
        evaluation_prompt = self._build_criterion_prompt(system_output, criterion)

        # LLMに評価を依頼
        try:
            response = await self._call_llm_for_criterion(evaluation_prompt)

            # レスポンスをパース
            judgment = response.get("judgment", "No")
            reasoning = response.get("reasoning", "判定理由が取得できませんでした")

            # スコア計算
            if criterion.type == "positive":
                # positive: Yes=満点、Partial=半分、No=0点
                if judgment == "Yes":
                    score = criterion.points
                elif judgment == "Partial":
                    score = criterion.points // 2
                else:
                    score = 0
            else:  # negative
                # negative: Yes=0点（減点）、Partial=半分減点、No=満点（減点なし）
                if judgment == "Yes":
                    score = 0
                elif judgment == "Partial":
                    score = criterion.points // 2
                else:
                    score = criterion.points

            result = CriterionEvaluationResult(
                criterion_id=criterion.criterion_id,
                name=criterion.name,
                description=criterion.description,
                judgment=judgment,  # type: ignore[arg-type]
                score=score,
                max_score=criterion.points,
                reasoning=reasoning,
                type=criterion.type,
            )

            logger.debug(
                "Criterion evaluated",
                criterion_id=criterion.criterion_id,
                judgment=judgment,
                score=score,
                max_score=criterion.points,
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to evaluate criterion",
                criterion_id=criterion.criterion_id,
                error=str(e),
            )

            # エラー時はNo判定として扱う
            return CriterionEvaluationResult(
                criterion_id=criterion.criterion_id,
                name=criterion.name,
                description=criterion.description,
                judgment="No",
                score=0,
                max_score=criterion.points,
                reasoning=f"評価中にエラーが発生しました: {str(e)}",
                type=criterion.type,
            )

    def _build_criterion_prompt(self, system_output: str, criterion: SoftJudgeCriterion) -> str:
        """
        評価項目用のプロンプトを構築

        Args:
            system_output: システム出力
            criterion: 評価項目

        Returns:
            プロンプト文字列
        """
        prompt = f"""
以下のシステム出力を評価してください。

【評価項目】
{criterion.name}

【評価内容】
{criterion.description}

{"【判定要件】" + chr(10) + criterion.requirement if criterion.requirement else ""}

【システム出力】
\"\"\"
{system_output}
\"\"\"

【判定方法】
以下のJSON形式で回答してください：
{{
  "judgment": "Yes" or "Partial" or "No",
  "reasoning": "判定理由を簡潔に説明"
}}

- Yes: 評価基準を完全に満たしている
- Partial: 部分的に満たしている
- No: 満たしていない

評価タイプ: {criterion.type}
配点: {criterion.points}点
"""
        return prompt.strip()

    async def _call_llm_for_criterion(self, prompt: str) -> dict[str, Any]:
        """
        LLMを呼び出して評価を取得

        Args:
            prompt: 評価プロンプト

        Returns:
            LLMの評価結果（辞書）
        """
        # OpenAIクライアントがない場合はスタブモード
        if self.client is None:
            logger.warning("No OpenAI client available, using stub judgment")
            return {"judgment": "Yes", "reasoning": "スタブモード: 評価スキップ"}

        try:
            # OpenAI API呼び出し
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはシステム出力を評価する専門家です。指定された評価基準に基づき、公平かつ正確に判定してください。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=500,
            )

            # レスポンスをパース
            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM returned empty response")

            # JSON部分を抽出（コードブロック対応）
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            result = json.loads(json_str)

            logger.debug(
                "LLM criterion evaluation completed",
                judgment=result.get("judgment"),
                tokens_used=response.usage.total_tokens if response.usage else None,
            )

            return result

        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            return {"judgment": "No", "reasoning": f"評価失敗: {str(e)}"}

    def _generate_overall_judgment(
        self,
        criteria_results: list[CriterionEvaluationResult],
        score_rate: float,
        pass_threshold: float,
    ) -> str:
        """
        総合判定コメントを生成

        Args:
            criteria_results: 各評価項目の結果
            score_rate: スコア率
            pass_threshold: 合格基準

        Returns:
            総合判定コメント
        """
        passed_count = sum(1 for r in criteria_results if r.judgment == "Yes")
        partial_count = sum(1 for r in criteria_results if r.judgment == "Partial")
        failed_count = sum(1 for r in criteria_results if r.judgment == "No")

        judgment = []
        judgment.append(f"スコア率: {score_rate:.1%}")
        judgment.append(
            f"評価結果: {passed_count}項目合格、{partial_count}項目部分合格、{failed_count}項目不合格"
        )

        if score_rate >= pass_threshold:
            judgment.append(f"✅ 合格基準（{pass_threshold:.0%}）を満たしています")
        else:
            judgment.append(f"❌ 合格基準（{pass_threshold:.0%}）を満たしていません")

        # 不合格項目の列挙
        failed_items = [r for r in criteria_results if r.judgment == "No"]
        if failed_items:
            judgment.append("\n改善が必要な項目:")
            for item in failed_items[:3]:  # 最大3項目まで
                judgment.append(f"  • {item.name}: {item.reasoning}")

        return "\n".join(judgment)


def get_rubric_llm_evaluator(judge_llm: BaseJudgeLLM) -> RubricLLMEvaluator:
    """
    RubricLLMEvaluatorインスタンスを取得

    Args:
        judge_llm: Judge LLMインスタンス

    Returns:
        RubricLLMEvaluator
    """
    return RubricLLMEvaluator(judge_llm)
