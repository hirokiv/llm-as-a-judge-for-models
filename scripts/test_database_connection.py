#!/usr/bin/env python
"""
Database connection test script for LLM-as-a-Judge

Supabaseローカル環境への接続をテストし、テーブルの存在を確認します。
"""

import asyncio
import os
import sys

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.repositories.factory import get_repository


async def test_connection():
    """データベース接続テスト"""
    print("🔍 Testing database connection...")
    print(f"DB_PROVIDER: {os.getenv('DB_PROVIDER', 'supabase')}")
    print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'Not set')}")
    print()

    try:
        # Repositoryインスタンス取得
        print("📦 Creating repository instance...")
        repo = get_repository()
        print(f"✅ Repository created: {type(repo).__name__}")
        print()

        # ヘルスチェック
        print("🏥 Running health check...")
        is_healthy = await repo.health_check()

        if is_healthy:
            print("✅ Health check passed!")
        else:
            print("❌ Health check failed!")
            return False

        print()

        # テーブル存在確認（空のリスト取得）
        print("📋 Checking tables...")

        print("  - evaluation_results table...")
        results = await repo.list_evaluation_results(limit=1)
        print(f"    ✅ Table exists (found {len(results)} records)")

        print("  - idempotency_checks table...")
        checks = await repo.list_idempotency_checks(limit=1)
        print(f"    ✅ Table exists (found {len(checks)} records)")

        print()
        print("🎉 All tests passed! Database is ready.")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("💡 Troubleshooting:")
        print("  1. Is Supabase running? Run: supabase status")
        print("  2. Are environment variables set? Check .env file")
        print("  3. Is Docker running?")
        return False


def main():
    """メイン関数"""
    # .envファイルを読み込み（python-dotenv使用）
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("✅ .env file loaded")
        print()
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment variables")
        print()

    # 非同期テスト実行
    success = asyncio.run(test_connection())

    # 終了コード
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
