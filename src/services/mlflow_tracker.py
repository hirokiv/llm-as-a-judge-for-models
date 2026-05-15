"""
MLflow tracking service for evaluation results

評価結果をMLflowに記録するサービス
"""

import os
import tempfile
from pathlib import Path
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

from src.models.judge_result import JudgeResult
from src.models.rubric import HardRulesResult, RubricEvaluationResult
from src.models.test_case import TestCaseScenario
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MLflowTrackerService:
    """
    MLflow tracking service for managing evaluation experiments

    評価実験を管理するMLflowトラッキングサービス
    """

    def __init__(
        self,
        tracking_uri: str | None = None,
        experiment_name: str = "llm-judge-evaluations",
        enable_autolog: bool = True,
    ):
        """
        Initialize MLflow tracker service

        Args:
            tracking_uri: MLflow tracking URI（None の場合は環境変数から取得）
            experiment_name: 実験名
            enable_autolog: MLflow autologging を有効化するか（デフォルト: True）
        """
        self.tracking_uri: str = (
            tracking_uri
            or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
            or "http://localhost:5000"
        )
        self.experiment_name = experiment_name

        # MLflow設定
        mlflow.set_tracking_uri(self.tracking_uri)
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

        # 実験を作成または取得
        self.experiment_id = self._get_or_create_experiment()

        # MLflow autologging を有効化
        if enable_autolog:
            self._enable_autologging()

        logger.info(
            "Initialized MLflowTrackerService",
            tracking_uri=self.tracking_uri,
            experiment_name=self.experiment_name,
            experiment_id=self.experiment_id,
            autolog_enabled=enable_autolog,
        )

    def _get_or_create_experiment(self) -> str:
        """
        実験を取得または作成

        Returns:
            実験ID
        """
        experiment = mlflow.get_experiment_by_name(self.experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(self.experiment_name)
            logger.info("Created MLflow experiment", experiment_id=experiment_id)
        else:
            experiment_id = experiment.experiment_id
            logger.info("Using existing MLflow experiment", experiment_id=experiment_id)

        return experiment_id

    def _enable_autologging(self) -> None:
        """
        MLflow autologging を有効化

        LLM呼び出しの自動追跡を有効化します：
        - トークン使用量の自動記録
        - レイテンシの自動記録
        - コストの自動記録
        - リクエスト/レスポンスの自動記録

        Note:
            エラーが発生してもサービス初期化は継続します。
            autologging は補助的な機能であり、失敗しても既存の手動ログは動作します。
        """
        llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()

        try:
            if llm_provider in ["openai", "azure_openai"]:
                # OpenAI autologging
                try:
                    import mlflow.openai

                    # MLflow OpenAI autolog - 最小限のパラメータで有効化
                    # Note: MLflow 2.9+ では autolog() はパラメータを取らない
                    mlflow.openai.autolog()
                    logger.info(
                        "Enabled MLflow autologging for OpenAI",
                        provider=llm_provider,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to enable OpenAI autologging, continuing without it",
                        error=str(e),
                        provider=llm_provider,
                    )

            elif llm_provider == "anthropic":
                # Anthropic autologging
                try:
                    import mlflow.anthropic

                    # MLflow Anthropic autolog - 最小限のパラメータで有効化
                    mlflow.anthropic.autolog()
                    logger.info(
                        "Enabled MLflow autologging for Anthropic",
                        provider=llm_provider,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to enable Anthropic autologging, continuing without it",
                        error=str(e),
                        provider=llm_provider,
                    )

            else:
                logger.warning(
                    "Unknown LLM provider, autologging not enabled",
                    provider=llm_provider,
                    supported_providers=["openai", "azure_openai", "anthropic"],
                )

        except Exception as e:
            logger.warning(
                "Failed to enable MLflow autologging",
                error=str(e),
                provider=llm_provider,
            )

    def start_run(
        self,
        run_name: str | None = None,
        tags: dict[str, Any] | None = None,
    ) -> str:
        """
        MLflow Runを開始

        Args:
            run_name: Run名（オプション）
            tags: タグ辞書（オプション）

        Returns:
            Run ID
        """
        run = mlflow.start_run(
            experiment_id=self.experiment_id,
            run_name=run_name,
            tags=tags,
        )
        run_id: str = str(run.info.run_id)

        logger.info(
            "Started MLflow run",
            run_id=run_id,
            run_name=run_name,
        )

        return run_id

    def end_run(self, status: str = "FINISHED") -> None:
        """
        MLflow Runを終了

        Args:
            status: Run のステータス（FINISHED, FAILED, KILLED）
        """
        active_run = mlflow.active_run()
        run_id = active_run.info.run_id if active_run else None
        mlflow.end_run(status=status)

        logger.info(
            "Ended MLflow run",
            run_id=run_id,
            status=status,
        )

    def log_evaluation_result(
        self,
        test_case: TestCaseScenario,
        judge_result: JudgeResult,
        system_output: str,
        hard_rules_result: HardRulesResult | None = None,
        rubric_result: RubricEvaluationResult | None = None,
    ) -> None:
        """
        評価結果をMLflowに記録

        Args:
            test_case: テストケースシナリオ
            judge_result: Judge評価結果
            system_output: システム出力
            hard_rules_result: Hard Rules評価結果（オプション）
            rubric_result: Rubric評価結果（オプション）
        """
        # Parameters をロギング
        self.log_params(
            {
                "test_case_id": test_case.id,
                "test_case_name": test_case.name,
                "judge_model": judge_result.judge_model or "unknown",
                "judge_provider": judge_result.judge_provider or "unknown",
                "private_data_access": test_case.lethal_trifecta_vectors.private_data_access,
                "untrusted_content_exposure": test_case.lethal_trifecta_vectors.untrusted_content_exposure,
                "external_communication": test_case.lethal_trifecta_vectors.external_communication,
            }
        )

        # Metrics をロギング
        metrics = {
            "risk_score": float(judge_result.risk_score),
            "is_safe": 1.0 if judge_result.is_safe else 0.0,
            "exploited_vectors_count": float(len(judge_result.exploited_vectors)),
        }

        # Hard Rules評価結果をメトリクスに追加
        if hard_rules_result is not None:
            metrics.update(
                {
                    "hard_rules_enabled": 1.0 if hard_rules_result.enabled else 0.0,
                    "hard_rules_total_violations": float(hard_rules_result.total_violations),
                    "hard_rules_critical_violations": float(
                        hard_rules_result.critical_violations_count
                    ),
                    "hard_rules_high_violations": float(hard_rules_result.high_violations_count),
                    "hard_rules_has_violations": 1.0 if hard_rules_result.has_violations else 0.0,
                }
            )

        # Rubric評価結果（LLMベース）をメトリクスに追加
        if rubric_result is not None:
            metrics.update(
                {
                    "rubric_total_score": float(rubric_result.total_score),
                    "rubric_max_score": float(rubric_result.max_possible_score),
                    "rubric_score_rate": float(rubric_result.score_rate),
                    "rubric_is_pass": 1.0 if rubric_result.is_pass else 0.0,
                }
            )

            # 各評価項目のスコアを個別にログ
            for criterion_result in rubric_result.criteria_results:
                criterion_id = criterion_result.criterion_id.replace("-", "_").lower()
                metrics[f"rubric_criterion_{criterion_id}_score"] = float(criterion_result.score)
                metrics[f"rubric_criterion_{criterion_id}_max"] = float(criterion_result.max_score)

        self.log_metrics(metrics)

        # Tags をロギング
        tags = {
            "exploited_vectors": ", ".join(judge_result.exploited_vectors)
            if judge_result.exploited_vectors
            else "none",
            "environment": os.getenv("ENVIRONMENT", "development"),
        }

        # Hard Rules評価のサマリーをタグに追加
        if hard_rules_result is not None:
            tags["hard_rules_summary"] = hard_rules_result.to_summary()

        # Rubric評価のサマリーをタグに追加
        if rubric_result is not None:
            tags["rubric_summary"] = rubric_result.to_summary()

        self.log_tags(tags)

        # Artifacts をロギング（テキストファイル）
        artifacts = {
            "system_output.txt": system_output,
            "reasoning.txt": judge_result.reasoning,
            "recommendation.txt": judge_result.recommendation,
        }

        # Hard Rules評価の詳細をアーティファクトに追加
        if hard_rules_result is not None and hard_rules_result.enabled:
            artifacts["hard_rules_violations.txt"] = self._format_hard_rules_violations(
                hard_rules_result
            )

        # Rubric評価の詳細をアーティファクトに追加
        if rubric_result is not None:
            artifacts["rubric_evaluation.txt"] = self._format_rubric_evaluation(rubric_result)

        self._log_text_artifacts(artifacts)

        logger.info(
            "Logged evaluation result to MLflow",
            test_case_id=test_case.id,
            risk_score=judge_result.risk_score,
            is_safe=judge_result.is_safe,
            hard_rules_violations=(hard_rules_result.total_violations if hard_rules_result else 0),
            rubric_score_rate=f"{rubric_result.score_rate:.1%}" if rubric_result else "N/A",
        )

    def log_params(self, params: dict[str, Any]) -> None:
        """
        パラメータをロギング

        Args:
            params: パラメータ辞書
        """
        for key, value in params.items():
            mlflow.log_param(key, value)

    def log_metrics(self, metrics: dict[str, float]) -> None:
        """
        メトリクスをロギング

        Args:
            metrics: メトリクス辞書
        """
        for key, value in metrics.items():
            mlflow.log_metric(key, value)

    def log_tags(self, tags: dict[str, str]) -> None:
        """
        タグをロギング

        Args:
            tags: タグ辞書
        """
        mlflow.set_tags(tags)

    def log_prompt(self, prompt_template: dict[str, Any]) -> None:
        """
        プロンプトテンプレートをMLflow Prompt Registryに記録（Phase 2）

        Args:
            prompt_template: プロンプトテンプレート辞書

        Note:
            MLflow Prompt Registryの仕様に準拠した形式を期待
            - name: プロンプト名
            - template: プロンプトテンプレート文字列
            - parameters: パラメータリスト
            - version: バージョン文字列
            - metadata: メタデータ辞書
        """
        try:
            # MLflow Prompt Registryに記録
            # 現時点では、プロンプトをパラメータとアーティファクトとして記録
            # （MLflow 3.x のPrompt Registry APIが安定したら、native APIに移行）

            # プロンプトメタデータをパラメータとして記録
            mlflow.log_param("prompt_name", prompt_template.get("name", "unknown"))
            mlflow.log_param("prompt_version", prompt_template.get("version", "1.0.0"))

            # プロンプトテンプレートをアーティファクトとして記録
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                prompt_file = tmpdir_path / "prompt_template.txt"

                # プロンプト内容を整形
                content_lines = [
                    "=" * 60,
                    "PROMPT TEMPLATE",
                    "=" * 60,
                    "",
                    f"Name: {prompt_template.get('name')}",
                    f"Version: {prompt_template.get('version')}",
                    "",
                    "=" * 60,
                    "TEMPLATE",
                    "=" * 60,
                    "",
                    prompt_template.get("template", ""),
                    "",
                    "=" * 60,
                    "PARAMETERS",
                    "=" * 60,
                    "",
                ]

                for param in prompt_template.get("parameters", []):
                    param_name = param.get("name", "unknown")
                    param_type = param.get("type", "unknown")
                    param_desc = param.get("description", "")
                    content_lines.append(f"- {param_name} ({param_type}): {param_desc}")

                # メタデータを追加
                metadata = prompt_template.get("metadata", {})
                if metadata:
                    content_lines.extend(
                        [
                            "",
                            "=" * 60,
                            "METADATA",
                            "=" * 60,
                            "",
                        ]
                    )
                    for key, value in metadata.items():
                        content_lines.append(f"{key}: {value}")

                prompt_file.write_text("\n".join(content_lines), encoding="utf-8")
                mlflow.log_artifact(str(prompt_file), artifact_path="prompts")

            logger.info(
                "Logged prompt template to MLflow",
                name=prompt_template.get("name"),
                version=prompt_template.get("version"),
            )

        except Exception as e:
            logger.warning(
                "Failed to log prompt template",
                error=str(e),
                name=prompt_template.get("name", "unknown"),
            )

    def log_dataset(self, dataset: Any, context: str = "evaluation") -> None:
        """
        Evaluation DatasetをMLflowに記録（Phase 3）

        Args:
            dataset: mlflow.data.dataset.Dataset オブジェクト
            context: データセットのコンテキスト（例: "evaluation", "training"）

        Note:
            MLflow Datasets機能を使用してテストケースをバージョン管理
            - データセットの変更履歴を自動追跡
            - UIでデータセットを一覧表示
            - 評価結果とデータセットの紐付け
        """
        try:
            # MLflow Datasetsに記録
            mlflow.log_input(dataset, context=context)

            # データセットメタデータをパラメータとして記録
            mlflow.log_param("dataset_name", dataset.name)
            mlflow.log_param("dataset_source", dataset.source)

            # データセットの統計情報を記録
            if hasattr(dataset, "_df") and dataset._df is not None:
                df = dataset._df
                mlflow.log_metric("dataset_num_rows", float(len(df)))
                mlflow.log_metric("dataset_num_columns", float(len(df.columns)))

                # Lethal Trifecta要素の統計
                if "private_data_access" in df.columns:
                    mlflow.log_metric(
                        "dataset_private_data_access_count",
                        float(df["private_data_access"].sum()),
                    )
                if "untrusted_content_exposure" in df.columns:
                    mlflow.log_metric(
                        "dataset_untrusted_content_count",
                        float(df["untrusted_content_exposure"].sum()),
                    )
                if "external_communication" in df.columns:
                    mlflow.log_metric(
                        "dataset_external_communication_count",
                        float(df["external_communication"].sum()),
                    )

            logger.info(
                "Logged dataset to MLflow",
                name=dataset.name,
                source=dataset.source,
                context=context,
            )

        except Exception as e:
            logger.warning(
                "Failed to log dataset",
                error=str(e),
                name=getattr(dataset, "name", "unknown"),
            )

    def _log_text_artifacts(self, artifacts: dict[str, str]) -> None:
        """
        テキストアーティファクトをロギング

        Args:
            artifacts: アーティファクト辞書（ファイル名: 内容）
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            for filename, content in artifacts.items():
                filepath = tmpdir_path / filename
                filepath.write_text(content, encoding="utf-8")
                mlflow.log_artifact(str(filepath))

    def _format_hard_rules_violations(self, hard_rules_result: HardRulesResult) -> str:
        """
        Hard Rules違反を整形されたテキストに変換

        Args:
            hard_rules_result: Hard Rules評価結果

        Returns:
            整形されたテキスト
        """
        if not hard_rules_result.has_violations:
            return "No violations detected."

        lines = [
            "=" * 60,
            "HARD RULES VIOLATIONS",
            "=" * 60,
            "",
            f"Total Violations: {hard_rules_result.total_violations}",
            f"Critical: {hard_rules_result.critical_violations_count}",
            f"High: {hard_rules_result.high_violations_count}",
            "",
            "=" * 60,
            "VIOLATION DETAILS",
            "=" * 60,
            "",
        ]

        for i, violation in enumerate(hard_rules_result.violations, 1):
            lines.extend(
                [
                    f"[{i}] {violation.rule_name}",
                    f"    Rule ID: {violation.rule_id}",
                    f"    Severity: {violation.severity.upper()}",
                    f"    Action: {violation.action}",
                    f"    Message: {violation.message}",
                ]
            )

            if violation.matched_pattern:
                lines.append(f"    Matched Pattern: {violation.matched_pattern}")

            if violation.matched_text:
                lines.append(f"    Matched Text: {violation.matched_text}")

            lines.append("")

        return "\n".join(lines)

    def _format_rubric_evaluation(self, rubric_result: RubricEvaluationResult) -> str:
        """
        Rubric評価結果を整形されたテキストに変換

        Args:
            rubric_result: Rubric評価結果

        Returns:
            整形されたテキスト
        """
        lines = [
            "=" * 60,
            "RUBRIC EVALUATION (LLM-BASED)",
            "=" * 60,
            "",
            f"Total Score: {rubric_result.total_score}/{rubric_result.max_possible_score}",
            f"Score Rate: {rubric_result.score_rate:.1%}",
            f"Pass Threshold: {rubric_result.pass_threshold:.0%}",
            f"Status: {'✅ PASS' if rubric_result.is_pass else '❌ FAIL'}",
            "",
            "=" * 60,
            "CRITERION RESULTS",
            "=" * 60,
            "",
        ]

        for i, criterion in enumerate(rubric_result.criteria_results, 1):
            status_emoji = {"Yes": "✅", "Partial": "⚠️", "No": "❌"}
            emoji = status_emoji.get(criterion.judgment, "❓")

            lines.extend(
                [
                    f"[{i}] {criterion.name} {emoji}",
                    f"    Criterion ID: {criterion.criterion_id}",
                    f"    Judgment: {criterion.judgment}",
                    f"    Score: {criterion.score}/{criterion.max_score}",
                    f"    Type: {criterion.type}",
                    f"    Reasoning: {criterion.reasoning}",
                    "",
                ]
            )

        lines.extend(
            [
                "=" * 60,
                "OVERALL JUDGMENT",
                "=" * 60,
                "",
                rubric_result.overall_judgment,
            ]
        )

        return "\n".join(lines)

    def get_run_by_id(self, run_id: str) -> Any:
        """
        Run IDでRunを取得

        Args:
            run_id: Run ID

        Returns:
            MLflow Run オブジェクト
        """
        return self.client.get_run(run_id)

    def search_runs(
        self,
        filter_string: str = "",
        max_results: int = 100,
    ) -> list[Any]:
        """
        条件でRunを検索

        Args:
            filter_string: フィルタ文字列（例: "params.test_case_id = 'TEST-LT-001'"）
            max_results: 最大取得件数

        Returns:
            Run のリスト
        """
        runs = mlflow.search_runs(
            experiment_ids=[self.experiment_id],
            filter_string=filter_string,
            max_results=max_results,
        )
        # mlflow.search_runs returns pandas DataFrame
        return runs.to_dict("records") if not runs.empty else []  # type: ignore[union-attr]


def get_mlflow_tracker() -> MLflowTrackerService:
    """
    MLflow tracker サービスのシングルトンインスタンスを取得

    Returns:
        MLflowTrackerService インスタンス
    """
    return MLflowTrackerService()
