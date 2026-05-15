"""
Mock MLflow Tracker for Testing

テスト用MLflowトラッカーモック実装
"""

from typing import Any
from uuid import uuid4

from src.models.judge_result import JudgeResult
from src.models.test_case import TestCaseScenario
from src.services.mlflow_tracker import MLflowTrackerService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MockMLflowTracker(MLflowTrackerService):
    """MLflowトラッカーのモック実装（テスト用）

    実際のMLflowサーバーに接続せず、メモリ内でRunを管理する。
    E2Eテストやユニットテストで使用。
    """

    def __init__(self) -> None:
        """Initialize mock MLflow tracker"""
        self._runs: dict[str, dict[str, Any]] = {}
        self._current_run_id: str | None = None

    def start_run(self, run_name: str | None = None, tags: dict[str, Any] | None = None) -> str:
        """MLflow Runを開始（モック）

        Args:
            run_name: Run名
            tags: タグ

        Returns:
            Run ID
        """
        run_id = f"mock_run_{uuid4().hex[:8]}"
        self._current_run_id = run_id

        self._runs[run_id] = {
            "run_id": run_id,
            "run_name": run_name or f"run_{run_id}",
            "tags": tags or {},
            "params": {},
            "metrics": {},
            "artifacts": {},
            "status": "RUNNING",
        }

        logger.info(
            "Mock MLflow run started",
            run_id=run_id,
            run_name=run_name,
        )

        return run_id

    def log_param(self, key: str, value: Any) -> None:
        """パラメータをログ（モック）

        Args:
            key: パラメータキー
            value: パラメータ値
        """
        if self._current_run_id:
            self._runs[self._current_run_id]["params"][key] = value

    def log_metric(self, key: str, value: float) -> None:
        """メトリクスをログ（モック）

        Args:
            key: メトリクスキー
            value: メトリクス値
        """
        if self._current_run_id:
            self._runs[self._current_run_id]["metrics"][key] = value

    def log_artifact(self, local_path: str, artifact_path: str | None = None) -> None:
        """アーティファクトをログ（モック）

        Args:
            local_path: ローカルファイルパス
            artifact_path: アーティファクトパス
        """
        if self._current_run_id:
            key = artifact_path or local_path
            self._runs[self._current_run_id]["artifacts"][key] = local_path

    def log_text(self, text: str, artifact_file: str) -> None:
        """テキストをアーティファクトとしてログ（モック）

        Args:
            text: テキスト内容
            artifact_file: アーティファクトファイル名
        """
        if self._current_run_id:
            self._runs[self._current_run_id]["artifacts"][artifact_file] = text

    def log_dict(self, dictionary: dict[str, Any], artifact_file: str) -> None:
        """辞書をアーティファクトとしてログ（モック）

        Args:
            dictionary: 辞書データ
            artifact_file: アーティファクトファイル名
        """
        if self._current_run_id:
            self._runs[self._current_run_id]["artifacts"][artifact_file] = dictionary

    def set_tag(self, key: str, value: str) -> None:
        """タグを設定（モック）

        Args:
            key: タグキー
            value: タグ値
        """
        if self._current_run_id:
            self._runs[self._current_run_id]["tags"][key] = value

    def end_run(self, status: str = "FINISHED") -> None:
        """MLflow Runを終了（モック）

        Args:
            status: 終了ステータス（FINISHED/FAILED）
        """
        if self._current_run_id:
            self._runs[self._current_run_id]["status"] = status
            logger.info(
                "Mock MLflow run ended",
                run_id=self._current_run_id,
                status=status,
            )
            self._current_run_id = None

    def log_evaluation_result(
        self,
        test_case: TestCaseScenario,
        judge_result: JudgeResult,
        system_output: str,
    ) -> None:
        """評価結果をMLflowにログ（モック）

        Args:
            test_case: テストケース
            judge_result: Judge LLM評価結果
            system_output: 対象AIシステムの出力
        """
        if not self._current_run_id:
            return

        # Log parameters
        self.log_param("test_case_id", test_case.id)
        self.log_param("test_case_name", test_case.name)
        self.log_param("private_data_access", test_case.lethal_trifecta_vectors.private_data_access)
        self.log_param(
            "untrusted_content_exposure",
            test_case.lethal_trifecta_vectors.untrusted_content_exposure,
        )
        self.log_param(
            "external_communication", test_case.lethal_trifecta_vectors.external_communication
        )

        # Log metrics
        self.log_metric("risk_score", float(judge_result.risk_score))
        self.log_metric("is_safe", 1.0 if judge_result.is_safe else 0.0)
        self.log_metric("exploited_vectors_count", float(len(judge_result.exploited_vectors)))

        # Log tags
        self.set_tag("is_safe", str(judge_result.is_safe))
        self.set_tag("risk_level", f"risk_{judge_result.risk_score}")
        for vector in judge_result.exploited_vectors:
            self.set_tag(f"exploited_{vector.replace(' ', '_').lower()}", "true")

        # Log artifacts
        self.log_text(judge_result.reasoning, "reasoning.txt")
        self.log_text(judge_result.recommendation, "recommendation.txt")
        self.log_text(system_output, "system_output.txt")

        logger.info(
            "Mock evaluation result logged to MLflow",
            run_id=self._current_run_id,
            risk_score=judge_result.risk_score,
            is_safe=judge_result.is_safe,
        )

    # Utility methods for testing

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Runを取得（テスト用）

        Args:
            run_id: Run ID

        Returns:
            Run情報
        """
        return self._runs.get(run_id)

    def clear(self) -> None:
        """全Runをクリア（テスト用）"""
        self._runs.clear()
        self._current_run_id = None
