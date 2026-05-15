"""
Integration tests for database configuration loading

DB-first with YAML fallback 統合テスト
"""

import pytest

from src.config.loader import ConfigLoader
from src.repositories.memory_repository import InMemoryRepository
from src.utils.rubric_loader import load_rubric_criteria_async
from src.utils.test_case_loader import TestCaseLoader


@pytest.fixture
def enable_db_config(monkeypatch):
    """Enable USE_DB_CONFIG environment variable"""
    monkeypatch.setenv("USE_DB_CONFIG", "true")


@pytest.fixture
def disable_db_config(monkeypatch):
    """Disable USE_DB_CONFIG environment variable"""
    monkeypatch.setenv("USE_DB_CONFIG", "false")


@pytest.fixture
async def seeded_repository():
    """Create in-memory repository with seeded config data"""
    repo = InMemoryRepository()

    # Seed system configs
    await repo.upsert_system_config(
        config_key="application.name",
        value="LLM-as-a-Judge Test",
        value_type="string",
        environment="default",
    )
    await repo.upsert_system_config(
        config_key="application.version",
        value="1.0.0-test",
        value_type="string",
        environment="default",
    )
    await repo.upsert_system_config(
        config_key="application.api.port",
        value="8000",
        value_type="integer",
        environment="default",
    )

    # Seed target AI system
    await repo.upsert_target_ai_system(
        name="default",
        url="http://localhost:8080/api/chat",
        headers={"Content-Type": "application/json"},
        request_config={"method": "POST", "body_template": "{}"},
        response_config={"output_path": "$.result"},
        timeout_seconds=30,
    )

    # Seed evaluation criteria
    await repo.upsert_evaluation_criteria(
        name="default",
        version="1.0",
        hard_rules=[],
        soft_judge_criteria=[],
        risk_score_config={"method": "weighted_average"},
        recommendation_templates={},
    )

    return repo


class TestConfigLoaderDBIntegration:
    """ConfigLoader database integration tests"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_load_system_defaults_from_yaml_when_disabled(self, disable_db_config):
        """Test that YAML is used when USE_DB_CONFIG=false"""
        config = await ConfigLoader.load_system_defaults_async()

        assert "application" in config
        assert config["application"]["name"] == "LLM-as-a-Judge for Enterprise Systems"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_load_system_defaults_fallback_to_yaml(
        self, enable_db_config, monkeypatch, seeded_repository
    ):
        """Test fallback to YAML when DB is empty"""
        # Mock get_repository to return empty repository
        from src.repositories import factory

        monkeypatch.setattr(factory, "_repository", InMemoryRepository())

        config = await ConfigLoader.load_system_defaults_async()

        # Should fall back to YAML
        assert "application" in config
        assert config["application"]["name"] == "LLM-as-a-Judge for Enterprise Systems"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_load_target_ai_system_from_yaml_when_disabled(self, disable_db_config):
        """Test that YAML is used when USE_DB_CONFIG=false"""
        config = await ConfigLoader.load_target_ai_system_async()

        assert "url" in config
        assert config["url"] == "http://localhost:8080/api/chat"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_load_rubric_criteria_from_yaml_when_disabled(self, disable_db_config):
        """Test that YAML is used when USE_DB_CONFIG=false"""
        criteria = await load_rubric_criteria_async()

        assert criteria.version == "1.0"
        assert criteria.soft_judge is not None


class TestTestCaseLoaderDBIntegration:
    """TestCaseLoader database integration tests"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_test_cases_from_yaml_when_disabled(self, disable_db_config):
        """Test that YAML is used when USE_DB_CONFIG=false"""
        loader = TestCaseLoader()
        test_case_ids = await loader.list_test_cases_async()

        # Should return test cases from YAML files
        assert len(test_case_ids) > 0
        assert all(isinstance(tc_id, str) for tc_id in test_case_ids)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_test_cases_fallback_to_yaml(self, enable_db_config, monkeypatch):
        """Test fallback to YAML when DB is empty"""
        # Mock get_repository to return empty repository
        from src.repositories import factory

        monkeypatch.setattr(factory, "_repository", InMemoryRepository())

        loader = TestCaseLoader()
        test_case_ids = await loader.list_test_cases_async()

        # Should fall back to YAML
        assert len(test_case_ids) > 0


class TestUnflattenDict:
    """Test _unflatten_dict functionality"""

    def test_unflatten_simple_dict(self):
        """Test unflattening simple key-value pairs"""
        configs = [
            {"config_key": "application.name", "value": "Test App", "value_type": "string"},
            {"config_key": "application.version", "value": "1.0", "value_type": "string"},
        ]

        result = ConfigLoader._unflatten_dict(configs)

        assert result["application"]["name"] == "Test App"
        assert result["application"]["version"] == "1.0"

    def test_unflatten_nested_dict(self):
        """Test unflattening nested key-value pairs"""
        configs = [
            {
                "config_key": "application.api.port",
                "value": "8000",
                "value_type": "integer",
            },
            {
                "config_key": "application.api.host",
                "value": "0.0.0.0",
                "value_type": "string",
            },
        ]

        result = ConfigLoader._unflatten_dict(configs)

        assert result["application"]["api"]["port"] == 8000
        assert result["application"]["api"]["host"] == "0.0.0.0"

    def test_unflatten_type_conversion(self):
        """Test type conversion during unflattening"""
        configs = [
            {"config_key": "debug.enabled", "value": "true", "value_type": "boolean"},
            {"config_key": "debug.level", "value": "10", "value_type": "integer"},
            {"config_key": "debug.threshold", "value": "0.5", "value_type": "float"},
        ]

        result = ConfigLoader._unflatten_dict(configs)

        assert result["debug"]["enabled"] is True
        assert result["debug"]["level"] == 10
        assert result["debug"]["threshold"] == 0.5


class TestEnvironmentVariableCheck:
    """Test USE_DB_CONFIG environment variable checking"""

    def test_use_db_config_true(self, monkeypatch):
        """Test USE_DB_CONFIG=true"""
        monkeypatch.setenv("USE_DB_CONFIG", "true")
        assert ConfigLoader._use_db_config() is True

    def test_use_db_config_false(self, monkeypatch):
        """Test USE_DB_CONFIG=false"""
        monkeypatch.setenv("USE_DB_CONFIG", "false")
        assert ConfigLoader._use_db_config() is False

    def test_use_db_config_default(self, monkeypatch):
        """Test default behavior when USE_DB_CONFIG is not set"""
        monkeypatch.delenv("USE_DB_CONFIG", raising=False)
        assert ConfigLoader._use_db_config() is False
