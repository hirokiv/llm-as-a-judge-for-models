"""
Proxy endpoints for LLM-as-a-Judge

プロキシエンドポイント - ユーザーのAIシステムへのプロキシとして動作し、
入力・出力の両方を評価する
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import RepositoryDep
from src.services.evaluator import get_evaluator
from src.services.idempotency_checker import get_idempotency_checker
from src.services.judge_llm import get_judge_llm
from src.services.mlflow_tracker import get_mlflow_tracker
from src.services.proxy_service import ProxyServiceError, get_proxy_service
from src.utils.logger import get_logger
from src.utils.test_case_loader import load_all_test_cases

router = APIRouter()
logger = get_logger(__name__)


class ProxyChatRequest(BaseModel):
    """プロキシチャットリクエスト

    Attributes:
        user_input: ユーザーからの入力プロンプト
        enable_input_check: INPUT評価を実施するか（プロンプト攻撃検出）
        enable_output_check: OUTPUT評価を実施するか（AI出力の安全性評価）
        test_case_ids: 評価に使用するテストケースIDリスト（省略時は全テストケース）
    """

    user_input: str = Field(..., description="ユーザーからの入力プロンプト", min_length=1)
    enable_input_check: bool = Field(
        True, description="INPUT評価を実施するか（プロンプト攻撃検出）"
    )
    enable_output_check: bool = Field(
        True, description="OUTPUT評価を実施するか（AI出力の安全性評価）"
    )
    test_case_ids: list[str] | None = Field(
        None, description="評価に使用するテストケースIDリスト（省略時は全テストケース）"
    )


class ProxyChatResponse(BaseModel):
    """プロキシチャットレスポンス

    Attributes:
        status: ステータス（常に "success"）
        ai_response: AIシステムからの出力（常に返す）
        input_evaluation: INPUT評価結果（検出・警告のみ）
        output_evaluation: OUTPUT評価結果（評価のみ、ブロックしない）

    Note:
        このシステムは評価専用です。ブロックはしません。
        ユーザー側が評価結果（is_safe, risk_score）を見て判断してください。
    """

    status: str = Field(default="success", description="ステータス（常に 'success'）")
    ai_response: str = Field(..., description="AIシステムからの出力（常に返す）")
    input_evaluation: dict[str, Any] | None = Field(
        None, description="INPUT評価結果（検出・警告のみ）"
    )
    output_evaluation: dict[str, Any] | None = Field(
        None, description="OUTPUT評価結果（評価のみ、ブロックしない）"
    )


@router.post(
    "/chat",
    response_model=ProxyChatResponse,
    status_code=status.HTTP_200_OK,
    summary="プロキシチャット（INPUT/OUTPUT評価付き）",
    description="ユーザー入力を評価し、ターゲットAIシステムに転送し、出力も評価する（評価専用、ブロックなし）",
)
async def proxy_chat(
    request: ProxyChatRequest,
    repository: RepositoryDep,
) -> ProxyChatResponse:
    """プロキシチャットエンドポイント（評価専用）

    フロー:
    1. INPUT評価（有効時）: ユーザー入力がプロンプト攻撃かチェック（警告のみ）
    2. ターゲットAIシステムへ転送
    3. OUTPUT評価（有効時）: AI出力の安全性をチェック（評価のみ）
    4. AI応答と評価結果を返す（危険でもブロックしない）

    Note:
        このシステムは評価専用です。ブロックはしません。
        ユーザー側が評価結果（is_safe, risk_score）を見て、
        ブロックするかどうかを判断してください。

    Args:
        request: プロキシチャットリクエスト
        repository: Repository依存性注入

    Returns:
        プロキシチャットレスポンス

    Raises:
        HTTPException: エラー発生時
    """
    try:
        logger.info(
            "Proxy chat request received",
            input_length=len(request.user_input),
            enable_input_check=request.enable_input_check,
            enable_output_check=request.enable_output_check,
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

        input_evaluation_results = None
        output_evaluation_results = None

        # ===== STEP 1: INPUT評価 =====
        if request.enable_input_check:
            logger.info("Running INPUT evaluation (prompt injection detection)")

            # INPUT評価用のテストケースを取得
            all_test_cases = load_all_test_cases()
            input_test_cases = [tc for tc in all_test_cases if tc.evaluation_type == "input"]

            # テストケースIDフィルタ（指定がある場合）
            if request.test_case_ids:
                input_test_cases = [tc for tc in input_test_cases if tc.id in request.test_case_ids]

            # 各テストケースで評価
            input_results = []
            for test_case in input_test_cases:
                result = await evaluator.evaluate(
                    test_case_id=test_case.id,
                    system_output=request.user_input,  # INPUTの場合、ユーザー入力を評価
                    enable_idempotency_check=False,
                )
                input_results.append(result.to_dict())

            input_evaluation_results = {
                "total_cases": len(input_results),
                "results": input_results,
                "unsafe_cases": [r for r in input_results if not r["is_safe"]],
            }

            # 危険な入力を検出した場合、警告のみ（ブロックしない）
            if input_evaluation_results["unsafe_cases"]:
                logger.warning(
                    "INPUT evaluation detected potential attack, continuing to OUTPUT evaluation",
                    unsafe_count=len(input_evaluation_results["unsafe_cases"]),
                )
            else:
                logger.info("INPUT evaluation passed, all checks safe")

        # ===== STEP 2: ターゲットAIシステムへ転送 =====
        proxy_service = get_proxy_service()

        try:
            ai_response = await proxy_service.send_to_target_ai(request.user_input)
            logger.info("Received response from target AI system", response_length=len(ai_response))

        except ProxyServiceError as e:
            logger.error("Proxy service error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "TARGET_AI_ERROR",
                    "message": f"ターゲットAIシステムとの通信エラー: {str(e)}",
                },
            ) from e
        finally:
            await proxy_service.close()

        # ===== STEP 3: OUTPUT評価 =====
        if request.enable_output_check:
            logger.info("Running OUTPUT evaluation (response safety check)")

            # OUTPUT評価用のテストケースを取得
            all_test_cases = load_all_test_cases()
            output_test_cases = [tc for tc in all_test_cases if tc.evaluation_type == "output"]

            # テストケースIDフィルタ（指定がある場合）
            if request.test_case_ids:
                output_test_cases = [
                    tc for tc in output_test_cases if tc.id in request.test_case_ids
                ]

            # 各テストケースで評価
            output_results = []
            for test_case in output_test_cases:
                result = await evaluator.evaluate(
                    test_case_id=test_case.id,
                    system_output=ai_response,  # OUTPUTの場合、AI出力を評価
                    enable_idempotency_check=False,
                )
                output_results.append(result.to_dict())

            output_evaluation_results = {
                "total_cases": len(output_results),
                "results": output_results,
                "unsafe_cases": [r for r in output_results if not r["is_safe"]],
            }

            # 危険な出力を検出した場合、警告ログのみ（ブロックしない）
            if output_evaluation_results["unsafe_cases"]:
                logger.warning(
                    "OUTPUT evaluation detected unsafe response (evaluation only, no blocking)",
                    unsafe_count=len(output_evaluation_results["unsafe_cases"]),
                )
            else:
                logger.info("OUTPUT evaluation passed, all checks safe")

        # ===== STEP 4: AI応答と評価結果を返す（常にブロックしない） =====
        return ProxyChatResponse(
            status="success",
            ai_response=ai_response,
            input_evaluation=input_evaluation_results,
            output_evaluation=output_evaluation_results,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Proxy chat error",
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "PROXY_CHAT_ERROR",
                "message": f"プロキシチャット処理中にエラーが発生しました: {str(e)}",
            },
        ) from e
