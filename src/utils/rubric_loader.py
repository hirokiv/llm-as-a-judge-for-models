"""
Rubric criteria loader utility

Rubric設定ファイルを読み込むユーティリティ
"""

from pathlib import Path

import yaml

from src.models.rubric import RubricCriteria
from src.utils.logger import get_logger

logger = get_logger(__name__)


def load_rubric_criteria(config_path: str | None = None) -> RubricCriteria:
    """
    Rubric設定ファイルを読み込む

    Args:
        config_path: 設定ファイルのパス（デフォルト: config/rubric_criteria.yaml）

    Returns:
        RubricCriteria

    Raises:
        FileNotFoundError: 設定ファイルが見つからない場合
        ValueError: 設定ファイルの形式が不正な場合
    """
    if config_path is None:
        config_path = "config/rubric_criteria.yaml"

    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Rubric config file not found: {config_path}")

    try:
        with open(config_file, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        rubric = RubricCriteria(**config_data)

        logger.debug(
            "Rubric criteria loaded",
            version=rubric.version,
            hard_rules_count=len(rubric.hard_rules.rules),
            soft_judge_criteria_count=len(rubric.soft_judge.criteria),
        )

        return rubric

    except Exception as e:
        logger.error("Failed to load rubric criteria", error=str(e))
        raise ValueError(f"Invalid rubric config: {e}") from e
