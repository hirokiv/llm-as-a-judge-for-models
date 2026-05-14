"""
Databricks Repository implementation for LLM-as-a-Judge

Databricks Delta Lakeを使用したデータアクセス層の実装（スタブ）
"""

from typing import Any

from src.models.idempotency import IdempotencyCheckResult
from src.models.judge_result import JudgeResult
from src.repositories.base import BaseRepository


class DatabricksRepository(BaseRepository):
    """Databricks Delta Lakeを使用したRepository実装（スタブ）

    Note:
        本番環境での使用を想定した実装。
        現在はスタブのみで、実際のDatabricks接続は未実装。
    """

    def __init__(
        self,
        server_hostname: str,
        http_path: str,
        access_token: str,
    ):
        """
        Args:
            server_hostname: Databricksサーバーホスト名
            http_path: SQLウェアハウスのHTTPパス
            access_token: アクセストークン
        """
        self.server_hostname = server_hostname
        self.http_path = http_path
        self.access_token = access_token

        # TODO: Databricks SQL Connectorの初期化
        # from databricks import sql
        # self.connection = sql.connect(
        #     server_hostname=server_hostname,
        #     http_path=http_path,
        #     access_token=access_token
        # )

    # Evaluation Results CRUD

    async def save_evaluation_result(
        self,
        mlflow_run_id: str,
        test_case_id: str,
        system_output: str,
        judge_result: JudgeResult,
    ) -> str:
        """評価結果を保存（スタブ）"""
        raise NotImplementedError("Databricks implementation is not yet available")

    async def get_evaluation_result(self, result_id: str) -> dict[str, Any] | None:
        """評価結果を取得（スタブ）"""
        raise NotImplementedError("Databricks implementation is not yet available")

    async def get_evaluation_result_by_mlflow_run_id(
        self, mlflow_run_id: str
    ) -> dict[str, Any] | None:
        """MLflow Run IDで評価結果を取得（スタブ）"""
        raise NotImplementedError("Databricks implementation is not yet available")

    async def list_evaluation_results(
        self,
        test_case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """評価結果の一覧を取得（スタブ）"""
        raise NotImplementedError("Databricks implementation is not yet available")

    # Idempotency Checks CRUD

    async def save_idempotency_check(
        self,
        input_hash: str,
        model_version_key: str,
        test_case_id: str,
        check_result: IdempotencyCheckResult,
        provider: str,
        model_name: str,
        model_version: str | None,
        temperature: float,
        seed: int | None,
        prompt_version: str,
    ) -> str:
        """冪等性チェック結果を保存（スタブ）"""
        raise NotImplementedError("Databricks implementation is not yet available")

    async def get_idempotency_check(
        self, model_version_key: str, input_hash: str
    ) -> dict[str, Any] | None:
        """冪等性チェック結果を取得（スタブ）"""
        raise NotImplementedError("Databricks implementation is not yet available")

    async def list_idempotency_checks(
        self,
        test_case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """冪等性チェック結果の一覧を取得（スタブ）"""
        raise NotImplementedError("Databricks implementation is not yet available")

    # Health Check

    async def health_check(self) -> bool:
        """データベース接続の健全性チェック（スタブ）"""
        raise NotImplementedError("Databricks implementation is not yet available")
