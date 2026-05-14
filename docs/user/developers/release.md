# リリースプロセス

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## バージョニング

Semantic Versioningに従います：

```
MAJOR.MINOR.PATCH
```

- **MAJOR**: 互換性のない変更
- **MINOR**: 後方互換性のある機能追加
- **PATCH**: 後方互換性のあるバグ修正

## リリース手順

### 1. バージョン更新

```bash
# pyproject.toml
version = "1.1.0"

# CHANGELOG.md更新
```

### 2. テスト実行

```bash
make test
make lint
```

### 3. タグ作成

```bash
git tag v1.1.0
git push origin v1.1.0
```

### 4. GitHub Release

GitHubでリリースノートを作成します。

### 5. デプロイ

```bash
# ステージング
make deploy-staging

# 本番（確認後）
make deploy-production
```

## ロールバック

問題が発生した場合：

```bash
# 前のバージョンにロールバック
git revert HEAD
make deploy-production
```

詳細は[変更履歴](../changelog.md)を参照してください。
