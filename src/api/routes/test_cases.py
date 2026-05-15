"""
Test Case Management endpoints

テストケース管理API
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status

from src.models.test_case import TestCaseScenario
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# In-memory test case store for E2E testing
# 本番環境ではYAMLファイルまたはデータベースを使用
_test_case_store: dict[str, dict[str, Any]] = {}


@router.get(
    "/test-cases",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="テストケース一覧取得",
    description="テストケースの一覧を取得",
)
async def list_test_cases(
    limit: int = 100,
    offset: int = 0,
    vector_filter: str | None = None,
) -> dict[str, Any]:
    """テストケース一覧取得エンドポイント

    Args:
        limit: 取得件数
        offset: オフセット
        vector_filter: Lethal Trifectaのフィルタ（未実装）

    Returns:
        テストケース一覧
    """
    scenarios = list(_test_case_store.values())

    # Apply pagination
    paginated = scenarios[offset : offset + limit]

    return {
        "status": "success",
        "data": {
            "scenarios": paginated,
            "total": len(scenarios),
            "limit": limit,
            "offset": offset,
        },
    }


@router.get(
    "/test-cases/{test_case_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="テストケース詳細取得",
    description="特定のテストケースの詳細を取得",
)
async def get_test_case(test_case_id: str) -> dict[str, Any]:
    """テストケース詳細取得エンドポイント

    Args:
        test_case_id: テストケースID

    Returns:
        テストケース詳細

    Raises:
        HTTPException: テストケースが見つからない場合
    """
    if test_case_id not in _test_case_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Test case not found: {test_case_id}",
            },
        )

    return {
        "status": "success",
        "data": _test_case_store[test_case_id],
    }


@router.post(
    "/test-cases",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="テストケース作成",
    description="新しいテストケースを作成",
)
async def create_test_case(test_case: TestCaseScenario) -> dict[str, Any]:
    """テストケース作成エンドポイント

    Args:
        test_case: テストケース

    Returns:
        作成結果

    Raises:
        HTTPException: IDが既に存在する場合
    """
    if test_case.id in _test_case_store:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_ID",
                "message": f"Test case with ID '{test_case.id}' already exists",
            },
        )

    # Convert to dict and add timestamps
    test_case_dict = test_case.model_dump()
    now = datetime.now(timezone.utc).isoformat()
    test_case_dict["created_at"] = now
    test_case_dict["updated_at"] = now

    _test_case_store[test_case.id] = test_case_dict

    logger.info(
        "Test case created",
        test_case_id=test_case.id,
        name=test_case.name,
    )

    return {
        "status": "success",
        "data": {
            "id": test_case.id,
            "message": f"Test case '{test_case.id}' created successfully",
        },
    }


@router.put(
    "/test-cases/{test_case_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="テストケース更新",
    description="既存のテストケースを更新",
)
async def update_test_case(
    test_case_id: str,
    test_case: TestCaseScenario,
) -> dict[str, Any]:
    """テストケース更新エンドポイント

    Args:
        test_case_id: テストケースID
        test_case: 更新するテストケース

    Returns:
        更新結果

    Raises:
        HTTPException: テストケースが見つからない場合
    """
    if test_case_id not in _test_case_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Test case not found: {test_case_id}",
            },
        )

    # Update test case
    test_case_dict = test_case.model_dump()
    test_case_dict["id"] = test_case_id  # Ensure ID matches
    test_case_dict["created_at"] = _test_case_store[test_case_id]["created_at"]
    test_case_dict["updated_at"] = datetime.now(timezone.utc).isoformat()

    _test_case_store[test_case_id] = test_case_dict

    logger.info(
        "Test case updated",
        test_case_id=test_case_id,
        name=test_case.name,
    )

    return {
        "status": "success",
        "data": {
            "id": test_case_id,
            "message": "Test case updated successfully",
        },
    }


@router.delete(
    "/test-cases/{test_case_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="テストケース削除",
    description="テストケースを削除",
)
async def delete_test_case(test_case_id: str) -> dict[str, Any]:
    """テストケース削除エンドポイント

    Args:
        test_case_id: テストケースID

    Returns:
        削除結果

    Raises:
        HTTPException: テストケースが見つからない場合
    """
    if test_case_id not in _test_case_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Test case not found: {test_case_id}",
            },
        )

    del _test_case_store[test_case_id]

    logger.info(
        "Test case deleted",
        test_case_id=test_case_id,
    )

    return {
        "status": "success",
        "data": {
            "message": f"Test case '{test_case_id}' deleted successfully",
        },
    }


def clear_test_cases() -> None:
    """テストケースストアをクリア（テスト用）"""
    _test_case_store.clear()
