"""
Pytest configuration and fixtures for the entire test suite

全テストスイート用のPytest設定とフィクスチャ
"""

import os

import pytest
from fastapi.testclient import TestClient


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "requires_db: mark test as requiring database connection")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "stub_validation: mark test as stub validation test")


@pytest.fixture(scope="session", autouse=True)
def check_db_availability():
    """Check if database is available for tests that require it"""
    db_available = all(
        [
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY"),
            os.getenv("DB_PROVIDER"),
        ]
    )
    return db_available


def pytest_collection_modifyitems(config, items):
    """
    Skip tests marked with requires_db if database is not available

    データベースが利用できない場合、requires_dbマーカーのテストをスキップ
    """
    db_available = all(
        [
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY"),
            os.getenv("DB_PROVIDER"),
        ]
    )

    skip_db = pytest.mark.skip(reason="Database not available (missing env vars)")
    for item in items:
        if "requires_db" in item.keywords and not db_available:
            item.add_marker(skip_db)


@pytest.fixture(scope="session")
def test_app():
    """FastAPI application for testing.

    This fixture imports the app only when needed to avoid import errors
    during test collection.
    """
    from src.api.main import app

    return app


@pytest.fixture
def client(test_app, monkeypatch):
    """FastAPI test client with Stub LLM provider.

    This client automatically uses the Stub LLM provider for consistent,
    deterministic test results without requiring actual LLM API calls.
    """
    # Set environment to use Stub LLM provider
    monkeypatch.setenv("LLM_PROVIDER", "stub")

    # Set mock Supabase environment variables for E2E tests
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_KEY", "test-key-for-e2e-tests")
    monkeypatch.setenv("DB_PROVIDER", "supabase")

    # Override dependencies for E2E tests
    from src.api.dependencies import get_repository_dependency
    from src.repositories.memory_repository import InMemoryRepository
    from src.services.mock_mlflow_tracker import MockMLflowTracker

    # Create mock instances
    mock_repository = InMemoryRepository()
    mock_mlflow_tracker = MockMLflowTracker()

    # Override repository dependency
    async def override_get_repository():
        return mock_repository

    test_app.dependency_overrides[get_repository_dependency] = override_get_repository

    # Patch get_mlflow_tracker to return mock
    # Need to patch it in the evaluate module's namespace since it imports the function directly
    import src.api.routes.evaluate as evaluate_module
    import src.services.mlflow_tracker as mlflow_tracker_module

    original_get_mlflow_tracker = mlflow_tracker_module.get_mlflow_tracker
    original_evaluate_get_mlflow = evaluate_module.get_mlflow_tracker

    # Patch in all modules that import it
    mlflow_tracker_module.get_mlflow_tracker = lambda: mock_mlflow_tracker
    evaluate_module.get_mlflow_tracker = lambda: mock_mlflow_tracker

    with TestClient(test_app) as test_client:
        yield test_client

    # Restore original functions
    mlflow_tracker_module.get_mlflow_tracker = original_get_mlflow_tracker
    evaluate_module.get_mlflow_tracker = original_evaluate_get_mlflow

    # Clear dependency overrides
    test_app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests.

    Returns headers with a test API key for authentication.
    Uses the API key from environment or a default test key.
    """
    test_api_key = os.getenv("TEST_API_KEY", "test_api_key_1")
    return {"Authorization": f"Bearer {test_api_key}"}
