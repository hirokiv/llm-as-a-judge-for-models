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

    # System Configs CRUD

    @abstractmethod
    async def get_system_config(
        self, config_key: str, environment: str | None = None
    ) -> dict[str, Any] | None:
        """システム設定を取得

        Args:
            config_key: 設定キー（例: "application.api.port"）
            environment: 環境名（default, development, staging, production）

        Returns:
            設定値の辞書、存在しない場合はNone

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def list_system_configs(
        self, environment: str | None = None, is_active: bool = True
    ) -> list[dict[str, Any]]:
        """システム設定の一覧を取得

        Args:
            environment: 環境名でフィルタ（オプション）
            is_active: アクティブな設定のみ取得

        Returns:
            設定の辞書のリスト

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def upsert_system_config(
        self,
        config_key: str,
        value: str,
        value_type: str,
        environment: str = "default",
        description: str | None = None,
        is_active: bool = True,
    ) -> str:
        """システム設定を挿入または更新

        Args:
            config_key: 設定キー
            value: 設定値
            value_type: 値の型（string, integer, float, boolean, json）
            environment: 環境名
            description: 説明
            is_active: アクティブフラグ

        Returns:
            保存されたレコードのID

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    # Target AI Systems CRUD

    @abstractmethod
    async def get_target_ai_system(self, name: str) -> dict[str, Any] | None:
        """ターゲットAIシステム設定を取得

        Args:
            name: システム名（例: "default", "production"）

        Returns:
            設定の辞書、存在しない場合はNone

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def list_target_ai_systems(self, is_active: bool = True) -> list[dict[str, Any]]:
        """ターゲットAIシステム設定の一覧を取得

        Args:
            is_active: アクティブな設定のみ取得

        Returns:
            設定の辞書のリスト

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def upsert_target_ai_system(
        self,
        name: str,
        url: str,
        headers: dict[str, Any],
        request_config: dict[str, Any],
        response_config: dict[str, Any],
        timeout_seconds: int = 30,
        stub_enabled: bool = False,
        stub_responses: dict[str, Any] | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> str:
        """ターゲットAIシステム設定を挿入または更新

        Args:
            name: システム名
            url: エンドポイントURL
            headers: 認証ヘッダー
            request_config: リクエスト設定
            response_config: レスポンスパーサー設定
            timeout_seconds: タイムアウト秒数
            stub_enabled: スタブ有効フラグ
            stub_responses: スタブ応答パターン
            description: 説明
            is_active: アクティブフラグ

        Returns:
            保存されたレコードのID

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    # Evaluation Criteria CRUD

    @abstractmethod
    async def get_evaluation_criteria(
        self, name: str, version: str | None = None
    ) -> dict[str, Any] | None:
        """評価基準設定を取得

        Args:
            name: 基準名（例: "default", "strict"）
            version: バージョン（オプション、指定しない場合は最新のアクティブ版）

        Returns:
            設定の辞書、存在しない場合はNone

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def list_evaluation_criteria(self, is_active: bool = True) -> list[dict[str, Any]]:
        """評価基準設定の一覧を取得

        Args:
            is_active: アクティブな設定のみ取得

        Returns:
            設定の辞書のリスト

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def upsert_evaluation_criteria(
        self,
        name: str,
        version: str,
        hard_rules: list[dict[str, Any]],
        soft_judge_criteria: list[dict[str, Any]],
        risk_score_config: dict[str, Any],
        recommendation_templates: dict[str, Any],
        hard_rules_enabled: bool = False,
        description: str | None = None,
        is_active: bool = True,
    ) -> str:
        """評価基準設定を挿入または更新

        Args:
            name: 基準名
            version: バージョン
            hard_rules: Hard Rules定義
            soft_judge_criteria: Soft Judge基準
            risk_score_config: リスクスコア計算ルール
            recommendation_templates: 推奨事項テンプレート
            hard_rules_enabled: Hard Rules有効フラグ
            description: 説明
            is_active: アクティブフラグ

        Returns:
            保存されたレコードのID

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    # Test Cases CRUD

    @abstractmethod
    async def get_test_case(self, test_case_id: str) -> dict[str, Any] | None:
        """テストケースを取得

        Args:
            test_case_id: テストケースID

        Returns:
            テストケースの辞書、存在しない場合はNone

        Raises:
            RepositoryError: データベースエラー
        """
        pass

    @abstractmethod
    async def list_test_cases(
        self, is_active: bool = True, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """テストケースの一覧を取得

        Args:
            is_active: アクティブなテストケースのみ取得
            limit: 取得件数の上限

        Returns:
            テストケースの辞書のリスト

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
