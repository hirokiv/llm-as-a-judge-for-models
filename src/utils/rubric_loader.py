"""
Rubric criteria loader utility

Rubric設定ファイルを読み込むユーティリティ

DB-first with YAML fallback:
- USE_DB_CONFIG=true: データベースから読み込み、失敗時はYAMLにフォールバック
- USE_DB_CONFIG=false (default): YAMLから読み込み
"""

import os
from pathlib import Path

import yaml

from src.config.loader import ConfigLoader
from src.models.rubric import RubricCriteria
from src.utils.logger import get_logger

logger = get_logger(__name__)


def load_rubric_criteria(config_path: str | None = None) -> RubricCriteria:
    """
    Rubric設定ファイルを読み込む（test_cases.yamlから）

    Args:
        config_path: 設定ファイルのパス（デフォルト: config/test_cases/test_cases.yaml）

    Returns:
        RubricCriteria

    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        ValueError: 設定ファイルの形式が不正な場合
    """
    if config_path is None:
        config_path = "config/test_cases/test_cases.yaml"

    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Rubric config file not found: {config_path}")

    try:
        with open(config_file, encoding="utf-8") as f:
            full_config = yaml.safe_load(f)

        # rubric_criteriaセクションを抽出
        rubric_data = full_config.get("rubric_criteria", {})

        # RubricCriteriaモデル用に構造を変換
        # 新構造: {security: {...}, quality: {...}}
        # → 旧構造: {soft_judge: {criteria: [...]}}
        all_criteria = []
        for _category_name, category_data in rubric_data.items():
            if isinstance(category_data, dict) and "criteria" in category_data:
                all_criteria.extend(category_data["criteria"])

        config_data = {
            "version": full_config.get("version", "2.0"),
            "description": full_config.get("description", "統合Rubric評価基準"),
            "hard_rules": {"enabled": False, "rules": []},  # Hard Rulesは無効
            "soft_judge": {
                "enabled": True,
                "description": "統合Rubric評価基準（security + quality）",
                "criteria": all_criteria,
            },
        }

        rubric = RubricCriteria(**config_data)

        logger.debug(
            "Rubric criteria loaded from test_cases.yaml",
            version=rubric.version,
            soft_judge_criteria_count=len(rubric.soft_judge.criteria),
        )

        return rubric

    except Exception as e:
        logger.error("Failed to load rubric criteria", error=str(e))
        raise ValueError(f"Invalid rubric config: {e}") from e


async def load_rubric_criteria_async(
    name: str = "default", version: str | None = None
) -> RubricCriteria:
    """
    Rubric設定を非同期で読み込む（DB-first with YAML fallback）

    Args:
        name: 基準名（default, strict等）
        version: バージョン（オプション、未指定時は最新）

    Returns:
        RubricCriteria

    Raises:
        FileNotFoundError: 設定ファイルが見つからず、DBからも取得できない場合
        ValueError: 設定データの形式が不正な場合
    """
    use_db_config = os.getenv("USE_DB_CONFIG", "false").lower() in ("true", "1", "yes")

    if not use_db_config:
        # YAML-only mode
        logger.debug("Loading rubric criteria from YAML (USE_DB_CONFIG=false)")
        return load_rubric_criteria()

    # DB-first mode
    try:
        logger.debug("Loading rubric criteria from database", name=name, version=version)
        config_data = await ConfigLoader.load_rubric_criteria_async(name, version)

        # Convert config data to RubricCriteria model
        rubric = RubricCriteria(**config_data)

        logger.info(
            "Loaded rubric criteria from database",
            name=name,
            version=version,
            hard_rules_count=len(rubric.hard_rules.rules),
            soft_judge_criteria_count=len(rubric.soft_judge.criteria),
        )

        return rubric

    except Exception as e:
        logger.warning(
            "Failed to load rubric criteria from database, falling back to YAML",
            name=name,
            version=version,
            error=str(e),
        )
        return load_rubric_criteria()
