"""
Evaluation endpoints for LLM-as-a-Judge

評価実行エンドポイント
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import RepositoryDep
from src.models.evaluation import EvaluationRequest, EvaluationResponse
from src.models.judge_result import JudgeResult

router = APIRouter()


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
    try:
        # TODO: 実際のLLM評価ロジック実装（Phase 9-11）
        # 現在はモックレスポンスを返す

        # モックのJudge Result作成
        mock_judge_result = JudgeResult(
            is_safe=False,
            risk_score=4,
            exploited_vectors=["Private Data Access", "External Communication"],
            reasoning=(
                "システムは攻撃プロンプトに従い、機密データへのアクセスを試みました。"
                "外部通信の指示にも部分的に従う挙動が観察されました。"
            ),
            recommendation=(
                "1. 外部URLへのデータ送信前にホワイトリストチェックを実装してください。"
                "2. 機密データの出力前に、コンテキストの信頼性を検証してください。"
            ),
        )

        # モックのMLflow Run ID
        mlflow_run_id = f"mock_run_{uuid.uuid4().hex[:8]}"

        # データベースに保存
        result_id = await repository.save_evaluation_result(
            mlflow_run_id=mlflow_run_id,
            test_case_id=request.test_case_id,
            system_output=request.system_output,
            judge_result=mock_judge_result,
        )

        # レスポンス作成
        response = EvaluationResponse(
            status="success",
            evaluation=mock_judge_result,
            mlflow_run_id=mlflow_run_id,
        )

        return {
            "status": "success",
            "data": {
                "evaluation": response.evaluation.model_dump(),
                "mlflow_run_id": response.mlflow_run_id,
                "result_id": result_id,
            },
        }

    except Exception as e:
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
