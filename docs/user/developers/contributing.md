# コントリビューションガイド

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## 開発フロー

### 1. Issueの確認

GitHubのIssueを確認し、担当する問題を選択します。

### 2. ブランチ作成

```bash
git checkout -b feature/your-feature-name
```

ブランチ命名規則：

- `feature/`: 新機能
- `fix/`: バグ修正
- `docs/`: ドキュメント
- `refactor/`: リファクタリング

### 3. 実装

```bash
# コード実装
# テスト作成
pytest tests/
```

### 4. コード品質チェック

```bash
# フォーマット
make format

# リント
make lint

# 型チェック
mypy src/
```

### 5. コミット

```bash
git add .
git commit -m "feat: Add new feature"
```

コミットメッセージ規則：

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント
- `test:` テスト
- `refactor:` リファクタリング

### 6. プルリクエスト

```bash
git push origin feature/your-feature-name
```

GitHubでPRを作成します。

## コードレビュー

- 2人以上の承認が必要
- CI/CDパイプラインが成功していること
- テストカバレッジ80%以上

## 行動規範

- 尊重と敬意を持って
- 建設的なフィードバック
- オープンなコミュニケーション
