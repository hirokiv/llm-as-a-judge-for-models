"""
Idempotency Checker service for LLM evaluation consistency

LLM評価の冪等性（一貫性）をチェックするサービス
"""

import hashlib

from src.models.idempotency import ExecutionDetail, IdempotencyCheckResult
from src.models.judge_result import JudgeResult
from src.models.test_case import TestCaseScenario
from src.services.judge_llm import BaseJudgeLLM
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IdempotencyCheckerService:
    """
    LLM評価の冪等性をチェックするサービス

    同一の入力に対して複数回評価を実行し、出力の一貫性を検証する
    """

    def __init__(self, judge_llm: BaseJudgeLLM, num_runs: int = 3):
        """
        Initialize idempotency checker service

        Args:
            judge_llm: Judge LLMインスタンス
            num_runs: 実行回数（デフォルト: 3回）
        """
        self.judge_llm = judge_llm
        self.num_runs = num_runs

        logger.info(
            "Initialized IdempotencyCheckerService",
            num_runs=num_runs,
        )

    async def check_idempotency(
        self,
        test_case: TestCaseScenario,
        system_output: str,
        provider: str,
        model_name: str,
        model_version: str | None,
        temperature: float,
        seed: int | None,
        prompt_version: str,
    ) -> IdempotencyCheckResult:
        """
        冪等性をチェック

        Args:
            test_case: テストケースシナリオ
            system_output: システム出力
            provider: LLMプロバイダー
            model_name: モデル名
            model_version: モデルバージョン
            temperature: temperature設定
            seed: seed値
            prompt_version: プロンプトバージョン

        Returns:
            冪等性チェック結果
        """
        logger.info(
            "Starting idempotency check",
            test_case_id=test_case.id,
            num_runs=self.num_runs,
            provider=provider,
            model_name=model_name,
        )

        # 入力ハッシュを生成
        input_hash = self._generate_input_hash(test_case.id, system_output)

        # モデルバージョンキーを生成
        model_version_key = self._generate_model_version_key(
            provider=provider,
            model_name=model_name,
            model_version=model_version,
            temperature=temperature,
            seed=seed,
            prompt_version=prompt_version,
        )

        # 複数回実行
        executions: list[ExecutionDetail] = []
        results: list[JudgeResult] = []

        for run_number in range(1, self.num_runs + 1):
            try:
                result = await self.judge_llm.evaluate(test_case, system_output)
                results.append(result)

                execution = ExecutionDetail(
                    run_number=run_number,
                    is_safe=result.is_safe,
                    risk_score=result.risk_score,
                    exploited_vectors=result.exploited_vectors,
                    reasoning=result.reasoning,
                    recommendation=result.recommendation,
                )
                executions.append(execution)

                logger.debug(
                    "Completed execution",
                    run_number=run_number,
                    risk_score=result.risk_score,
                    is_safe=result.is_safe,
                )

            except Exception as e:
                logger.error(
                    "Execution failed",
                    run_number=run_number,
                    error=str(e),
                )
                raise

        # variance_scoreを計算
        variance_score = self._calculate_variance_score(results)

        # 冪等性を判定
        is_idempotent = variance_score >= 0.9

        # メッセージを生成
        if is_idempotent:
            message = (
                f"High consistency across {self.num_runs} runs "
                f"(variance_score: {variance_score:.2f})"
            )
        else:
            message = (
                f"Low consistency across {self.num_runs} runs "
                f"(variance_score: {variance_score:.2f}). "
                "Consider adjusting temperature or seed settings."
            )

        check_result = IdempotencyCheckResult(
            is_idempotent=is_idempotent,
            variance_score=variance_score,
            executions=executions,
            message=message,
        )

        logger.info(
            "Idempotency check completed",
            test_case_id=test_case.id,
            is_idempotent=is_idempotent,
            variance_score=variance_score,
            input_hash=input_hash,
            model_version_key=model_version_key,
        )

        return check_result

    def _generate_input_hash(self, test_case_id: str, system_output: str) -> str:
        """
        入力のハッシュ値を生成

        Args:
            test_case_id: テストケースID
            system_output: システム出力

        Returns:
            SHA-256ハッシュ値
        """
        input_str = f"{test_case_id}:{system_output}"
        return hashlib.sha256(input_str.encode()).hexdigest()

    def _generate_model_version_key(
        self,
        provider: str,
        model_name: str,
        model_version: str | None,
        temperature: float,
        seed: int | None,
        prompt_version: str,
    ) -> str:
        """
        モデルバージョンキーを生成

        Args:
            provider: LLMプロバイダー
            model_name: モデル名
            model_version: モデルバージョン
            temperature: temperature設定
            seed: seed値
            prompt_version: プロンプトバージョン

        Returns:
            モデルバージョンキー（例: "openai_gpt-4_v0.1_temp0.0_seed42_prompt1.0"）
        """
        version_str = model_version or "latest"
        seed_str = f"seed{seed}" if seed is not None else "noseed"
        temp_str = f"temp{temperature:.1f}"

        return f"{provider}_{model_name}_{version_str}_{temp_str}_{seed_str}_prompt{prompt_version}"

    def _calculate_variance_score(self, results: list[JudgeResult]) -> float:
        """
        複数実行結果のvariance_scoreを計算

        Args:
            results: Judge評価結果のリスト

        Returns:
            variance_score（0-1の範囲、1が完全一致）
        """
        if not results:
            return 0.0

        # risk_scoreの一致率を計算
        risk_scores = [r.risk_score for r in results]
        risk_score_consistency = len(set(risk_scores)) == 1

        # is_safeの一致率を計算
        is_safe_values = [r.is_safe for r in results]
        is_safe_consistency = len(set(is_safe_values)) == 1

        # exploited_vectorsの一致率を計算
        exploited_vectors_sets = [frozenset(r.exploited_vectors) for r in results]
        vectors_consistency = len(set(exploited_vectors_sets)) == 1

        # 総合スコアを計算（各要素の重み付け平均）
        # risk_score: 40%, is_safe: 40%, exploited_vectors: 20%
        score = (
            (1.0 if risk_score_consistency else 0.0) * 0.4
            + (1.0 if is_safe_consistency else 0.0) * 0.4
            + (1.0 if vectors_consistency else 0.0) * 0.2
        )

        return score


def get_idempotency_checker(
    judge_llm: BaseJudgeLLM,
    num_runs: int = 3,
) -> IdempotencyCheckerService:
    """
    IdempotencyCheckerServiceのインスタンスを取得

    Args:
        judge_llm: Judge LLMインスタンス
        num_runs: 実行回数

    Returns:
        IdempotencyCheckerService インスタンス
    """
    return IdempotencyCheckerService(judge_llm=judge_llm, num_runs=num_runs)
