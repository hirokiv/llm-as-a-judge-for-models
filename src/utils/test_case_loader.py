"""
Test case loader from YAML files

YAMLファイルからテストケースを読み込む
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.models.test_case import LethalTrifectaVectors, TestCaseScenario
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TestCaseNotFoundError(Exception):
    """テストケースが見つからない場合のエラー"""

    pass


class TestCaseLoader:
    """テストケースローダー（YAMLファイルまたはインメモリストアから読み込み）"""

    def __init__(self) -> None:
        """Initialize test case loader"""
        self._in_memory_store: dict[str, Any] = {}

    def set_in_memory_store(self, store: dict[str, Any]) -> None:
        """Set in-memory test case store for testing

        Args:
            store: In-memory test case store from test_cases.py
        """
        self._in_memory_store = store

    def load_test_case(self, test_case_id: str) -> TestCaseScenario:
        """Load test case from in-memory store or YAML files

        Args:
            test_case_id: Test case ID

        Returns:
            Test case scenario

        Raises:
            TestCaseNotFoundError: When test case is not found
        """
        # First, try instance's in-memory store
        if test_case_id in self._in_memory_store:
            return TestCaseScenario(**self._in_memory_store[test_case_id])

        # Fallback to module-level function (which checks global store then YAML)
        return load_test_case(test_case_id)


@lru_cache(maxsize=128)
def _load_test_case_from_yaml(test_case_id: str) -> TestCaseScenario:
    """
    テストケースIDからYAMLファイルを読み込む（内部関数、キャッシュ有効）

    Args:
        test_case_id: テストケースID

    Returns:
        読み込まれたテストケース

    Raises:
        TestCaseNotFoundError: テストケースが見つからない場合
    """
    # テストケースディレクトリを探索
    test_case_dirs = [
        "config/test_cases",
        "config/test_cases/lethal_trifecta",
    ]

    for test_case_dir in test_case_dirs:
        if not os.path.exists(test_case_dir):
            continue

        # ディレクトリ内のすべてのYAMLファイルを探索
        for yaml_file in Path(test_case_dir).glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                # test_cases リストを探索
                test_cases = data.get("test_cases", [])
                for tc_data in test_cases:
                    # YAML内では test_case_id キーを使用
                    if (
                        tc_data.get("test_case_id") == test_case_id
                        or tc_data.get("id") == test_case_id
                    ):
                        logger.info(
                            "Test case loaded",
                            test_case_id=test_case_id,
                            file=str(yaml_file),
                        )
                        return _parse_test_case(tc_data)

            except Exception as e:
                logger.warning(
                    "Failed to load test case file",
                    file=str(yaml_file),
                    error=str(e),
                )
                continue

    # 見つからなかった場合
    raise TestCaseNotFoundError(f"Test case '{test_case_id}' not found in {test_case_dirs}")


def load_test_case(test_case_id: str) -> TestCaseScenario:
    """
    テストケースIDからテストケースを読み込む

    Args:
        test_case_id: テストケースID（例: "TEST-LT-001"）

    Returns:
        読み込まれたテストケース

    Raises:
        TestCaseNotFoundError: テストケースが見つからない場合

    Examples:
        >>> test_case = load_test_case("TEST-LT-001")
        >>> print(test_case.name)
    """
    # First, check if test case exists in in-memory store (for E2E tests)
    try:
        from src.api.routes.test_cases import _test_case_store

        if test_case_id in _test_case_store:
            logger.info(
                "Test case loaded from in-memory store",
                test_case_id=test_case_id,
            )
            return TestCaseScenario(**_test_case_store[test_case_id])
    except ImportError:
        # If we can't import (e.g., in tests without API), skip
        pass

    # Fallback to cached YAML loading
    return _load_test_case_from_yaml(test_case_id)


def _parse_test_case(data: dict[str, Any]) -> TestCaseScenario:
    """
    辞書データからTestCaseScenarioオブジェクトを生成

    Args:
        data: YAMLから読み込んだ辞書データ

    Returns:
        TestCaseScenarioオブジェクト
    """
    vectors_data = data.get("lethal_trifecta_vectors", {})

    # YAML内では test_case_id キーを使用しているが、モデルではidを使用
    test_case_id = data.get("test_case_id") or data.get("id")
    if not test_case_id:
        raise ValueError("Test case must have 'test_case_id' or 'id' field")

    return TestCaseScenario(
        id=str(test_case_id),
        name=data["name"],
        description=data.get("description", ""),
        input_text=data["input_text"],
        expected_safe_behavior=data.get("expected_safe_behavior", ""),
        lethal_trifecta_vectors=LethalTrifectaVectors(
            private_data_access=vectors_data.get("private_data_access", False),
            untrusted_content_exposure=vectors_data.get("untrusted_content_exposure", False),
            external_communication=vectors_data.get("external_communication", False),
        ),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


def list_available_test_cases() -> list[str]:
    """
    利用可能なテストケースIDのリストを返す

    Returns:
        テストケースIDのリスト

    Examples:
        >>> test_case_ids = list_available_test_cases()
        >>> print(test_case_ids)
        ['TEST-LT-001', 'TEST-LT-002', ...]
    """
    test_case_ids = []
    test_case_dirs = [
        "config/test_cases",
        "config/test_cases/lethal_trifecta",
    ]

    for test_case_dir in test_case_dirs:
        if not os.path.exists(test_case_dir):
            continue

        for yaml_file in Path(test_case_dir).glob("**/*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                test_cases = data.get("test_cases", [])
                for tc_data in test_cases:
                    # YAML内では test_case_id または id キーを使用
                    tc_id = tc_data.get("test_case_id") or tc_data.get("id")
                    if tc_id:
                        test_case_ids.append(tc_id)

            except Exception:
                continue

    logger.info("Listed available test cases", count=len(test_case_ids))
    return sorted(test_case_ids)
