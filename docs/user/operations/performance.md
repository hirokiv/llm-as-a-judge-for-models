# パフォーマンスチューニング

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## パフォーマンス目標

- **レスポンスタイム P95**: < 10秒
- **スループット**: 100 req/min
- **同時接続数**: 50

## チューニングポイント

### 1. ワーカー数調整

```python
# config.py
MAX_WORKERS = 20  # デフォルト: 10
MAX_CONCURRENT_REQUESTS = 20  # デフォルト: 10
```

### 2. データベース接続プール

```python
# config.py
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 10
```

### 3. キャッシュ有効化

```python
# config.py
CACHE_ENABLED = True
CACHE_TTL_SECONDS = 300  # 5分
```

### 4. LLM API タイムアウト

```python
# config.py
LLM_API_TIMEOUT_SECONDS = 60
```

## パフォーマンステスト

```bash
# Locustで負荷テスト
locust -f tests/performance/locustfile.py
```

詳細は[設計書](../../design/00_overview.md)を参照してください。
