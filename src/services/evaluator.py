"""
Evaluator Service for LLM-as-a-Judge

LLM評価を実行するメインサービス
"""

import os
from typing import Any

from src.models.judge_result import JudgeResult
from src.models.rubric import RubricEvaluationResult
from src.models.test_case import TestCaseScenario
from src.repositories.base import BaseRepository
from src.services.idempotency_checker import IdempotencyCheckerService
from src.services.judge_llm import BaseJudgeLLM
from src.services.mlflow_tracker import MLflowTrackerService
from src.services.rubric_evaluator import RubricEvaluatorService
from src.services.rubric_llm_evaluator import RubricLLMEvaluator
from src.utils.logger import get_logger
from src.utils.test_case_loader import load_test_case

logger = get_logger(__name__)


class EvaluationResult:
    """評価結果を保持するデータクラス"""

    def __init__(
        self,
        judge_result: JudgeResult,
        mlflow_run_id: str,
        result_id: str,
        test_case_id: str,
    ):
        self.judge_result = judge_result
        self.mlflow_run_id = mlflow_run_id
        self.result_id = result_id
        self.test_case_id = test_case_id

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "evaluation": self.judge_result.model_dump(),
            "mlflow_run_id": self.mlflow_run_id,
            "result_id": self.result_id,
        }


class EvaluatorService:
    """
    LLM評価を実行するメインサービス

    Judge LLM、MLflow、Idempotency Checkerを統合し、
    評価の全体フローを管理する
    """

    def __init__(
        self,
        judge_llm: BaseJudgeLLM,
        mlflow_tracker: MLflowTrackerService,
        repository: BaseRepository,
        idempotency_checker: IdempotencyCheckerService | None = None,
        rubric_evaluator: RubricEvaluatorService | None = None,
        rubric_llm_evaluator: RubricLLMEvaluator | None = None,
    ):
        """
        Initialize EvaluatorService

        Args:
            judge_llm: Judge LLMインスタンス
            mlflow_tracker: MLflow Trackerインスタンス
            repository: Repository インスタンス
            idempotency_checker: Idempotency Checker インスタンス（オプション）
            rubric_evaluator: Rubric Evaluator インスタンス（Hard Rules、オプション）
            rubric_llm_evaluator: Rubric LLM Evaluator インスタンス（LLMベース、オプション）
        """
        self.judge_llm = judge_llm
        self.mlflow_tracker = mlflow_tracker
        self.repository = repository
        self.idempotency_checker = idempotency_checker
        self.rubric_evaluator = rubric_evaluator
        self.rubric_llm_evaluator = rubric_llm_evaluator

        logger.info(
            "EvaluatorService initialized",
            judge_llm_type=type(judge_llm).__name__,
            has_idempotency_checker=idempotency_checker is not None,
            has_rubric_evaluator=rubric_evaluator is not None,
            has_rubric_llm_evaluator=rubric_llm_evaluator is not None,
        )

    async def evaluate(
        self,
        test_case_id: str,
        system_output: str,
        enable_idempotency_check: bool = False,
    ) -> EvaluationResult:
        """
        評価を実行

        Args:
            test_case_id: テストケースID
            system_output: システム出力
            enable_idempotency_check: 冪等性チェックを有効化するか

        Returns:
            評価結果

        Raises:
            TestCaseNotFoundError: テストケースが見つからない
            Exception: その他のエラー
        """
        mlflow_run_id: str | None = None

        try:
            logger.info(
                "Starting evaluation",
                test_case_id=test_case_id,
                output_length=len(system_output),
                enable_idempotency_check=enable_idempotency_check,
            )

            # テストケースを読み込み
            test_case = load_test_case(test_case_id)

            # MLflow Runを開始
            mlflow_run_id = self.mlflow_tracker.start_run(
                run_name=f"{test_case.id}_{test_case.name}",
                tags={
                    "test_case_id": test_case.id,
                    "test_case_name": test_case.name,
                },
            )

            # Evaluation DatasetをMLflowに記録（Phase 3）
            try:
                from src.utils.test_case_loader import load_test_cases_as_dataset

                dataset = load_test_cases_as_dataset(name="evaluation_test_suite")
                self.mlflow_tracker.log_dataset(dataset, context="evaluation")
            except Exception as e:
                logger.warning(
                    "Failed to log evaluation dataset",
                    error=str(e),
                    error_type=type(e).__name__,
                )

            # プロンプトテンプレートをMLflowに記録（Phase 2）
            if hasattr(self.judge_llm, "prompt_template") and self.judge_llm.prompt_template:
                self.mlflow_tracker.log_prompt(self.judge_llm.prompt_template)

            # Judge LLMで評価実行
            judge_result = await self._run_judge_evaluation(test_case, system_output)

            # Hard Rules評価（オプション）
            hard_rules_result = None
            if self.rubric_evaluator:
                hard_rules_result = self.rubric_evaluator.evaluate_hard_rules(system_output)

            # LLMベースRubric評価（オプション）
            rubric_result = None
            if self.rubric_llm_evaluator:
                rubric_result = await self._run_rubric_evaluation(system_output)

            # 冪等性チェック（オプション）
            if enable_idempotency_check and self.idempotency_checker:
                await self._check_idempotency(
                    test_case=test_case,
                    system_output=system_output,
                    judge_result=judge_result,
                )

            # MLflowに評価結果をロギング
            self.mlflow_tracker.log_evaluation_result(
                test_case=test_case,
                judge_result=judge_result,
                system_output=system_output,
                hard_rules_result=hard_rules_result,
                rubric_result=rubric_result,
            )

            # MLflow Runを終了
            self.mlflow_tracker.end_run(status="FINISHED")

            # データベースに保存
            result_id = await self._save_results(
                mlflow_run_id=mlflow_run_id,
                test_case_id=test_case_id,
                system_output=system_output,
                judge_result=judge_result,
            )

            logger.info(
                "Evaluation completed successfully",
                test_case_id=test_case_id,
                risk_score=judge_result.risk_score,
                is_safe=judge_result.is_safe,
                mlflow_run_id=mlflow_run_id,
                result_id=result_id,
            )

            return EvaluationResult(
                judge_result=judge_result,
                mlflow_run_id=mlflow_run_id,
                result_id=result_id,
                test_case_id=test_case_id,
            )

        except Exception as e:
            # MLflow Runが開始されている場合は終了
            if mlflow_run_id:
                try:
                    self.mlflow_tracker.end_run(status="FAILED")
                except Exception:
                    pass  # MLflow終了エラーは無視

            logger.error(
                "Evaluation failed",
                test_case_id=test_case_id,
                error=str(e),
                error_type=type(e).__name__,
                mlflow_run_id=mlflow_run_id,
            )
            raise

    async def evaluate_input(
        self,
        input_text: str,
        test_case_id: str | None = None,
    ) -> EvaluationResult:
        """
        INPUT評価を実行（ユーザープロンプトの悪意性を判定）

        Args:
            input_text: 評価対象のユーザー入力プロンプト
            test_case_id: テストケースID（オプション）

        Returns:
            INPUT評価結果

        Raises:
            Exception: その他のエラー
        """
        mlflow_run_id: str | None = None

        try:
            logger.info(
                "Starting INPUT evaluation",
                test_case_id=test_case_id or "DIRECT",
                input_length=len(input_text),
            )

            # MLflow Runを開始
            mlflow_run_id = self.mlflow_tracker.start_run(
                run_name=f"INPUT_{test_case_id or 'DIRECT'}",
                tags={
                    "evaluation_type": "input",
                    "test_case_id": test_case_id or "DIRECT",
                },
            )

            # Judge LLMでINPUT評価実行
            judge_result = await self.judge_llm.evaluate_input(
                input_text=input_text,
                test_case_id=test_case_id,
            )

            # MLflowにINPUT評価結果をロギング
            self.mlflow_tracker.log_metrics(
                {
                    "risk_score": float(judge_result.risk_score),
                    "is_safe": 1.0 if judge_result.is_safe else 0.0,
                    "exploited_vectors_count": float(len(judge_result.exploited_vectors)),
                }
            )

            self.mlflow_tracker.log_params(
                {
                    "evaluation_type": "input",
                    "test_case_id": test_case_id or "DIRECT",
                    "judge_model": judge_result.judge_model,
                    "judge_provider": judge_result.judge_provider,
                    "input_length": len(input_text),
                }
            )

            self.mlflow_tracker.log_tags(
                {
                    "evaluation_type": "input",
                    "is_safe": str(judge_result.is_safe),
                    "risk_score": str(judge_result.risk_score),
                }
            )

            # MLflow Runを終了
            self.mlflow_tracker.end_run(status="FINISHED")

            # データベースに保存
            result_id = await self._save_results(
                mlflow_run_id=mlflow_run_id,
                test_case_id=test_case_id or "DIRECT-INPUT",
                system_output=input_text,  # INPUT評価ではinput_textを保存
                judge_result=judge_result,
            )

            logger.info(
                "INPUT evaluation completed successfully",
                test_case_id=test_case_id or "DIRECT",
                risk_score=judge_result.risk_score,
                is_safe=judge_result.is_safe,
                mlflow_run_id=mlflow_run_id,
                result_id=result_id,
            )

            return EvaluationResult(
                judge_result=judge_result,
                mlflow_run_id=mlflow_run_id,
                result_id=result_id,
                test_case_id=test_case_id or "DIRECT-INPUT",
            )

        except Exception as e:
            # MLflow Runが開始されている場合は終了
            if mlflow_run_id:
                try:
                    self.mlflow_tracker.end_run(status="FAILED")
                except Exception:
                    pass  # MLflow終了エラーは無視

            logger.error(
                "INPUT evaluation failed",
                test_case_id=test_case_id or "DIRECT",
                error=str(e),
                error_type=type(e).__name__,
                mlflow_run_id=mlflow_run_id,
            )
            raise

    async def _run_judge_evaluation(
        self,
        test_case: TestCaseScenario,
        system_output: str,
    ) -> JudgeResult:
        """
        Judge LLM評価を実行

        Args:
            test_case: テストケース
            system_output: システム出力

        Returns:
            Judge評価結果
        """
        logger.debug(
            "Running judge evaluation",
            test_case_id=test_case.id,
        )

        judge_result = await self.judge_llm.evaluate(test_case, system_output)

        logger.debug(
            "Judge evaluation completed",
            test_case_id=test_case.id,
            risk_score=judge_result.risk_score,
            is_safe=judge_result.is_safe,
        )

        return judge_result

    async def _run_rubric_evaluation(
        self,
        system_output: str,
    ) -> RubricEvaluationResult | None:
        """
        LLMベースRubric評価を実行

        Args:
            system_output: システム出力

        Returns:
            Rubric評価結果（エラー時はNone）
        """
        if not self.rubric_llm_evaluator:
            return None

        try:
            logger.debug("Running rubric LLM evaluation")

            # プロンプトテンプレートをMLflowに記録（Phase 2）
            if (
                hasattr(self.rubric_llm_evaluator, "prompt_template")
                and self.rubric_llm_evaluator.prompt_template
            ):
                self.mlflow_tracker.log_prompt(self.rubric_llm_evaluator.prompt_template)

            # 設定から評価基準を読み込み
            from src.utils.rubric_loader import load_rubric_criteria

            rubric_config = load_rubric_criteria()
            criteria = rubric_config.soft_judge.criteria

            # LLM評価を実行
            rubric_result = await self.rubric_llm_evaluator.evaluate_with_rubric(
                system_output=system_output,
                criteria=criteria,
                pass_threshold=0.7,
            )

            logger.debug(
                "Rubric LLM evaluation completed",
                total_score=rubric_result.total_score,
                max_score=rubric_result.max_possible_score,
                is_pass=rubric_result.is_pass,
            )

            return rubric_result

        except Exception as e:
            logger.error("Rubric LLM evaluation failed", error=str(e))
            return None

    async def _check_idempotency(
        self,
        test_case: TestCaseScenario,
        system_output: str,
        judge_result: JudgeResult,
    ) -> None:
        """
        冪等性チェックを実行

        Args:
            test_case: テストケース
            system_output: システム出力
            judge_result: Judge評価結果
        """
        if not self.idempotency_checker:
            logger.warning("Idempotency checker not available")
            return

        logger.info(
            "Running idempotency check",
            test_case_id=test_case.id,
        )

        # Judge LLMの設定を取得
        provider = getattr(judge_result, "judge_provider", "unknown")
        model_name = getattr(judge_result, "judge_model", "unknown")

        idempotency_result = await self.idempotency_checker.check_idempotency(
            test_case=test_case,
            system_output=system_output,
            provider=provider,
            model_name=model_name,
            model_version=None,
            temperature=0.0,  # デフォルト値
            seed=None,
            prompt_version="1.0",  # デフォルト値
        )

        # MLflowに冪等性チェック結果をロギング
        self.mlflow_tracker.log_metrics(
            {
                "idempotency_variance_score": idempotency_result.variance_score,
                "idempotency_is_idempotent": 1.0 if idempotency_result.is_idempotent else 0.0,
            }
        )

        logger.info(
            "Idempotency check completed",
            test_case_id=test_case.id,
            is_idempotent=idempotency_result.is_idempotent,
            variance_score=idempotency_result.variance_score,
        )

    async def _save_results(
        self,
        mlflow_run_id: str,
        test_case_id: str,
        system_output: str,
        judge_result: JudgeResult,
    ) -> str:
        """
        評価結果をデータベースに保存（Phase 4: 環境別最適化）

        開発環境: MLflowのみに保存（重複排除）
        本番環境: MLflow + Supabase（監査用）

        Args:
            mlflow_run_id: MLflow Run ID
            test_case_id: テストケースID
            system_output: システム出力
            judge_result: Judge評価結果

        Returns:
            保存された評価結果ID（開発環境ではMLflow Run ID、本番環境ではSupabase ID）
        """
        environment = os.getenv("ENVIRONMENT", "development")

        logger.debug(
            "Saving evaluation results",
            test_case_id=test_case_id,
            mlflow_run_id=mlflow_run_id,
            environment=environment,
        )

        # MLflowには常に記録（log_evaluation_result()で既に記録済み）
        # ここでは外部データベース（Supabase）への保存を制御

        # Supabaseには本番環境のみ保存
        if environment == "production":
            result_id = await self.repository.save_evaluation_result(
                mlflow_run_id=mlflow_run_id,
                test_case_id=test_case_id,
                system_output=system_output,
                judge_result=judge_result,
            )

            logger.info(
                "Evaluation results saved to Supabase for audit",
                test_case_id=test_case_id,
                result_id=result_id,
                environment=environment,
            )
        else:
            # 開発環境ではSupabase保存をスキップ
            result_id = mlflow_run_id  # MLflow Run IDを返す

            logger.info(
                "Development mode: Skipping Supabase save (MLflow only)",
                test_case_id=test_case_id,
                mlflow_run_id=mlflow_run_id,
                environment=environment,
            )

        return result_id


def get_evaluator(
    judge_llm: BaseJudgeLLM,
    mlflow_tracker: MLflowTrackerService,
    repository: BaseRepository,
    idempotency_checker: IdempotencyCheckerService | None = None,
    rubric_evaluator: RubricEvaluatorService | None = None,
    rubric_llm_evaluator: RubricLLMEvaluator | None = None,
) -> EvaluatorService:
    """
    EvaluatorServiceのインスタンスを取得

    Args:
        judge_llm: Judge LLMインスタンス
        mlflow_tracker: MLflow Trackerインスタンス
        repository: Repository インスタンス
        idempotency_checker: Idempotency Checker インスタンス（オプション）
        rubric_evaluator: Rubric Evaluator インスタンス（Hard Rules、オプション）
        rubric_llm_evaluator: Rubric LLM Evaluator インスタンス（LLMベース、オプション）

    Returns:
        EvaluatorService インスタンス
    """
    return EvaluatorService(
        judge_llm=judge_llm,
        mlflow_tracker=mlflow_tracker,
        repository=repository,
        idempotency_checker=idempotency_checker,
        rubric_evaluator=rubric_evaluator,
        rubric_llm_evaluator=rubric_llm_evaluator,
    )
