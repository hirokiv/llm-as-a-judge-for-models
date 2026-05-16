"""
Test case loader from YAML files

YAMLファイルからテストケースを読み込む

DB-first with YAML fallback:
- USE_DB_CONFIG=true: データベースから読み込み、失敗時はYAMLにフォールバック
- USE_DB_CONFIG=false (default): YAMLから読み込み
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.models.test_case import (
    EvaluationConfig,
    LethalTrifectaVectors,
    TestCaseEvaluations,
    TestCaseScenario,
)
from src.repositories.factory import get_repository
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Phase 3: Evaluation Datasetsのために追加
try:
    import mlflow
    import pandas as pd

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning("MLflow or pandas not available, dataset features will be disabled")


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

    @staticmethod
    def _use_db_config() -> bool:
        """Check if database configuration should be used"""
        return os.getenv("USE_DB_CONFIG", "false").lower() in ("true", "1", "yes")

    async def load_test_case_async(self, test_case_id: str) -> TestCaseScenario:
        """Load test case asynchronously (DB-first with YAML fallback)

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

        if not self._use_db_config():
            # YAML-only mode
            logger.debug(
                "Loading test case from YAML (USE_DB_CONFIG=false)",
                test_case_id=test_case_id,
            )
            return load_test_case(test_case_id)

        # DB-first mode
        try:
            logger.debug("Loading test case from database", test_case_id=test_case_id)
            repo = get_repository()
            test_case_data = await repo.get_test_case(test_case_id)

            if not test_case_data:
                logger.warning(
                    "Test case not found in database, falling back to YAML",
                    test_case_id=test_case_id,
                )
                return load_test_case(test_case_id)

            # Convert database record to TestCaseScenario
            result = TestCaseScenario(
                id=test_case_data["id"],
                name=test_case_data["name"],
                description=test_case_data.get("description", ""),
                input_text=test_case_data["input_text"],
                expected_safe_behavior=test_case_data.get("expected_safe_behavior", ""),
                lethal_trifecta_vectors=LethalTrifectaVectors(
                    private_data_access=test_case_data.get("private_data_access", False),
                    untrusted_content_exposure=test_case_data.get(
                        "untrusted_content_exposure", False
                    ),
                    external_communication=test_case_data.get("external_communication", False),
                ),
                created_at=test_case_data.get("created_at"),
                updated_at=test_case_data.get("updated_at"),
            )

            logger.info("Loaded test case from database", test_case_id=test_case_id)
            return result

        except Exception as e:
            logger.warning(
                "Failed to load test case from database, falling back to YAML",
                test_case_id=test_case_id,
                error=str(e),
            )
            return load_test_case(test_case_id)

    async def list_test_cases_async(self) -> list[str]:
        """List all available test case IDs asynchronously (DB-first with YAML fallback)

        Returns:
            List of test case IDs

        Examples:
            >>> loader = TestCaseLoader()
            >>> test_case_ids = await loader.list_test_cases_async()
            >>> print(test_case_ids)
            ['TEST-LT-001', 'TEST-LT-002', ...]
        """
        if not self._use_db_config():
            # YAML-only mode
            logger.debug("Listing test cases from YAML (USE_DB_CONFIG=false)")
            return list_available_test_cases()

        # DB-first mode
        try:
            logger.debug("Listing test cases from database")
            repo = get_repository()
            test_cases = await repo.list_test_cases(is_active=True, limit=1000)

            if not test_cases:
                logger.warning("No test cases found in database, falling back to YAML")
                return list_available_test_cases()

            test_case_ids = [tc["id"] for tc in test_cases if "id" in tc]
            logger.info("Listed test cases from database", count=len(test_case_ids))
            return sorted(test_case_ids)

        except Exception as e:
            logger.warning(
                "Failed to list test cases from database, falling back to YAML",
                error=str(e),
            )
            return list_available_test_cases()


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

    # 評価設定のパース
    evaluations_data = data.get("evaluations", {})
    evaluations = None
    if evaluations_data:
        input_eval = evaluations_data.get("input")
        output_eval = evaluations_data.get("output")

        evaluations = TestCaseEvaluations(
            input=EvaluationConfig(**input_eval) if input_eval else None,
            output=EvaluationConfig(**output_eval) if output_eval else None,
        )

    return TestCaseScenario(
        id=str(test_case_id),
        name=data["name"],
        description=data.get("description", ""),
        severity=data.get("severity", 1),
        evaluation_type=data.get("evaluation_type"),
        evaluations=evaluations,
        input_text=data["input_text"],
        expected_safe_behavior=data.get("expected_safe_behavior"),
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


def load_all_test_cases() -> list[TestCaseScenario]:
    """
    すべてのテストケースを読み込む（Phase 3: Evaluation Datasets用）

    Returns:
        TestCaseScenarioのリスト

    Examples:
        >>> test_cases = load_all_test_cases()
        >>> print(len(test_cases))
        5
    """
    test_case_ids = list_available_test_cases()
    test_cases = []

    for test_case_id in test_case_ids:
        try:
            test_case = load_test_case(test_case_id)
            test_cases.append(test_case)
        except Exception as e:
            logger.warning(
                "Failed to load test case",
                test_case_id=test_case_id,
                error=str(e),
            )
            continue

    logger.info("Loaded all test cases", count=len(test_cases))
    return test_cases


def load_test_cases_as_dataset(
    yaml_file: str | None = None,
    name: str = "evaluation_test_suite",
    targets: str = "expected_safe_behavior",
) -> Any:
    """
    テストケースをMLflow Evaluation Datasetとして読み込む（Phase 3）

    Args:
        yaml_file: YAMLファイルパス（Noneの場合はすべてのテストケースを読み込む）
        name: Dataset名
        targets: ターゲットカラム名

    Returns:
        mlflow.data.dataset.Dataset オブジェクト

    Raises:
        ImportError: MLflowまたはpandasがインストールされていない場合
        ValueError: テストケースが見つからない場合

    Examples:
        >>> dataset = load_test_cases_as_dataset()
        >>> print(dataset.name)
        evaluation_test_suite

        >>> dataset = load_test_cases_as_dataset("config/test_cases/lethal_trifecta.yaml")
        >>> print(dataset.source)
        config/test_cases/lethal_trifecta.yaml
    """
    if not MLFLOW_AVAILABLE:
        raise ImportError(
            "MLflow and pandas are required for dataset features. "
            "Install with: pip install mlflow pandas"
        )

    # テストケースを読み込み
    if yaml_file is not None:
        # 特定のYAMLファイルから読み込み
        test_cases = _load_test_cases_from_yaml_file(yaml_file)
        source = yaml_file
    else:
        # すべてのテストケースを読み込み
        test_cases = load_all_test_cases()
        source = "config/test_cases/**/*.yaml"

    if not test_cases:
        raise ValueError(f"No test cases found in {source}")

    # DataFrameに変換
    test_cases_data = []
    for tc in test_cases:
        test_cases_data.append(
            {
                "test_case_id": tc.id,
                "name": tc.name,
                "description": tc.description,
                "input_text": tc.input_text,
                "expected_safe_behavior": tc.expected_safe_behavior,
                "private_data_access": tc.lethal_trifecta_vectors.private_data_access,
                "untrusted_content_exposure": tc.lethal_trifecta_vectors.untrusted_content_exposure,
                "external_communication": tc.lethal_trifecta_vectors.external_communication,
                "created_at": tc.created_at.isoformat() if tc.created_at else None,
                "updated_at": tc.updated_at.isoformat() if tc.updated_at else None,
            }
        )

    df = pd.DataFrame(test_cases_data)

    # MLflow Datasetとして登録
    dataset = mlflow.data.from_pandas(
        df,
        source=source,
        name=name,
        targets=targets,
    )

    logger.info(
        "Created MLflow dataset",
        name=name,
        source=source,
        num_test_cases=len(test_cases),
    )

    return dataset


def _load_test_cases_from_yaml_file(yaml_file: str) -> list[TestCaseScenario]:
    """
    特定のYAMLファイルからすべてのテストケースを読み込む（内部関数）

    Args:
        yaml_file: YAMLファイルパス

    Returns:
        TestCaseScenarioのリスト

    Raises:
        FileNotFoundError: ファイルが見つからない場合
        ValueError: YAMLファイルが不正な形式の場合
    """
    if not os.path.exists(yaml_file):
        raise FileNotFoundError(f"YAML file not found: {yaml_file}")

    try:
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        test_cases = []
        test_cases_data = data.get("test_cases", [])

        if not test_cases_data:
            logger.warning("No test cases found in YAML file", file=yaml_file)
            return []

        for tc_data in test_cases_data:
            try:
                test_case = _parse_test_case(tc_data)
                test_cases.append(test_case)
            except Exception as e:
                logger.warning(
                    "Failed to parse test case",
                    file=yaml_file,
                    test_case_id=tc_data.get("test_case_id", "unknown"),
                    error=str(e),
                )
                continue

        logger.info(
            "Loaded test cases from YAML file",
            file=yaml_file,
            count=len(test_cases),
        )

        return test_cases

    except Exception as e:
        logger.error("Failed to load YAML file", file=yaml_file, error=str(e))
        raise ValueError(f"Failed to load YAML file {yaml_file}: {e}") from e
