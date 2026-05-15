"""
Configuration Loader

YAMLベースの設定ファイルを読み込み、アプリケーション全体で使用可能にします。

DB-first with YAML fallback:
- USE_DB_CONFIG=true: データベースから設定を読み込み、失敗時はYAMLにフォールバック
- USE_DB_CONFIG=false (default): YAMLから読み込み（既存動作）
"""

import os
from pathlib import Path
from typing import Any

import yaml

from src.repositories.factory import get_repository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """
    設定ファイルを読み込むクラス

    すべての設定ファイルをconfig/ディレクトリから読み込み、
    環境変数による上書きをサポートします。
    """

    # 設定ファイルのベースディレクトリ
    CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

    @classmethod
    def load_yaml(cls, file_path: str | Path) -> dict[str, Any]:
        """
        YAMLファイルを読み込む

        Args:
            file_path: YAMLファイルのパス（相対または絶対）

        Returns:
            読み込んだ設定の辞書

        Raises:
            FileNotFoundError: ファイルが見つからない場合
            yaml.YAMLError: YAML構文エラーがある場合
        """
        path = Path(file_path)

        # 相対パスの場合、CONFIG_DIRからの相対パスとして解釈
        if not path.is_absolute():
            path = cls.CONFIG_DIR / path

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 環境変数の展開
        expanded_config: dict[str, Any] = cls._expand_env_vars(config)
        return expanded_config

    @classmethod
    def _expand_env_vars(cls, config: Any) -> Any:
        """
        設定内の環境変数を展開する

        ${VARIABLE_NAME} 形式の文字列を環境変数で置換します。

        Args:
            config: 設定データ（dict, list, str, etc.）

        Returns:
            環境変数展開後の設定データ
        """
        if isinstance(config, dict):
            return {k: cls._expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [cls._expand_env_vars(item) for item in config]
        elif isinstance(config, str):
            # ${VAR_NAME} 形式の環境変数を展開
            if config.startswith("${") and config.endswith("}"):
                var_name = config[2:-1]
                return os.getenv(var_name, config)
            return config
        else:
            return config

    @classmethod
    def load_system_defaults(cls) -> dict[str, Any]:
        """
        システムデフォルト設定を読み込む

        Returns:
            システム設定の辞書
        """
        return cls.load_yaml("system_defaults.yaml")

    @classmethod
    def load_judge_configs(cls) -> dict[str, Any]:
        """
        Judge LLM設定を読み込む

        Returns:
            Judge LLM設定の辞書
        """
        return cls.load_yaml("judge_llm_configs.yaml")

    @classmethod
    def load_rubric_criteria(cls) -> dict[str, Any]:
        """
        Rubric評価基準を読み込む（test_cases.yamlから）

        Returns:
            評価基準の辞書
        """
        test_cases_config = cls.load_yaml("test_cases/test_cases.yaml")
        return test_cases_config.get("rubric_criteria", {})

    @classmethod
    def load_test_cases(cls, category: str = "lethal_trifecta") -> dict[str, Any]:
        """
        テストケースを読み込む

        Args:
            category: テストケースのカテゴリ（デフォルト: lethal_trifecta）

        Returns:
            テストケースの辞書
        """
        return cls.load_yaml(f"test_cases/{category}.yaml")

    @classmethod
    def load_stub_patterns(cls) -> dict[str, Any]:
        """
        スタブ動作パターンを読み込む

        Returns:
            スタブパターンの辞書
        """
        return cls.load_yaml("stubs/behavior_patterns.yaml")

    @classmethod
    def get_judge_config_by_id(cls, config_id: str) -> dict[str, Any] | None:
        """
        指定されたIDのJudge LLM設定を取得

        Args:
            config_id: 設定ID（例: "gpt-4-production"）

        Returns:
            Judge LLM設定、見つからない場合はNone
        """
        configs = cls.load_judge_configs()

        for config in configs.get("configs", []):
            if config.get("config_id") == config_id:
                result: dict[str, Any] = config
                return result

        return None

    @classmethod
    def get_default_judge_config(cls) -> dict[str, Any]:
        """
        デフォルトのJudge LLM設定を取得

        Returns:
            デフォルトのJudge LLM設定

        Raises:
            ValueError: デフォルト設定が見つからない場合
        """
        configs = cls.load_judge_configs()
        default_id = configs.get("default_config_id")

        if not default_id:
            raise ValueError("No default_config_id specified in judge_llm_configs.yaml")

        config = cls.get_judge_config_by_id(default_id)

        if not config:
            raise ValueError(f"Default config '{default_id}' not found")

        return config

    @classmethod
    def get_environment_config(cls, environment: str | None = None) -> dict[str, Any]:
        """
        環境別の設定を取得

        Args:
            environment: 環境名（development/staging/production）
                        Noneの場合はENVIRONMENT環境変数を使用

        Returns:
            環境別設定の辞書
        """
        system_config = cls.load_system_defaults()

        if environment is None:
            environment = os.getenv("ENVIRONMENT", "development")

        env_defaults = system_config.get("environments", {}).get(environment, {})

        # システムデフォルトと環境別設定をマージ
        return cls._merge_configs(system_config, env_defaults)

    @staticmethod
    def _merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        2つの設定辞書をマージ（override が base を上書き）

        Args:
            base: ベース設定
            override: 上書き設定

        Returns:
            マージ後の設定
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def _unflatten_dict(configs: list[dict[str, Any]], sep: str = ".") -> dict[str, Any]:
        """
        フラット化された設定を階層構造に戻す

        Args:
            configs: データベースから取得したフラット化設定のリスト
            sep: 区切り文字（デフォルト: "."）

        Returns:
            階層構造の設定辞書

        Example:
            Input: [{"config_key": "application.api.port", "value": "8000", "value_type": "integer"}]
            Output: {"application": {"api": {"port": 8000}}}
        """
        result: dict[str, Any] = {}

        for config in configs:
            config_key = config.get("config_key", "")
            value = config.get("value", "")
            value_type = config.get("value_type", "string")

            # 型変換
            if value_type == "integer":
                converted_value: Any = int(value)
            elif value_type == "float":
                converted_value = float(value)
            elif value_type == "boolean":
                converted_value = value.lower() in ("true", "1", "yes")
            elif value_type == "json":
                import json

                converted_value = json.loads(value)
            else:  # string
                converted_value = value

            # ドット区切りのキーを階層構造に展開
            parts = config_key.split(sep)
            current = result

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = converted_value

        return result

    @classmethod
    def _use_db_config(cls) -> bool:
        """
        データベース設定を使用するかチェック

        Returns:
            USE_DB_CONFIG環境変数がtrueの場合True
        """
        return os.getenv("USE_DB_CONFIG", "false").lower() in ("true", "1", "yes")

    # ==========================================
    # Async methods with DB-first approach
    # ==========================================

    @classmethod
    async def load_system_defaults_async(cls, environment: str | None = None) -> dict[str, Any]:
        """
        システムデフォルト設定を非同期で読み込む（DB-first with YAML fallback）

        Args:
            environment: 環境名（default, development, staging, production）

        Returns:
            システム設定の辞書

        Raises:
            FileNotFoundError: YAMLファイルが見つからず、DBからも取得できない場合
        """
        if not cls._use_db_config():
            # YAML-only mode
            logger.debug("Loading system defaults from YAML (USE_DB_CONFIG=false)")
            return cls.load_system_defaults()

        # DB-first mode
        try:
            logger.debug(
                "Loading system defaults from database", environment=environment or "default"
            )
            repo = get_repository()
            configs = await repo.list_system_configs(
                environment=environment or "default", is_active=True
            )

            if not configs:
                logger.warning(
                    "No system configs found in database, falling back to YAML",
                    environment=environment,
                )
                return cls.load_system_defaults()

            # フラット化された設定を階層構造に戻す
            result = cls._unflatten_dict(configs)
            logger.info(
                "Loaded system defaults from database",
                config_count=len(configs),
                environment=environment,
            )
            return result

        except Exception as e:
            logger.warning(
                "Failed to load system defaults from database, falling back to YAML",
                error=str(e),
                environment=environment,
            )
            return cls.load_system_defaults()

    @classmethod
    async def load_judge_configs_async(cls) -> dict[str, Any]:
        """
        Judge LLM設定を非同期で読み込む（DB-first with YAML fallback）

        Returns:
            Judge LLM設定の辞書
        """
        if not cls._use_db_config():
            logger.debug("Loading judge configs from YAML (USE_DB_CONFIG=false)")
            return cls.load_judge_configs()

        try:
            logger.debug("Loading judge configs from database")
            repo = get_repository()

            # judge_llm_configsテーブルから全設定を取得
            # Note: Repository層にjudge_llm_configs用のメソッドがないため、
            # 一旦YAMLから読み込み（Phase 3で追加したのはsystem_configs, target_ai_systems, evaluation_criteriaのみ）
            # TODO: judge_llm_configsもRepository層に追加する
            logger.warning("Judge configs DB loading not yet implemented, using YAML fallback")
            return cls.load_judge_configs()

        except Exception as e:
            logger.warning(
                "Failed to load judge configs from database, falling back to YAML",
                error=str(e),
            )
            return cls.load_judge_configs()

    @classmethod
    async def load_target_ai_system_async(cls, name: str = "default") -> dict[str, Any]:
        """
        ターゲットAIシステム設定を非同期で読み込む（DB-first with YAML fallback）

        Args:
            name: システム名（default, production等）

        Returns:
            ターゲットAIシステム設定の辞書
        """
        if not cls._use_db_config():
            logger.debug("Loading target AI system from YAML (USE_DB_CONFIG=false)")
            # YAMLファイルの構造に合わせて返す
            yaml_config = cls.load_yaml("target_ai_system.yaml")
            return yaml_config.get("target_ai_system", {})

        try:
            logger.debug("Loading target AI system from database", name=name)
            repo = get_repository()
            system_config = await repo.get_target_ai_system(name)

            if not system_config:
                logger.warning(
                    "Target AI system not found in database, falling back to YAML",
                    name=name,
                )
                yaml_config = cls.load_yaml("target_ai_system.yaml")
                return yaml_config.get("target_ai_system", {})

            # JSONB フィールドを適切にパース
            import json

            result = {
                "url": system_config.get("url"),
                "timeout": system_config.get("timeout_seconds", 30),
                "headers": (
                    json.loads(system_config["headers"])
                    if isinstance(system_config.get("headers"), str)
                    else system_config.get("headers", {})
                ),
                "request_format": (
                    json.loads(system_config["request_config"])
                    if isinstance(system_config.get("request_config"), str)
                    else system_config.get("request_config", {})
                ),
                "response_parser": (
                    json.loads(system_config["response_config"])
                    if isinstance(system_config.get("response_config"), str)
                    else system_config.get("response_config", {})
                ),
            }

            logger.info("Loaded target AI system from database", name=name)
            return result

        except Exception as e:
            logger.warning(
                "Failed to load target AI system from database, falling back to YAML",
                error=str(e),
                name=name,
            )
            yaml_config = cls.load_yaml("target_ai_system.yaml")
            return yaml_config.get("target_ai_system", {})

    @classmethod
    async def load_rubric_criteria_async(
        cls, name: str = "default", version: str | None = None
    ) -> dict[str, Any]:
        """
        Rubric評価基準を非同期で読み込む（DB-first with YAML fallback）

        Args:
            name: 基準名（default, strict等）
            version: バージョン（オプション、未指定時は最新）

        Returns:
            評価基準の辞書
        """
        if not cls._use_db_config():
            logger.debug("Loading rubric criteria from YAML (USE_DB_CONFIG=false)")
            return cls.load_rubric_criteria()

        try:
            logger.debug("Loading rubric criteria from database", name=name, version=version)
            repo = get_repository()
            criteria_config = await repo.get_evaluation_criteria(name, version)

            if not criteria_config:
                logger.warning(
                    "Rubric criteria not found in database, falling back to YAML",
                    name=name,
                    version=version,
                )
                return cls.load_rubric_criteria()

            # JSONB フィールドを適切にパース
            import json

            result = {
                "version": criteria_config.get("version", "1.0"),
                "description": criteria_config.get("description", ""),
                "hard_rules": {
                    "enabled": criteria_config.get("hard_rules_enabled", False),
                    "rules": (
                        json.loads(criteria_config["hard_rules"])
                        if isinstance(criteria_config.get("hard_rules"), str)
                        else criteria_config.get("hard_rules", [])
                    ),
                },
                "soft_judge": {
                    "criteria": (
                        json.loads(criteria_config["soft_judge_criteria"])
                        if isinstance(criteria_config.get("soft_judge_criteria"), str)
                        else criteria_config.get("soft_judge_criteria", [])
                    )
                },
                "risk_score_calculation": (
                    json.loads(criteria_config["risk_score_config"])
                    if isinstance(criteria_config.get("risk_score_config"), str)
                    else criteria_config.get("risk_score_config", {})
                ),
                "recommendation_templates": (
                    json.loads(criteria_config["recommendation_templates"])
                    if isinstance(criteria_config.get("recommendation_templates"), str)
                    else criteria_config.get("recommendation_templates", {})
                ),
            }

            logger.info("Loaded rubric criteria from database", name=name, version=version)
            return result

        except Exception as e:
            logger.warning(
                "Failed to load rubric criteria from database, falling back to YAML",
                error=str(e),
                name=name,
                version=version,
            )
            return cls.load_rubric_criteria()


# シングルトンインスタンス
_config_cache: dict[str, Any] = {}


def get_cached_config(config_type: str) -> dict[str, Any]:
    """
    キャッシュされた設定を取得（パフォーマンス最適化）

    Args:
        config_type: 設定タイプ（system/judge/rubric/test_cases/stub）

    Returns:
        設定辞書
    """
    if config_type not in _config_cache:
        if config_type == "system":
            _config_cache[config_type] = ConfigLoader.load_system_defaults()
        elif config_type == "judge":
            _config_cache[config_type] = ConfigLoader.load_judge_configs()
        elif config_type == "rubric":
            _config_cache[config_type] = ConfigLoader.load_rubric_criteria()
        elif config_type == "test_cases":
            _config_cache[config_type] = ConfigLoader.load_test_cases()
        elif config_type == "stub":
            _config_cache[config_type] = ConfigLoader.load_stub_patterns()
        else:
            raise ValueError(f"Unknown config type: {config_type}")

    result: dict[str, Any] = _config_cache[config_type]
    return result


def clear_config_cache() -> None:
    """設定キャッシュをクリア（テスト用）"""
    global _config_cache
    _config_cache = {}
