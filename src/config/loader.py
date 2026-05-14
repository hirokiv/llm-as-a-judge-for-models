"""
Configuration Loader

YAMLベースの設定ファイルを読み込み、アプリケーション全体で使用可能にします。
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class ConfigLoader:
    """
    設定ファイルを読み込むクラス

    すべての設定ファイルをconfig/ディレクトリから読み込み、
    環境変数による上書きをサポートします。
    """

    # 設定ファイルのベースディレクトリ
    CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

    @classmethod
    def load_yaml(cls, file_path: str | Path) -> Dict[str, Any]:
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

        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 環境変数の展開
        return cls._expand_env_vars(config)

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
    def load_system_defaults(cls) -> Dict[str, Any]:
        """
        システムデフォルト設定を読み込む

        Returns:
            システム設定の辞書
        """
        return cls.load_yaml("system_defaults.yaml")

    @classmethod
    def load_judge_configs(cls) -> Dict[str, Any]:
        """
        Judge LLM設定を読み込む

        Returns:
            Judge LLM設定の辞書
        """
        return cls.load_yaml("judge_llm_configs.yaml")

    @classmethod
    def load_rubric_criteria(cls) -> Dict[str, Any]:
        """
        Rubric評価基準を読み込む

        Returns:
            評価基準の辞書
        """
        return cls.load_yaml("rubric_criteria.yaml")

    @classmethod
    def load_test_cases(cls, category: str = "lethal_trifecta") -> Dict[str, Any]:
        """
        テストケースを読み込む

        Args:
            category: テストケースのカテゴリ（デフォルト: lethal_trifecta）

        Returns:
            テストケースの辞書
        """
        return cls.load_yaml(f"test_cases/{category}.yaml")

    @classmethod
    def load_stub_patterns(cls) -> Dict[str, Any]:
        """
        スタブ動作パターンを読み込む

        Returns:
            スタブパターンの辞書
        """
        return cls.load_yaml("stubs/behavior_patterns.yaml")

    @classmethod
    def get_judge_config_by_id(cls, config_id: str) -> Optional[Dict[str, Any]]:
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
                return config

        return None

    @classmethod
    def get_default_judge_config(cls) -> Dict[str, Any]:
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
    def get_environment_config(cls, environment: Optional[str] = None) -> Dict[str, Any]:
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
    def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
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


# シングルトンインスタンス
_config_cache: Dict[str, Any] = {}


def get_cached_config(config_type: str) -> Dict[str, Any]:
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

    return _config_cache[config_type]


def clear_config_cache():
    """設定キャッシュをクリア（テスト用）"""
    global _config_cache
    _config_cache = {}
