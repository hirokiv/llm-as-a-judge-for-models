# セキュリティベストプラクティス

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## API キー管理

### 開発環境

- `.env`ファイルに保存
- `.gitignore`に追加
- 絶対にコミットしない

### 本番環境

- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

## データベースセキュリティ

- RLS（Row Level Security）有効化
- 最小権限の原則
- 定期的なバックアップ

## ログ管理

### 機密情報のマスキング

自動的に以下をマスキング：

- メールアドレス → `[REDACTED:EMAIL]`
- APIキー → `[REDACTED:API_KEY]`
- クレジットカード番号 → `[REDACTED:CREDIT_CARD]`

## 監査ログ

- 全操作を記録
- 7年間保持（デフォルト）
- 改ざん防止

詳細は[設計書](../../design/04_authentication.md)と[ログ戦略](../../design/14_logging_strategy.md)を参照してください。
