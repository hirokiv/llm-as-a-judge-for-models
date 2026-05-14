"""
Repository Factory for LLM-as-a-Judge

環境変数に基づいて適切なRepositoryインスタンスを生成
"""

import os
from functools import lru_cache

from src.repositories.base import BaseRepository, RepositoryError
from src.repositories.databricks_repository import DatabricksRepository
from src.repositories.supabase_repository import SupabaseRepository


@lru_cache
def get_repository() -> BaseRepository:
    """環境変数に基づき適切なRepositoryインスタンスを返す

    環境変数:
        DB_PROVIDER: データベースプロバイダー（"supabase" | "databricks"）
        SUPABASE_URL: Supabase URL（DB_PROVIDER=supabaseの場合）
        SUPABASE_KEY: Supabase API Key（DB_PROVIDER=supabaseの場合）
        DATABRICKS_SERVER_HOSTNAME: Databricksサーバーホスト名（DB_PROVIDER=databricksの場合）
        DATABRICKS_HTTP_PATH: SQLウェアハウスのHTTPパス（DB_PROVIDER=databricksの場合）
        DATABRICKS_ACCESS_TOKEN: アクセストークン（DB_PROVIDER=databricksの場合）

    Returns:
        適切なRepositoryインスタンス

    Raises:
        RepositoryError: 環境変数が設定されていない場合

    Example:
        >>> repo = get_repository()
        >>> result = await repo.save_evaluation_result(...)
    """
    db_provider = os.getenv("DB_PROVIDER", "supabase").lower()

    if db_provider == "databricks":
        server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        http_path = os.getenv("DATABRICKS_HTTP_PATH")
        access_token = os.getenv("DATABRICKS_ACCESS_TOKEN")

        if not all([server_hostname, http_path, access_token]):
            raise RepositoryError(
                "Missing required environment variables for Databricks: "
                "DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_ACCESS_TOKEN"
            )

        return DatabricksRepository(
            server_hostname=server_hostname,
            http_path=http_path,
            access_token=access_token,
        )

    elif db_provider == "supabase":
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not all([supabase_url, supabase_key]):
            raise RepositoryError(
                "Missing required environment variables for Supabase: SUPABASE_URL, SUPABASE_KEY"
            )

        return SupabaseRepository(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
        )

    else:
        raise RepositoryError(
            f"Unknown DB_PROVIDER: {db_provider}. Supported providers: supabase, databricks"
        )


def clear_repository_cache():
    """Repositoryキャッシュをクリア

    テスト時や環境変数変更時に使用
    """
    get_repository.cache_clear()
