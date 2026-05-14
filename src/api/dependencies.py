"""
FastAPI dependencies for LLM-as-a-Judge

依存性注入の定義
"""

from typing import Annotated

from fastapi import Depends

from src.repositories.base import BaseRepository
from src.repositories.factory import get_repository


# Repository依存性注入
async def get_repository_dependency() -> BaseRepository:
    """Repository依存性注入

    環境変数に基づき適切なRepositoryインスタンスを返す

    Returns:
        BaseRepository: Repositoryインスタンス

    Example:
        ```python
        @app.get("/example")
        async def example(repo: Annotated[BaseRepository, Depends(get_repository_dependency)]):
            result = await repo.list_evaluation_results()
            return result
        ```
    """
    return get_repository()


# 型エイリアス（便利な型定義）
RepositoryDep = Annotated[BaseRepository, Depends(get_repository_dependency)]


# TODO: 認証依存性注入（Phase 6-8で実装）
# async def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
# ) -> dict:
#     """JWT認証"""
#     token = credentials.credentials
#     # JWT検証ロジック
#     return {"user_id": "user123", "role": "admin"}
#
# CurrentUserDep = Annotated[dict, Depends(get_current_user)]
