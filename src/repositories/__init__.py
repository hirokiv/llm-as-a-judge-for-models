"""
Repository package for LLM-as-a-Judge

データアクセス層のパッケージ
"""

from src.repositories.base import (
    BaseRepository,
    RepositoryConnectionError,
    RepositoryDuplicateError,
    RepositoryError,
    RepositoryNotFoundError,
)
from src.repositories.databricks_repository import DatabricksRepository
from src.repositories.factory import clear_repository_cache, get_repository
from src.repositories.supabase_repository import SupabaseRepository

__all__ = [
    # Base
    "BaseRepository",
    "RepositoryError",
    "RepositoryConnectionError",
    "RepositoryNotFoundError",
    "RepositoryDuplicateError",
    # Implementations
    "SupabaseRepository",
    "DatabricksRepository",
    # Factory
    "get_repository",
    "clear_repository_cache",
]
