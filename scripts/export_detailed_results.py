#!/usr/bin/env python3
"""
MLflowから評価結果の詳細をArtifactsから取得してCSVにエクスポート
"""

import csv
import json
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


def export_detailed_results(
    output_file: str = "exports/evaluations/detailed_evaluation_results.csv",
):
    """
    MLflowのRunsとArtifactsから詳細な評価結果をエクスポート

    Args:
        output_file: 出力CSVファイル名
    """
    client = MlflowClient()

    # 実験を取得
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
    print()

    # 最近のrunを取得
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id], max_results=100, order_by=["start_time DESC"]
    )

    print(f"取得したruns: {len(runs)}件")
    print()

    if not runs:
        print("⚠️  評価データが見つかりません")
        return

    # CSV用のデータを準備
    csv_data = []

    for idx, run in enumerate(runs, 1):
        run_id = run.info.run_id
        start_time = datetime.fromtimestamp(run.info.start_time / 1000.0)
        end_time = datetime.fromtimestamp(run.info.end_time / 1000.0) if run.info.end_time else None
        duration = (run.info.end_time - run.info.start_time) / 1000.0 if run.info.end_time else None

        # メトリクス、パラメータ、タグを取得
        metrics = run.data.metrics
        params = run.data.params
        tags = run.data.tags

        print(f"[{idx}/{len(runs)}] Processing run: {run_id[:8]}...")

        # 基本情報
        row = {
            "run_id": run_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else "",
            "duration_sec": f"{duration:.2f}" if duration else "",
            "status": run.info.status,
            "test_case_id": params.get("test_case_id", tags.get("test_case_id", "N/A")),
            "model": params.get("judge_model", tags.get("model", "N/A")),
            "is_safe": metrics.get("is_safe", "N/A"),
            "risk_score": metrics.get("risk_score", "N/A"),
        }

        # Artifactsから詳細データを取得
        try:
            artifacts = client.list_artifacts(run_id)

            for artifact in artifacts:
                artifact_path = artifact.path

                # JSONファイルを探す
                if artifact_path.endswith(".json"):
                    try:
                        # Artifactをダウンロード
                        local_path = client.download_artifacts(run_id, artifact_path)

                        # JSONを読み込む
                        with open(local_path, encoding="utf-8") as f:
                            artifact_data = json.load(f)

                        # 詳細データを抽出
                        if "input_text" in artifact_data:
                            row["input_text"] = (
                                artifact_data["input_text"][:200] + "..."
                                if len(artifact_data.get("input_text", "")) > 200
                                else artifact_data.get("input_text", "")
                            )

                        if "system_output" in artifact_data:
                            row["system_output"] = (
                                artifact_data["system_output"][:200] + "..."
                                if len(artifact_data.get("system_output", "")) > 200
                                else artifact_data.get("system_output", "")
                            )

                        if "reasoning" in artifact_data:
                            row["reasoning"] = artifact_data["reasoning"]

                        if "recommendation" in artifact_data:
                            row["recommendation"] = artifact_data["recommendation"]

                        if "exploited_vectors" in artifact_data:
                            vectors = artifact_data["exploited_vectors"]
                            if isinstance(vectors, list):
                                row["exploited_vectors"] = ", ".join(vectors)
                            else:
                                row["exploited_vectors"] = str(vectors)

                        if "confidence" in artifact_data:
                            row["confidence"] = artifact_data["confidence"]

                        if "prompt_tokens" in artifact_data:
                            row["prompt_tokens"] = artifact_data["prompt_tokens"]

                        if "completion_tokens" in artifact_data:
                            row["completion_tokens"] = artifact_data["completion_tokens"]

                        if "total_tokens" in artifact_data:
                            row["total_tokens"] = artifact_data["total_tokens"]

                    except Exception as e:
                        print(f"  ⚠️  Artifact読み込みエラー ({artifact_path}): {e}")

                # テキストファイルを探す
                elif artifact_path.endswith(".txt"):
                    try:
                        local_path = client.download_artifacts(run_id, artifact_path)
                        with open(local_path, encoding="utf-8") as f:
                            content = f.read()

                        # ファイル名に応じて格納
                        if "reasoning" in artifact_path.lower():
                            row["reasoning"] = content
                        elif "recommendation" in artifact_path.lower():
                            row["recommendation"] = content
                        elif "input" in artifact_path.lower():
                            row["input_text"] = (
                                content[:200] + "..." if len(content) > 200 else content
                            )
                        elif "output" in artifact_path.lower():
                            row["system_output"] = (
                                content[:200] + "..." if len(content) > 200 else content
                            )

                    except Exception as e:
                        print(f"  ⚠️  Artifact読み込みエラー ({artifact_path}): {e}")

        except Exception as e:
            print(f"  ⚠️  Artifacts取得エラー: {e}")

        # デフォルト値を設定
        if "exploited_vectors" not in row:
            row["exploited_vectors"] = params.get("exploited_vectors", "N/A")
        if "reasoning" not in row:
            row["reasoning"] = "N/A"
        if "recommendation" not in row:
            row["recommendation"] = "N/A"
        if "input_text" not in row:
            row["input_text"] = "N/A"
        if "system_output" not in row:
            row["system_output"] = "N/A"

        csv_data.append(row)

    print()

    # CSVに書き込み
    if csv_data:
        # すべてのキーを収集（動的に列を決定）
        all_keys = set()
        for row in csv_data:
            all_keys.update(row.keys())

        # 列の順序を定義
        primary_fields = [
            "run_id",
            "start_time",
            "end_time",
            "duration_sec",
            "status",
            "test_case_id",
            "model",
            "is_safe",
            "risk_score",
            "exploited_vectors",
            "input_text",
            "system_output",
            "reasoning",
            "recommendation",
        ]

        # 追加フィールド（トークン数など）
        additional_fields = sorted(all_keys - set(primary_fields))

        fieldnames = [f for f in primary_fields if f in all_keys] + additional_fields

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(csv_data)

        print(f"✅ 詳細エクスポート完了: {output_file} ({len(csv_data)}件)")
        print(f"📊 含まれる列: {len(fieldnames)}列")
        print(f"   - {', '.join(fieldnames[:8])}...")
    else:
        print("⚠️  エクスポートするデータがありません")


if __name__ == "__main__":
    print("=" * 80)
    print("MLflow詳細評価結果エクスポート（Artifacts含む）")
    print("=" * 80)
    print()

    export_detailed_results()

    print()
    print("✅ エクスポート処理が完了しました")
