# トラブルシューティング

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## よくある問題

### APIが起動しない

#### 症状
```
ERROR: Port 8000 is already in use
```

#### 解決方法
```bash
# ポートを使用しているプロセスを確認
lsof -i :8000

# プロセスを終了
kill -9 <PID>
```

### データベース接続エラー

#### 症状
```
ERROR: Connection to database failed
```

#### 解決方法
```bash
# 環境変数確認
make check-env

# 接続テスト
psql $DATABASE_URL
```

### LLM API エラー

#### 症状
```
ERROR: OpenAI API rate limit exceeded
```

#### 解決方法
```python
# config.pyで調整
MAX_CONCURRENT_REQUESTS = 5  # デフォルト: 10
```

## ログ確認

```bash
# アプリケーションログ
tail -f logs/app.log

# エラーログ
grep ERROR logs/app.log
```

詳細は[FAQ](../faq.md)を参照してください。
