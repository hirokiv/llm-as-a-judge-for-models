"""
Base Repository for LLM-as-a-Judge

データアクセス層の抽象基底クラス定義
"""

from abc import ABC, abstractmethod
from typing import Any

from src.models.idempotency import IdempotencyCheckResult
from src.models.judge_result import JudgeResult


class BaseRepository(ABC):
    """データベースアクセスの抽象基底クラス

    Supabase/Databricks間の切り替えを容易にするためのインターフェース
    """

    # Evaluation Results CRUD

    @abstractmethod
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

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def get_evaluation_result(self, result_id: str) -> dict[str, Any] | None:
        """評価結果を取得

        Args:
            result_id: 評価結果ID

        Returns:
            評価結果の辞書、存在しない場合はNone

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def get_evaluation_result_by_mlflow_run_id(
        self, mlflow_run_id: str
    ) -> dict[str, Any] | None:
        """MLflow Run IDで評価結果を取得

        Args:
            mlflow_run_id: MLflow Run ID

        Returns:
            評価結果の辞書、存在しない場合はNone

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
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

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    # Idempotency Checks CRUD

    @abstractmethod
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
            temperature: Temperature設定
            seed: Seed値
            prompt_version: プロンプトバージョン

        Returns:
            保存されたレコードのID

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def get_idempotency_check(
        self, model_version_key: str, input_hash: str
    ) -> dict[str, Any] | None:
        """冪等性チェック結果を取得

        Args:
            model_version_key: モデルバージョンキー
            input_hash: 入力のハッシュ値

        Returns:
            冪等性チェック結果の辞書、存在しない場合はNone

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
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

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    # Health Check

    @abstractmethod
    async def health_check(self) -> bool:
        """データベース接続の健全性チェック

        Returns:
            接続が正常な場合True

        Raises:
            RepositoryError: データベースエラー
        """
        pass


class RepositoryError(Exception):
    """Repository層のエラー基底クラス"""

    pass


class RepositoryConnectionError(RepositoryError):
    """データベース接続エラー"""

    pass


class RepositoryNotFoundError(RepositoryError):
    """レコードが見つからないエラー"""

    pass


class RepositoryDuplicateError(RepositoryError):
    """重複レコードエラー"""

    pass
