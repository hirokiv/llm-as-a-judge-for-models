"""
Idempotency Check endpoints

冪等性チェックAPI
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import RepositoryDep
from src.api.routes.test_cases import _test_case_store
from src.models.idempotency import IdempotencyCheckRequest
from src.services.idempotency_checker import get_idempotency_checker
from src.services.judge_llm import get_judge_llm
from src.utils.logger import get_logger
from src.utils.test_case_loader import TestCaseLoader, TestCaseNotFoundError

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/idempotency-check",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="冪等性チェック実行",
    description="特定のテストケースに対して複数回評価を実行し、冪等性を検証",
)
async def check_idempotency(
    request: IdempotencyCheckRequest,
    repository: RepositoryDep,
) -> dict[str, Any]:
    """冪等性チェック実行エンドポイント

    Args:
        request: 冪等性チェックリクエスト
        repository: Repository依存性注入

    Returns:
        冪等性チェック結果

    Raises:
        HTTPException: エラー発生時
    """
    try:
        logger.info(
            "Idempotency check request received",
            test_case_id=request.test_case_id,
            num_runs=request.num_runs,
        )

        # テストケースを取得（YAMLまたはインメモリストアから）
        test_case_loader = TestCaseLoader()
        test_case_loader.set_in_memory_store(_test_case_store)
        test_case = test_case_loader.load_test_case(request.test_case_id)

        # Idempotency Checkerを初期化
        judge_llm = get_judge_llm()
        idempotency_checker = get_idempotency_checker(
            judge_llm=judge_llm, num_runs=request.num_runs
        )

        # 冪等性チェック実行
        # Note: We need to provide all required parameters for check_idempotency
        result = await idempotency_checker.check_idempotency(
            test_case=test_case,
            system_output=request.system_output,
            provider="stub",  # Use stub provider for E2E tests
            model_name="stub-model",
            model_version="1.0",
            temperature=0.0,
            seed=42,
            prompt_version="v1",
        )

        # E2Eテスト用のレスポンス形式
        # executions を簡略化した形式に変換
        executions_simplified = [
            {
                "run": exec_detail.run_number,
                "risk_score": exec_detail.risk_score,
                "is_safe": exec_detail.is_safe,
            }
            for exec_detail in result.executions
        ]

        # レスポンス作成
        return {
            "status": "success",
            "data": {
                "is_idempotent": result.is_idempotent,
                "variance_score": result.variance_score,
                "executions": executions_simplified,
                "message": result.message,
            },
        }

    except TestCaseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TEST_CASE_NOT_FOUND",
                "message": f"テストケースが見つかりません: {request.test_case_id}",
            },
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Idempotency check error",
            test_case_id=request.test_case_id,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "IDEMPOTENCY_CHECK_ERROR",
                "message": f"冪等性チェック中にエラーが発生しました: {str(e)}",
            },
        ) from e
