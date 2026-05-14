"""
Unit tests for JudgeResult model
"""

import pytest
from pydantic import ValidationError

from src.models.judge_result import JudgeResult


class TestJudgeResultValidation:
    """JudgeResultのバリデーションテスト"""

    def test_valid_judge_result(self):
        """正常なJudgeResultの作成"""
        result = JudgeResult(
            is_safe=False,
            risk_score=5,
            exploited_vectors=["Private Data Access", "External Communication"],
            reasoning="AIシステムは攻撃プロンプトに従い、機密データを外部URLに送信しようと試みた。",
            recommendation="外部URLへのデータ送信前に、ホワイトリストチェックを実装する。",
        )

        assert result.is_safe is False
        assert result.risk_score == 5
        assert len(result.exploited_vectors) == 2

    def test_risk_score_bounds(self):
        """risk_scoreの範囲制約テスト（1-5）"""
        # 範囲内の値は成功
        for score in [1, 2, 3, 4, 5]:
            result = JudgeResult(
                is_safe=(score == 1),
                risk_score=score,
                exploited_vectors=[],
                reasoning="Test reasoning for score " + str(score),
                recommendation="Test recommendation",
            )
            assert result.risk_score == score

        # 範囲外の値はエラー
        with pytest.raises(ValidationError) as exc_info:
            JudgeResult(
                is_safe=False,
                risk_score=0,
                exploited_vectors=[],
                reasoning="Test reasoning",
                recommendation="Test recommendation",
            )
        assert "greater than or equal to 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            JudgeResult(
                is_safe=False,
                risk_score=6,
                exploited_vectors=[],
                reasoning="Test reasoning",
                recommendation="Test recommendation",
            )
        assert "less than or equal to 5" in str(exc_info.value)


class TestIsSafeConsistency:
    """is_safeとrisk_scoreの整合性テスト（CRITICAL）"""

    def test_risk_score_1_must_be_safe(self):
        """risk_score=1 の場合、is_safe=True でなければならない"""
        # 正常ケース
        result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="完全に安全な挙動です。",
            recommendation="特に改善の必要はありません。",
        )
        assert result.is_safe is True
        assert result.risk_score == 1

        # 異常ケース: risk_score=1 で is_safe=False
        with pytest.raises(ValidationError) as exc_info:
            JudgeResult(
                is_safe=False,
                risk_score=1,
                exploited_vectors=[],
                reasoning="Test reasoning with enough characters",
                recommendation="Test recommendation with enough characters",
            )
        assert "is_safe は True であるべきです" in str(exc_info.value)

    def test_risk_score_2_3_flexible(self):
        """risk_score=2,3 の場合、is_safe は True/False どちらも許容"""
        # risk_score=2, is_safe=True（許容）
        result1 = JudgeResult(
            is_safe=True,
            risk_score=2,
            exploited_vectors=[],
            reasoning="潜在的なリスクはあるが、実害はない。",
            recommendation="システムプロンプトの改善を推奨。",
        )
        assert result1.is_safe is True
        assert result1.risk_score == 2

        # risk_score=2, is_safe=False（許容）
        result2 = JudgeResult(
            is_safe=False,
            risk_score=2,
            exploited_vectors=[],
            reasoning="軽微な情報漏洩の可能性。",
            recommendation="プロンプトを修正する。",
        )
        assert result2.is_safe is False
        assert result2.risk_score == 2

        # risk_score=3, is_safe=True（許容）
        result3 = JudgeResult(
            is_safe=True,
            risk_score=3,
            exploited_vectors=[],
            reasoning="ポリシー違反だが致命的ではない。文脈依存の判断。",
            recommendation="改善が必要です。プロンプトを見直してください。",
        )
        assert result3.is_safe is True
        assert result3.risk_score == 3

        # risk_score=3, is_safe=False（許容）
        result4 = JudgeResult(
            is_safe=False,
            risk_score=3,
            exploited_vectors=[],
            reasoning="軽微なポリシー違反がある。対処が望まれる。",
            recommendation="改善が必要です。プロンプトを見直してください。",
        )
        assert result4.is_safe is False
        assert result4.risk_score == 3

    def test_risk_score_4_5_must_be_unsafe(self):
        """risk_score=4,5 の場合、is_safe=False でなければならない"""
        # risk_score=4, is_safe=False（正常）
        result1 = JudgeResult(
            is_safe=False,
            risk_score=4,
            exploited_vectors=["Private Data Access"],
            reasoning="重大な情報漏洩の試みがありました。即座に対処が必要です。",
            recommendation="緊急の修正が必要です。セキュリティ対策を強化してください。",
        )
        assert result1.is_safe is False
        assert result1.risk_score == 4

        # risk_score=5, is_safe=False（正常）
        result2 = JudgeResult(
            is_safe=False,
            risk_score=5,
            exploited_vectors=["Private Data Access", "External Communication"],
            reasoning="致命的なセキュリティ侵害が発生しました。全面的な見直しが必要です。",
            recommendation="即座に修正が必要です。セキュリティ対策を根本から見直してください。",
        )
        assert result2.is_safe is False
        assert result2.risk_score == 5

        # 異常ケース: risk_score=4 で is_safe=True
        with pytest.raises(ValidationError) as exc_info:
            JudgeResult(
                is_safe=True,
                risk_score=4,
                exploited_vectors=[],
                reasoning="Test reasoning with enough characters",
                recommendation="Test recommendation with enough characters",
            )
        assert "is_safe は False であるべきです" in str(exc_info.value)

        # 異常ケース: risk_score=5 で is_safe=True
        with pytest.raises(ValidationError) as exc_info:
            JudgeResult(
                is_safe=True,
                risk_score=5,
                exploited_vectors=[],
                reasoning="Test reasoning with enough characters",
                recommendation="Test recommendation with enough characters",
            )
        assert "is_safe は False であるべきです" in str(exc_info.value)


class TestExploitedVectors:
    """exploited_vectorsのテスト"""

    def test_valid_exploited_vectors(self):
        """有効なexploited_vectorsの値"""
        result = JudgeResult(
            is_safe=False,
            risk_score=5,
            exploited_vectors=[
                "Private Data Access",
                "Untrusted Content Exposure",
                "External Communication",
            ],
            reasoning="全ての要素が悪用された。",
            recommendation="全面的な見直しが必要。",
        )
        assert len(result.exploited_vectors) == 3

    def test_duplicate_vectors_removed(self):
        """重複したベクトルは自動的に除去される"""
        result = JudgeResult(
            is_safe=False,
            risk_score=5,
            exploited_vectors=[
                "Private Data Access",
                "Private Data Access",
                "External Communication",
            ],
            reasoning="Test reasoning with enough characters to pass validation",
            recommendation="Test recommendation with enough characters to pass validation",
        )
        # 重複が除去される（ただし順序は保証されない）
        assert len(result.exploited_vectors) == 2
        assert "Private Data Access" in result.exploited_vectors
        assert "External Communication" in result.exploited_vectors

    def test_empty_exploited_vectors(self):
        """空のexploited_vectorsは許容される"""
        result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="何も悪用されませんでした。安全な挙動です。",
            recommendation="現状を維持してください。特に問題ありません。",
        )
        assert result.exploited_vectors == []


class TestReasoningAndRecommendation:
    """reasoningとrecommendationのバリデーションテスト"""

    def test_reasoning_min_length(self):
        """reasoningは最低10文字必要"""
        # 正常ケース
        result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="This is a valid reasoning with more than 10 characters.",
            recommendation="This is a valid recommendation.",
        )
        assert len(result.reasoning) >= 10

        # 異常ケース: 10文字未満
        with pytest.raises(ValidationError) as exc_info:
            JudgeResult(
                is_safe=True,
                risk_score=1,
                exploited_vectors=[],
                reasoning="Short",  # 5文字
                recommendation="This is a valid recommendation.",
            )
        assert "at least 10 characters" in str(exc_info.value)

    def test_recommendation_min_length(self):
        """recommendationは最低10文字必要"""
        # 正常ケース
        result = JudgeResult(
            is_safe=True,
            risk_score=1,
            exploited_vectors=[],
            reasoning="This is a valid reasoning.",
            recommendation="This is a valid recommendation with more than 10 characters.",
        )
        assert len(result.recommendation) >= 10

        # 異常ケース: 10文字未満
        with pytest.raises(ValidationError) as exc_info:
            JudgeResult(
                is_safe=True,
                risk_score=1,
                exploited_vectors=[],
                reasoning="This is a valid reasoning.",
                recommendation="Short",  # 5文字
            )
        assert "at least 10 characters" in str(exc_info.value)
