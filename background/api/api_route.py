from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import yaml
import os
import fcntl # ファイルロック用 (UNIX系想定)
from app.services.evaluator import EvaluatorService

router = APIRouter()
evaluator = EvaluatorService()

YAML_PATH = os.path.join(os.path.dirname(__file__), "../prompts/lethal_trifecta.yaml")

# ==========================================
# Pydantic Models for Test Cases
# ==========================================
class LethalTrifectaVectors(BaseModel):
    private_data_access: bool = Field(..., description="機密データへのアクセス能力が必要か")
    untrusted_content_exposure: bool = Field(..., description="非信頼コンテンツへの曝露が含まれるか")
    external_communication: bool = Field(..., description="外部への通信能力が必要か")

class TestCaseScenario(BaseModel):
    id: str = Field(..., description="テストケースの一意のID (例: BANK-LT-004)")
    name: str = Field(..., description="テストケースの名称")
    description: str = Field(..., description="攻撃シナリオの詳細な説明")
    lethal_trifecta_vectors: LethalTrifectaVectors
    input_text: str = Field(..., description="AIシステムへ入力される攻撃プロンプト")
    expected_safe_behavior: str = Field(..., description="AIシステムに期待される安全な挙動")

class EvaluationRequest(BaseModel):
    test_case_id: str
    system_output: str

# ==========================================
# Helper Functions for YAML I/O
# ==========================================
def _load_yaml() -> dict:
    if not os.path.exists(YAML_PATH):
        return {"version": "1.0", "scenarios": []}
    with open(YAML_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"version": "1.0", "scenarios": []}

def _save_yaml(data: dict):
    # 簡易的なファイルロック処理 (複数リクエストの競合を防ぐ)
    with open(YAML_PATH, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        fcntl.flock(f, fcntl.LOCK_UN)

# ==========================================
# API Endpoints
# ==========================================
@router.get("/test-cases", response_model=List[TestCaseScenario])
def list_test_cases():
    """登録されているテストケースの一覧を取得します。"""
    data = _load_yaml()
    return data.get("scenarios", [])

@router.post("/test-cases", status_code=status.HTTP_201_CREATED)
def add_test_case(scenario: TestCaseScenario):
    """新しいテストケースを追加し、YAMLファイルに保存します。"""
    data = _load_yaml()
    scenarios = data.get("scenarios", [])
    
    # IDの重複チェック
    if any(case["id"] == scenario.id for case in scenarios):
        raise HTTPException(status_code=400, detail=f"Test case with id '{scenario.id}' already exists.")
    
    scenarios.append(scenario.model_dump())
    data["scenarios"] = scenarios
    _save_yaml(data)
    
    return {"status": "success", "message": f"Test case '{scenario.id}' added."}

@router.delete("/test-cases/{test_case_id}")
def delete_test_case(test_case_id: str):
    """指定されたIDのテストケースを削除します。"""
    data = _load_yaml()
    scenarios = data.get("scenarios", [])
    
    initial_count = len(scenarios)
    # 指定されたID以外のものを残す
    data["scenarios"] = [case for case in scenarios if case["id"] != test_case_id]
    
    if len(data["scenarios"]) == initial_count:
        raise HTTPException(status_code=404, detail=f"Test case with id '{test_case_id}' not found.")
        
    _save_yaml(data)
    return {"status": "success", "message": f"Test case '{test_case_id}' deleted."}

@router.post("/evaluate")
def run_evaluation(request: EvaluationRequest):
    """指定されたテストケースIDと実際のシステム出力に基づいてLLM-as-a-judgeを実行します。"""
    data = _load_yaml()
    scenarios = data.get("scenarios", [])
    
    test_case = next((case for case in scenarios if case["id"] == request.test_case_id), None)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case ID not found.")
        
    # EvaluatorService (前回作成) を呼び出し
    result = evaluator.evaluate_test_case(test_case, request.system_output)
    return {"status": "success", "evaluation": result}