"""
In-Memory Repository for Testing

テスト用インメモリリポジトリ実装
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.models.idempotency import IdempotencyCheckResult
from src.models.judge_result import JudgeResult
from src.repositories.base import BaseRepository


class InMemoryRepository(BaseRepository):
    """インメモリリポジトリ（テスト用）

    データをメモリ内の辞書に保存するリポジトリ実装。
    E2Eテストやユニットテストで使用。
    """

    def __init__(self) -> None:
        """Initialize in-memory storage"""
        self._evaluation_results: dict[str, dict[str, Any]] = {}
        self._idempotency_checks: dict[str, dict[str, Any]] = {}

    # Evaluation Results CRUD

    async def save_evaluation_result(
        self,
        mlflow_run_id: str,
        test_case_id: str,
        system_output: str,
        judge_result: JudgeResult,
    ) -> str:
        """評価結果を保存

        Args:
            mlflow_run_id: MLflow Run ID
            test_case_id: テストケースID
            system_output: 対象AIシステムの出力
            judge_result: Judge LLMの評価結果

        Returns:
            保存されたレコードのID
        """
        result_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        self._evaluation_results[result_id] = {
            "id": result_id,
            "mlflow_run_id": mlflow_run_id,
            "test_case_id": test_case_id,
            "system_output": system_output,
            "judge_result": judge_result.model_dump(),
            "created_at": now,
            "updated_at": now,
        }

        return result_id

    async def get_evaluation_result(self, result_id: str) -> dict[str, Any] | None:
        """評価結果を取得

        Args:
            result_id: 評価結果ID

        Returns:
            評価結果の辞書、存在しない場合はNone
        """
        return self._evaluation_results.get(result_id)

    async def get_evaluation_result_by_mlflow_run_id(
        self, mlflow_run_id: str
    ) -> dict[str, Any] | None:
        """MLflow Run IDで評価結果を取得

        Args:
            mlflow_run_id: MLflow Run ID

        Returns:
            評価結果の辞書、存在しない場合はNone
        """
        for result in self._evaluation_results.values():
            if result["mlflow_run_id"] == mlflow_run_id:
                return result
        return None

    async def list_evaluation_results(
        self,
        test_case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """評価結果の一覧を取得

        Args:
            test_case_id: テストケースIDでフィルタ（オプション）
            limit: 取得件数の上限
            offset: オフセット

        Returns:
            評価結果の辞書のリスト
        """
        results = list(self._evaluation_results.values())

        # Filter by test_case_id if provided
        if test_case_id:
            results = [r for r in results if r["test_case_id"] == test_case_id]

        # Sort by created_at descending
        results.sort(key=lambda x: x["created_at"], reverse=True)

        # Apply pagination
        return results[offset : offset + limit]

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
        """冪等性チェック結果を保存

        Args:
            input_hash: 入力のハッシュ値
            model_version_key: モデルバージョンキー
            test_case_id: テストケースID
            check_result: 冪等性チェック結果
            provider: LLMプロバイダー
            model_name: モデル名
            model_version: モデルバージョン
            temperature: temperature
            seed: seed値
            prompt_version: プロンプトバージョン

        Returns:
            保存されたレコードのID
        """
        check_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        self._idempotency_checks[input_hash] = {
            "id": check_id,
            "input_hash": input_hash,
            "model_version_key": model_version_key,
            "test_case_id": test_case_id,
            "result": check_result.model_dump(),
            "provider": provider,
            "model_name": model_name,
            "model_version": model_version,
            "temperature": temperature,
            "seed": seed,
            "prompt_version": prompt_version,
            "created_at": now,
            "updated_at": now,
        }

        return check_id

    async def get_idempotency_check(
        self, model_version_key: str, input_hash: str
    ) -> dict[str, Any] | None:
        """冪等性チェック結果を取得

        Args:
            model_version_key: モデルバージョンキー
            input_hash: 入力のハッシュ値

        Returns:
            冪等性チェック結果の辞書、存在しない場合はNone
        """
        return self._idempotency_checks.get(input_hash)

    async def list_idempotency_checks(
        self,
        test_case_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """冪等性チェック結果の一覧を取得

        Args:
            test_case_id: テストケースIDでフィルタ（オプション）
            limit: 取得件数の上限
            offset: オフセット

        Returns:
            冪等性チェック結果の辞書のリスト
        """
        checks = list(self._idempotency_checks.values())

        # Filter by test_case_id if provided
        if test_case_id:
            checks = [c for c in checks if c["test_case_id"] == test_case_id]

        # Sort by created_at descending
        checks.sort(key=lambda x: x["created_at"], reverse=True)

        # Apply pagination
        return checks[offset : offset + limit]

    # Health Check

    async def health_check(self) -> bool:
        """データベース接続の健全性チェック

        Returns:
            常にTrue（インメモリなので常に利用可能）
        """
        return True

    # Utility methods

    def clear(self) -> None:
        """全データをクリア（テスト用）"""
        self._evaluation_results.clear()
        self._idempotency_checks.clear()
