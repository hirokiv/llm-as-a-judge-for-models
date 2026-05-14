"""
Unit tests for test case loader

テストケースローダーの単体テスト
"""

import pytest

from src.utils.test_case_loader import (
    TestCaseNotFoundError,
    list_available_test_cases,
    load_test_case,
)


class TestLoadTestCase:
    """load_test_case 関数のテスト"""

    def test_load_existing_test_case(self):
        """存在するテストケースが読み込めること"""
        # config/test_cases/lethal_trifecta.yaml に TEST-LT-001 がある想定
        test_case = load_test_case("TEST-LT-001")

        assert test_case.id == "TEST-LT-001"
        assert test_case.name is not None
        assert test_case.input_text is not None
        assert test_case.lethal_trifecta_vectors is not None

    def test_load_nonexistent_test_case(self):
        """存在しないテストケースでエラーが発生すること"""
        with pytest.raises(TestCaseNotFoundError):
            load_test_case("NONEXISTENT-TEST-999")

    def test_load_test_case_cached(self):
        """テストケースがキャッシュされること"""
        # 同じIDで2回読み込み
        test_case1 = load_test_case("TEST-LT-001")
        test_case2 = load_test_case("TEST-LT-001")

        # 同じオブジェクトが返されること（lru_cacheによるキャッシュ）
        assert test_case1 is test_case2


class TestListAvailableTestCases:
    """list_available_test_cases 関数のテスト"""

    def test_list_test_cases(self):
        """テストケース一覧が取得できること"""
        test_case_ids = list_available_test_cases()

        assert isinstance(test_case_ids, list)
        assert len(test_case_ids) > 0
        assert "TEST-LT-001" in test_case_ids

    def test_list_test_cases_sorted(self):
        """テストケースIDがソートされていること"""
        test_case_ids = list_available_test_cases()

        assert test_case_ids == sorted(test_case_ids)
