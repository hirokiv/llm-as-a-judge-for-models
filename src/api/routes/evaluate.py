"""
Evaluation endpoints for LLM-as-a-Judge

評価実行エンドポイント
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import RepositoryDep
from src.models.evaluation import EvaluationRequest
from src.services.judge_llm import get_judge_llm
from src.services.mlflow_tracker import get_mlflow_tracker
from src.utils.logger import get_logger
from src.utils.test_case_loader import TestCaseNotFoundError, load_test_case

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/evaluate",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="評価実行",
    description="テストケースに対してLLM-as-a-judge評価を実行",
)
async def evaluate(
    request: EvaluationRequest,
    repository: RepositoryDep,
) -> dict[str, Any]:
    """評価実行エンドポイント

    Args:
        request: 評価リクエスト
        repository: Repository依存性注入

    Returns:
        評価結果

    Raises:
        HTTPException: エラー発生時
    """
    mlflow_tracker = None
    mlflow_run_id = None

    try:
        logger.info(
            "Evaluation request received",
            test_case_id=request.test_case_id,
            output_length=len(request.system_output),
        )

        # テストケースを読み込み
        try:
            test_case = load_test_case(request.test_case_id)
        except TestCaseNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TEST_CASE_NOT_FOUND",
                    "message": f"テストケースが見つかりません: {request.test_case_id}",
                },
            ) from e

        # MLflow Runを開始
        mlflow_tracker = get_mlflow_tracker()
        mlflow_run_id = mlflow_tracker.start_run(
            run_name=f"{test_case.id}_{test_case.name}",
            tags={
                "test_case_id": test_case.id,
                "test_case_name": test_case.name,
            },
        )

        # Judge LLMで評価実行
        judge_llm = get_judge_llm()
        judge_result = await judge_llm.evaluate(test_case, request.system_output)

        # MLflowに評価結果をロギング
        mlflow_tracker.log_evaluation_result(
            test_case=test_case,
            judge_result=judge_result,
            system_output=request.system_output,
        )

        # MLflow Runを終了
        mlflow_tracker.end_run(status="FINISHED")

        logger.info(
            "Evaluation completed",
            test_case_id=request.test_case_id,
            risk_score=judge_result.risk_score,
            is_safe=judge_result.is_safe,
            mlflow_run_id=mlflow_run_id,
        )

        # データベースに保存
        result_id = await repository.save_evaluation_result(
            mlflow_run_id=mlflow_run_id,
            test_case_id=request.test_case_id,
            system_output=request.system_output,
            judge_result=judge_result,
        )

        # レスポンス作成
        return {
            "status": "success",
            "data": {
                "evaluation": judge_result.model_dump(),
                "mlflow_run_id": mlflow_run_id,
                "result_id": result_id,
            },
        }

    except HTTPException:
        # MLflow Runが開始されている場合は終了
        if mlflow_tracker and mlflow_run_id:
            try:
                mlflow_tracker.end_run(status="FAILED")
            except Exception:
                pass  # MLflow終了エラーは無視
        raise
    except Exception as e:
        # MLflow Runが開始されている場合は終了
        if mlflow_tracker and mlflow_run_id:
            try:
                mlflow_tracker.end_run(status="FAILED")
            except Exception:
                pass  # MLflow終了エラーは無視

        logger.error(
            "Evaluation error",
            test_case_id=request.test_case_id if "test_case" in locals() else None,
            error=str(e),
            mlflow_run_id=mlflow_run_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EVALUATION_ERROR",
                "message": f"評価実行中にエラーが発生しました: {str(e)}",
            },
        ) from e


@router.get(
    "/evaluations/{result_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="評価結果取得",
    description="評価結果IDで評価結果を取得",
)
async def get_evaluation(
    result_id: str,
    repository: RepositoryDep,
) -> dict[str, Any]:
    """評価結果取得エンドポイント

    Args:
        result_id: 評価結果ID
        repository: Repository依存性注入

    Returns:
        評価結果

    Raises:
        HTTPException: 評価結果が見つからない場合
    """
    try:
        result = await repository.get_evaluation_result(result_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "NOT_FOUND",
                    "message": f"評価結果が見つかりません: {result_id}",
                },
            )

        return {
            "status": "success",
            "data": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DATABASE_ERROR",
                "message": f"評価結果取得中にエラーが発生しました: {str(e)}",
            },
        ) from e


@router.get(
    "/evaluations",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="評価結果一覧取得",
    description="評価結果の一覧を取得（ページネーション対応）",
)
async def list_evaluations(
    repository: RepositoryDep,
    test_case_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """評価結果一覧取得エンドポイント

    Args:
        repository: Repository依存性注入
        test_case_id: テストケースIDでフィルタ（オプション）
        limit: 取得件数
        offset: オフセット

    Returns:
        評価結果一覧

    Raises:
        HTTPException: エラー発生時
    """
    try:
        results = await repository.list_evaluation_results(
            test_case_id=test_case_id,
            limit=limit,
            offset=offset,
        )

        return {
            "status": "success",
            "data": {
                "results": results,
                "total": len(results),
                "limit": limit,
                "offset": offset,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DATABASE_ERROR",
                "message": f"評価結果一覧取得中にエラーが発生しました: {str(e)}",
            },
        ) from e
