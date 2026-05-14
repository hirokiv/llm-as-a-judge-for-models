"""
MLflow tracking service for evaluation results

評価結果をMLflowに記録するサービス
"""

import os
import tempfile
from pathlib import Path
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

from src.models.judge_result import JudgeResult
from src.models.test_case import TestCaseScenario
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MLflowTrackerService:
    """
    MLflow tracking service for managing evaluation experiments

    評価実験を管理するMLflowトラッキングサービス
    """

    def __init__(
        self,
        tracking_uri: str | None = None,
        experiment_name: str = "llm-judge-evaluations",
    ):
        """
        Initialize MLflow tracker service

        Args:
            tracking_uri: MLflow tracking URI（None の場合は環境変数から取得）
            experiment_name: 実験名
        """
        self.tracking_uri: str = (
            tracking_uri
            or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
            or "http://localhost:5000"
        )
        self.experiment_name = experiment_name

        # MLflow設定
        mlflow.set_tracking_uri(self.tracking_uri)
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

        # 実験を作成または取得
        self.experiment_id = self._get_or_create_experiment()

        logger.info(
            "Initialized MLflowTrackerService",
            tracking_uri=self.tracking_uri,
            experiment_name=self.experiment_name,
            experiment_id=self.experiment_id,
        )

    def _get_or_create_experiment(self) -> str:
        """
        実験を取得または作成

        Returns:
            実験ID
        """
        experiment = mlflow.get_experiment_by_name(self.experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(self.experiment_name)
            logger.info("Created MLflow experiment", experiment_id=experiment_id)
        else:
            experiment_id = experiment.experiment_id
            logger.info("Using existing MLflow experiment", experiment_id=experiment_id)

        return experiment_id

    def start_run(
        self,
        run_name: str | None = None,
        tags: dict[str, Any] | None = None,
    ) -> str:
        """
        MLflow Runを開始

        Args:
            run_name: Run名（オプション）
            tags: タグ辞書（オプション）

        Returns:
            Run ID
        """
        run = mlflow.start_run(
            experiment_id=self.experiment_id,
            run_name=run_name,
            tags=tags,
        )
        run_id: str = str(run.info.run_id)

        logger.info(
            "Started MLflow run",
            run_id=run_id,
            run_name=run_name,
        )

        return run_id

    def end_run(self, status: str = "FINISHED") -> None:
        """
        MLflow Runを終了

        Args:
            status: Run のステータス（FINISHED, FAILED, KILLED）
        """
        active_run = mlflow.active_run()
        run_id = active_run.info.run_id if active_run else None
        mlflow.end_run(status=status)

        logger.info(
            "Ended MLflow run",
            run_id=run_id,
            status=status,
        )

    def log_evaluation_result(
        self,
        test_case: TestCaseScenario,
        judge_result: JudgeResult,
        system_output: str,
    ) -> None:
        """
        評価結果をMLflowに記録

        Args:
            test_case: テストケースシナリオ
            judge_result: Judge評価結果
            system_output: システム出力
        """
        # Parameters をロギング
        self.log_params(
            {
                "test_case_id": test_case.id,
                "test_case_name": test_case.name,
                "judge_model": judge_result.judge_model or "unknown",
                "judge_provider": judge_result.judge_provider or "unknown",
                "private_data_access": test_case.lethal_trifecta_vectors.private_data_access,
                "untrusted_content_exposure": test_case.lethal_trifecta_vectors.untrusted_content_exposure,
                "external_communication": test_case.lethal_trifecta_vectors.external_communication,
            }
        )

        # Metrics をロギング
        self.log_metrics(
            {
                "risk_score": float(judge_result.risk_score),
                "is_safe": 1.0 if judge_result.is_safe else 0.0,
                "exploited_vectors_count": float(len(judge_result.exploited_vectors)),
            }
        )

        # Tags をロギング
        self.log_tags(
            {
                "exploited_vectors": ", ".join(judge_result.exploited_vectors)
                if judge_result.exploited_vectors
                else "none",
                "environment": os.getenv("ENVIRONMENT", "development"),
            }
        )

        # Artifacts をロギング（テキストファイル）
        self._log_text_artifacts(
            {
                "system_output.txt": system_output,
                "reasoning.txt": judge_result.reasoning,
                "recommendation.txt": judge_result.recommendation,
            }
        )

        logger.info(
            "Logged evaluation result to MLflow",
            test_case_id=test_case.id,
            risk_score=judge_result.risk_score,
            is_safe=judge_result.is_safe,
        )

    def log_params(self, params: dict[str, Any]) -> None:
        """
        パラメータをロギング

        Args:
            params: パラメータ辞書
        """
        for key, value in params.items():
            mlflow.log_param(key, value)

    def log_metrics(self, metrics: dict[str, float]) -> None:
        """
        メトリクスをロギング

        Args:
            metrics: メトリクス辞書
        """
        for key, value in metrics.items():
            mlflow.log_metric(key, value)

    def log_tags(self, tags: dict[str, str]) -> None:
        """
        タグをロギング

        Args:
            tags: タグ辞書
        """
        mlflow.set_tags(tags)

    def _log_text_artifacts(self, artifacts: dict[str, str]) -> None:
        """
        テキストアーティファクトをロギング

        Args:
            artifacts: アーティファクト辞書（ファイル名: 内容）
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            for filename, content in artifacts.items():
                filepath = tmpdir_path / filename
                filepath.write_text(content, encoding="utf-8")
                mlflow.log_artifact(str(filepath))

    def get_run_by_id(self, run_id: str) -> Any:
        """
        Run IDでRunを取得

        Args:
            run_id: Run ID

        Returns:
            MLflow Run オブジェクト
        """
        return self.client.get_run(run_id)

    def search_runs(
        self,
        filter_string: str = "",
        max_results: int = 100,
    ) -> list[Any]:
        """
        条件でRunを検索

        Args:
            filter_string: フィルタ文字列（例: "params.test_case_id = 'TEST-LT-001'"）
            max_results: 最大取得件数

        Returns:
            Run のリスト
        """
        runs = mlflow.search_runs(
            experiment_ids=[self.experiment_id],
            filter_string=filter_string,
            max_results=max_results,
        )
        # mlflow.search_runs returns pandas DataFrame
        return runs.to_dict("records") if not runs.empty else []  # type: ignore[union-attr]


def get_mlflow_tracker() -> MLflowTrackerService:
    """
    MLflow tracker サービスのシングルトンインスタンスを取得

    Returns:
        MLflowTrackerService インスタンス
    """
    return MLflowTrackerService()
