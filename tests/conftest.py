"""
Pytest configuration and fixtures for the entire test suite

全テストスイート用のPytest設定とフィクスチャ
"""

import os

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "requires_db: mark test as requiring database connection")
    config.addinivalue_line("markers", "requires_llm: mark test as requiring real LLM API")
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
    Skip tests based on environment availability:
    - requires_db: Skip if database is not available
    - requires_llm: Skip if LLM API is not available (dummy key)

    環境に応じてテストをスキップ
    """
    db_available = all(
        [
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY"),
            os.getenv("DB_PROVIDER"),
        ]
    )

    # Check if real LLM API is available (not dummy key)
    openai_key = os.getenv("OPENAI_API_KEY", "")
    llm_available = openai_key and not openai_key.startswith("sk-test-dummy")

    skip_db = pytest.mark.skip(reason="Database not available (missing env vars)")
    skip_llm = pytest.mark.skip(reason="Real LLM API not available (dummy/missing API key)")

    for item in items:
        if "requires_db" in item.keywords and not db_available:
            item.add_marker(skip_db)
        if "requires_llm" in item.keywords and not llm_available:
            item.add_marker(skip_llm)


@pytest.fixture(scope="session")
def test_app():
    """FastAPI application for testing.

    This fixture imports the app only when needed to avoid import errors
    during test collection.
    """
    from src.api.main import app

    return app


@pytest.fixture
def sync_client(test_app, monkeypatch):
    """Synchronous FastAPI test client with Stub LLM provider.

    This client automatically uses the Stub LLM provider for consistent,
    deterministic test results without requiring actual LLM API calls.

    Use this for synchronous tests. For async tests, use the 'client' fixture instead.
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


@pytest_asyncio.fixture
async def client(test_app, monkeypatch):
    """Async HTTP client for integration tests.

    This fixture provides an AsyncClient configured with:
    - Stub LLM provider (no real API calls)
    - In-memory repository
    - Mock MLflow tracker
    """
    # Set environment to use Stub LLM provider
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_KEY", "test-key-for-integration-tests")
    monkeypatch.setenv("DB_PROVIDER", "supabase")

    # Override dependencies
    from src.api.dependencies import get_repository_dependency
    from src.repositories.memory_repository import InMemoryRepository
    from src.services.mock_mlflow_tracker import MockMLflowTracker

    mock_repository = InMemoryRepository()
    mock_mlflow_tracker = MockMLflowTracker()

    async def override_get_repository():
        return mock_repository

    test_app.dependency_overrides[get_repository_dependency] = override_get_repository

    # Patch MLflow tracker
    import src.api.routes.evaluate as evaluate_module
    import src.api.routes.proxy as proxy_module
    import src.services.mlflow_tracker as mlflow_tracker_module

    original_get_mlflow_tracker = mlflow_tracker_module.get_mlflow_tracker

    mlflow_tracker_module.get_mlflow_tracker = lambda: mock_mlflow_tracker
    evaluate_module.get_mlflow_tracker = lambda: mock_mlflow_tracker
    if hasattr(proxy_module, 'get_mlflow_tracker'):
        proxy_module.get_mlflow_tracker = lambda: mock_mlflow_tracker

    # Create async client
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    # Cleanup
    mlflow_tracker_module.get_mlflow_tracker = original_get_mlflow_tracker
    test_app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests.

    Returns headers with a test API key for authentication.
    Uses the API key from environment or a default test key.
    """
    test_api_key = os.getenv("TEST_API_KEY", "test_api_key_1")
    return {"Authorization": f"Bearer {test_api_key}"}
