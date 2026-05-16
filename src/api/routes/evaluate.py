"""
Evaluation endpoints for LLM-as-a-Judge

評価実行エンドポイント
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import RepositoryDep
from src.models.evaluation import EvaluationRequest, InputEvaluationRequest
from src.services.evaluator import get_evaluator
from src.services.idempotency_checker import get_idempotency_checker
from src.services.judge_llm import get_judge_llm
from src.services.mlflow_tracker import get_mlflow_tracker
from src.utils.logger import get_logger
from src.utils.test_case_loader import TestCaseLoader, TestCaseNotFoundError

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
    try:
        logger.info(
            "Evaluation request received",
            test_case_id=request.test_case_id,
            output_length=len(request.system_output),
        )

        # Evaluator Serviceを初期化
        judge_llm = get_judge_llm()
        mlflow_tracker = get_mlflow_tracker()
        idempotency_checker = get_idempotency_checker(judge_llm=judge_llm, num_runs=3)

        evaluator = get_evaluator(
            judge_llm=judge_llm,
            mlflow_tracker=mlflow_tracker,
            repository=repository,
            idempotency_checker=idempotency_checker,
        )

        # 評価実行
        result = await evaluator.evaluate(
            test_case_id=request.test_case_id,
            system_output=request.system_output,
            enable_idempotency_check=False,  # デフォルトは無効
        )

        # レスポンス作成
        return {
            "status": "success",
            "data": result.to_dict(),
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
            "Evaluation error",
            test_case_id=request.test_case_id,
            error=str(e),
            error_type=type(e).__name__,
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
                "evaluations": results,
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


@router.post(
    "/evaluate-input",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="INPUT評価実行",
    description="ユーザープロンプトの悪意性を事前評価（入力フィルタ）",
)
async def evaluate_input(
    request: InputEvaluationRequest,
    repository: RepositoryDep,
) -> dict[str, Any]:
    """INPUT評価実行エンドポイント

    ユーザーから入力されたプロンプトが悪意的かどうかを判定します。
    プロンプトインジェクション、権限昇格、データ漏洩などの攻撃パターンを検出します。

    Args:
        request: INPUT評価リクエスト
        repository: Repository依存性注入

    Returns:
        INPUT評価結果

    Raises:
        HTTPException: エラー発生時
    """
    try:
        # test_case_idとinput_promptの排他チェック
        if request.test_case_id and request.input_prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_REQUEST",
                    "message": "test_case_idとinput_promptは排他的です。どちらか一方のみ指定してください。",
                },
            )

        if not request.test_case_id and not request.input_prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_REQUEST",
                    "message": "test_case_idまたはinput_promptのいずれかを指定してください。",
                },
            )

        # 評価対象プロンプトの取得
        input_text = ""
        test_case_id = ""

        if request.test_case_id:
            # テストケースからプロンプトを取得
            loader = TestCaseLoader()
            test_case = await loader.load_test_case_async(request.test_case_id)
            input_text = test_case.input_text
            test_case_id = test_case.id

            logger.info(
                "INPUT evaluation request received (test case)",
                test_case_id=test_case_id,
                input_length=len(input_text),
            )
        else:
            # 直接指定されたプロンプトを使用
            input_text = request.input_prompt or ""
            test_case_id = "DIRECT-INPUT"

            logger.info(
                "INPUT evaluation request received (direct)",
                input_length=len(input_text),
            )

        # Evaluator Serviceを初期化
        judge_llm = get_judge_llm()
        mlflow_tracker = get_mlflow_tracker()

        evaluator = get_evaluator(
            judge_llm=judge_llm,
            mlflow_tracker=mlflow_tracker,
            repository=repository,
        )

        # INPUT評価実行
        result = await evaluator.evaluate_input(
            input_text=input_text,
            test_case_id=test_case_id,
        )

        # レスポンス作成
        return {
            "status": "success",
            "data": result.to_dict(),
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
            "INPUT evaluation error",
            test_case_id=request.test_case_id or "DIRECT",
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EVALUATION_ERROR",
                "message": f"INPUT評価実行中にエラーが発生しました: {str(e)}",
            },
        ) from e
