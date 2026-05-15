#!/usr/bin/env python3
"""すべてのテストケースを一括実行

使用方法:
    make test-all-cases

    または

    python scripts/run_all_test_cases.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
# Load .env from project directory
load_dotenv(project_root / '.env')

import mlflow
from src.services.evaluator import get_evaluator
from src.services.judge_llm import get_judge_llm
from src.services.mlflow_tracker import MLflowTrackerService
from src.repositories.factory import get_repository
from src.utils.test_case_loader import load_all_test_cases

async def main():
    print("🚀 Starting batch evaluation of all test cases...")
    
    # MLflow設定
    mlflow.set_tracking_uri("http://localhost:5555")
    mlflow.set_experiment("llm-judge-evaluations")
    
    # サービス初期化
    print("🔧 Initializing services...")
    judge_llm = get_judge_llm()
    mlflow_tracker = MLflowTrackerService()
    repository = get_repository()
    
    evaluator = get_evaluator(
        judge_llm=judge_llm,
        mlflow_tracker=mlflow_tracker,
        repository=repository
    )
    
    # すべてのテストケースを読み込み
    print("📋 Loading all test cases...")
    test_cases = load_all_test_cases()
    print(f"   Found {len(test_cases)} test cases")
    
    # 各テストケースの入力テキストを使って評価
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Evaluating: {test_case.id} - {test_case.name}")
        
        try:
            # テストケースのinput_textをsystem_outputとして使用
            result = await evaluator.evaluate(
                test_case_id=test_case.id,
                system_output=test_case.input_text
            )
            
            print(f"   ✅ MLflow Run: {result.mlflow_run_id}")
            print(f"   📊 Risk Score: {result.judge_result.risk_score}")
            print(f"   🔒 Is Safe: {result.judge_result.is_safe}")
            
            results.append({
                "test_case_id": test_case.id,
                "mlflow_run_id": result.mlflow_run_id,
                "risk_score": result.judge_result.risk_score,
                "is_safe": result.judge_result.is_safe,
                "status": "success"
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                "test_case_id": test_case.id,
                "status": "failed",
                "error": str(e)
            })
    
    # サマリー
    print("\n" + "="*60)
    print("📊 EVALUATION SUMMARY")
    print("="*60)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = len(results) - success_count
    
    print(f"\n✅ Successful: {success_count}/{len(results)}")
    print(f"❌ Failed: {failed_count}/{len(results)}")
    
    print("\n📋 Detailed Results:")
    for result in results:
        if result["status"] == "success":
            safe_emoji = "🟢" if result["is_safe"] else "🔴"
            print(f"  {safe_emoji} {result['test_case_id']}: risk={result['risk_score']}, safe={result['is_safe']}")
        else:
            print(f"  ❌ {result['test_case_id']}: {result['error']}")
    
    print(f"\n🔗 View results in MLflow UI: http://localhost:5555")
    print("\n✅ Batch evaluation completed!")

if __name__ == "__main__":
    asyncio.run(main())
