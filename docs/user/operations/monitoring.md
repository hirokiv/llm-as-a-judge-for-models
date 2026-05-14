# モニタリング

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## Prometheus メトリクス

以下のメトリクスを収集：

- **リクエスト数**: `http_requests_total`
- **レスポンスタイム**: `http_request_duration_seconds`
- **エラー率**: `http_requests_errors_total`
- **LLM API呼び出し**: `llm_api_calls_total`

## Grafana ダッシュボード

以下のダッシュボードを提供：

- システム概要
- API パフォーマンス
- LLM 使用状況
- エラートレンド

## アラート設定

### 重要なアラート

- エラー率 > 5%
- レスポンスタイム P95 > 10秒
- ディスク使用率 > 80%

詳細は[設計書](../../design/14_logging_strategy.md)を参照してください。
