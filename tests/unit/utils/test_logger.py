"""
Unit tests for logger module

ロガーモジュールの単体テスト
"""


from src.utils.logger import get_logger, mask_sensitive_data


class TestMaskSensitiveData:
    """機密情報マスキングのテスト"""

    def test_mask_email(self):
        """メールアドレスがマスキングされること"""
        text = "Contact us at support@example.com for help"
        masked = mask_sensitive_data(text)
        assert "support@example.com" not in masked
        assert "[REDACTED_EMAIL]" in masked

    def test_mask_api_key_openai(self):
        """OpenAI APIキーがマスキングされること"""
        # OpenAI APIキーは sk- + 48文字の英数字
        text = "API Key: sk-" + "a" * 48
        masked = mask_sensitive_data(text)
        assert "sk-aaa" not in masked
        assert "[REDACTED_API_KEY]" in masked

    def test_mask_api_key_jwt(self):
        """JWT トークンがマスキングされること"""
        text = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        masked = mask_sensitive_data(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked
        assert "[REDACTED_API_KEY]" in masked

    def test_mask_credit_card(self):
        """クレジットカード番号がマスキングされること"""
        text = "Card: 1234-5678-9012-3456"
        masked = mask_sensitive_data(text)
        assert "1234-5678-9012-3456" not in masked
        assert "[REDACTED_CREDIT_CARD]" in masked

    def test_mask_phone_number(self):
        """電話番号がマスキングされること"""
        text = "Call us at 123-456-7890"
        masked = mask_sensitive_data(text)
        assert "123-456-7890" not in masked
        assert "[REDACTED_PHONE]" in masked

    def test_mask_ssn(self):
        """SSN（社会保障番号）がマスキングされること"""
        text = "SSN: 123-45-6789"
        masked = mask_sensitive_data(text)
        assert "123-45-6789" not in masked
        assert "[REDACTED_SSN]" in masked

    def test_mask_dict(self):
        """辞書内の機密情報がマスキングされること"""
        data = {
            "email": "user@example.com",
            "api_key": "sk-" + "a" * 48,
            "message": "Contact support@test.com",
        }
        masked = mask_sensitive_data(data)

        assert "[REDACTED_EMAIL]" in masked["email"]
        assert "[REDACTED_API_KEY]" in masked["api_key"]
        assert "[REDACTED_EMAIL]" in masked["message"]

    def test_mask_list(self):
        """リスト内の機密情報がマスキングされること"""
        data = ["user@example.com", "sk-" + "a" * 48, "normal text"]
        masked = mask_sensitive_data(data)

        assert "[REDACTED_EMAIL]" in masked[0]
        assert "[REDACTED_API_KEY]" in masked[1]
        assert masked[2] == "normal text"

    def test_mask_nested_structure(self):
        """ネストされた構造の機密情報がマスキングされること"""
        data = {
            "user": {
                "email": "admin@example.com",
                "contacts": ["support@test.com", "info@test.com"],
            },
            "api_keys": ["sk-" + "a" * 48, "sk-" + "b" * 48],
        }
        masked = mask_sensitive_data(data)

        assert "[REDACTED_EMAIL]" in masked["user"]["email"]
        assert all("[REDACTED_EMAIL]" in c for c in masked["user"]["contacts"])
        assert all("[REDACTED_API_KEY]" in k for k in masked["api_keys"])

    def test_no_masking_for_non_sensitive(self):
        """機密情報でないテキストはそのまま返されること"""
        text = "This is a normal text without sensitive data"
        masked = mask_sensitive_data(text)
        assert masked == text

    def test_mask_multiple_patterns(self):
        """複数の機密情報が同時にマスキングされること"""
        text = "Email: user@test.com, API Key: sk-" + "a" * 48 + ", Card: 1234567890123456"
        masked = mask_sensitive_data(text)

        assert "[REDACTED_EMAIL]" in masked
        assert "[REDACTED_API_KEY]" in masked
        assert "[REDACTED_CREDIT_CARD]" in masked


class TestGetLogger:
    """ロガー取得のテスト"""

    def test_get_logger(self):
        """ロガーが取得できること"""
        logger = get_logger(__name__)
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_logger_info(self):
        """infoレベルのログが出力できること"""
        logger = get_logger(__name__)
        # ログ出力が例外を発生させないことを確認
        logger.info("Test info message", extra_field="value")

    def test_logger_with_context(self):
        """コンテキスト情報付きログが出力できること"""
        logger = get_logger(__name__)
        logger.info(
            "API request",
            endpoint="/api/v1/evaluate",
            method="POST",
            status_code=200,
        )
