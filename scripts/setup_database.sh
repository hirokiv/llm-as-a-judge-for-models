#!/bin/bash
# Database setup script for LLM-as-a-Judge
# Supabaseローカル環境のセットアップとマイグレーション実行

set -e

echo "🚀 Starting Supabase local environment setup..."

# 1. Dockerが起動しているか確認
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# 2. Supabaseローカル環境を起動
echo "📦 Starting Supabase local environment..."
supabase start

# 3. マイグレーションの状態確認
echo "🔍 Checking migration status..."
supabase migration list

# 4. マイグレーションを実行
echo "⚡ Running database migrations..."
supabase db reset

# 5. データベース接続情報を表示
echo ""
echo "✅ Database setup completed!"
echo ""
echo "📋 Connection details:"
supabase status | grep -E "(API URL|DB URL|Studio URL|anon key)"

echo ""
echo "🎉 Setup complete! You can now:"
echo "  - Access Studio UI: http://localhost:54323"
echo "  - Connect to DB: postgresql://postgres:postgres@localhost:54322/postgres"
echo "  - Use API: http://localhost:54321"
