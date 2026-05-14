"""
Pytest configuration and fixtures for the entire test suite

全テストスイート用のPytest設定とフィクスチャ
"""

import os

import pytest


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "requires_db: mark test as requiring database connection")


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
