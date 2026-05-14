"""
Environment setup validation tests

環境セットアップの検証テスト
"""

import os
import sys
from importlib import import_module

import pytest


class TestEnvironmentSetup:
    """環境セットアップの検証"""

    def test_python_version(self):
        """Python 3.10以上であることを確認"""
        assert sys.version_info >= (
            3,
            10,
        ), f"Python 3.10+ required, got {sys.version_info.major}.{sys.version_info.minor}"

    def test_required_packages_installed(self):
        """必須パッケージがインストールされていることを確認"""
        required_packages = [
            "fastapi",
            "pydantic",
            "mlflow",
            "supabase",
            "pytest",
        ]
        for package in required_packages:
            try:
                import_module(package)
            except ImportError:
                pytest.fail(f"Required package '{package}' is not installed")

    def test_environment_variables_exist(self):
        """必須環境変数が設定されていることを確認（MVP版）"""
        required_env_vars = [
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "DB_PROVIDER",
            "LLM_PROVIDER",
            "ENVIRONMENT",
        ]
        missing = [var for var in required_env_vars if not os.getenv(var)]
        if missing:
            pytest.skip(f"Missing environment variables (OK for CI): {missing}")

    def test_directory_structure(self):
        """プロジェクトディレクトリ構造が存在することを確認"""
        required_dirs = [
            "src/api",
            "src/models",
            "src/repositories",
            "tests/unit",
            "tests/integration",
            "config",
        ]
        for dir_path in required_dirs:
            assert os.path.isdir(dir_path), f"Required directory '{dir_path}' does not exist"
