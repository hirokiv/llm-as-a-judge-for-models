#!/usr/bin/env python3
"""
MLflowから評価結果をエクスポートしてCSVに保存
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .envファイルを読み込む
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from mlflow.tracking import MlflowClient  # noqa: E402


def export_traces_to_csv(output_file: str = "exports/evaluations/evaluation_results.csv"):
    """
    MLflowのトレースデータをCSVにエクスポート

    Args:
        output_file: 出力CSVファイル名
    """
    client = MlflowClient()

    # 実験IDを取得
    experiment_name = "llm-judge-evaluations"
    try:
        experiment = client.get_experiment_by_name(experiment_name)
        if not experiment:
            print(f"❌ 実験 '{experiment_name}' が見つかりません")
            return
    except Exception as e:
        print(f"❌ 実験取得エラー: {e}")
        return

    print(f"実験: {experiment_name} (ID: {experiment.experiment_id})")

    # 最近のrunを取得
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id], max_results=100, order_by=["start_time DESC"]
    )

    print(f"取得したruns: {len(runs)}件")

    if not runs:
        print("⚠️  評価データが見つかりません")
        return

    # CSV用のデータを準備
    csv_data = []

    for run in runs:
        run_id = run.info.run_id
        start_time = datetime.fromtimestamp(run.info.start_time / 1000.0)

        # メトリクスとパラメータを取得
        metrics = run.data.metrics
        params = run.data.params
        tags = run.data.tags

        row = {
            "run_id": run_id,
            "start_time": start_time.isoformat(),
            "test_case_id": params.get("test_case_id", tags.get("test_case_id", "N/A")),
            "model": params.get("model", tags.get("mlflow.runName", "N/A")),
            "is_safe": metrics.get("is_safe", params.get("is_safe", "N/A")),
            "risk_score": metrics.get("risk_score", params.get("risk_score", "N/A")),
            "exploited_vectors": params.get(
                "exploited_vectors", tags.get("exploited_vectors", "N/A")
            ),
            "reasoning": params.get("reasoning", "N/A")[:200] + "...",  # 最初の200文字
            "recommendation": params.get("recommendation", "N/A")[:200] + "...",
        }

        csv_data.append(row)

    # CSVに書き込み
    if csv_data:
        fieldnames = [
            "run_id",
            "start_time",
            "test_case_id",
            "model",
            "is_safe",
            "risk_score",
            "exploited_vectors",
            "reasoning",
            "recommendation",
        ]

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

        print(f"✅ エクスポート完了: {output_file} ({len(csv_data)}件)")
    else:
        print("⚠️  エクスポートするデータがありません")


def export_traces_with_mlflow_api(output_file: str = "traces_results.csv"):
    """
    MLflow Traces APIを使ってトレースデータをエクスポート

    Args:
        output_file: 出力CSVファイル名
    """
    try:
        from mlflow.tracing import get_traces

        # 最近のトレースを取得（100件）
        traces = get_traces(max_results=100)

        print(f"取得したtraces: {len(traces)}件")

        if not traces:
            print("⚠️  トレースデータが見つかりません")
            return

        # CSV用のデータを準備
        csv_data = []

        for trace in traces:
            row = {
                "request_id": trace.info.request_id,
                "timestamp": trace.info.timestamp_ms,
                "execution_time_ms": trace.info.execution_time_ms,
                "status": trace.info.status,
                "tags": str(trace.info.tags),
            }

            # スパンから詳細情報を抽出
            if trace.data and trace.data.spans:
                for span in trace.data.spans:
                    if span.name == "evaluate_input":
                        row["span_name"] = span.name
                        row["inputs"] = str(span.inputs)[:200] if span.inputs else ""
                        row["outputs"] = str(span.outputs)[:200] if span.outputs else ""
                        break

            csv_data.append(row)

        # CSVに書き込み
        if csv_data:
            fieldnames = list(csv_data[0].keys())

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)

            print(f"✅ トレースエクスポート完了: {output_file} ({len(csv_data)}件)")
        else:
            print("⚠️  エクスポートするデータがありません")

    except ImportError:
        print("⚠️  MLflow Tracing APIが利用できません（MLflow 2.x以降が必要）")
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == "__main__":
    print("=" * 80)
    print("MLflow評価結果エクスポート")
    print("=" * 80)
    print()

    # Runs（実験データ）をエクスポート
    print("【方法1】Runs（実験データ）をエクスポート")
    export_traces_to_csv("evaluation_results.csv")
    print()

    # Traces（トレースデータ）をエクスポート
    print("【方法2】Traces（トレースデータ）をエクスポート")
    export_traces_with_mlflow_api("traces_results.csv")
    print()

    print("✅ エクスポート処理が完了しました")
