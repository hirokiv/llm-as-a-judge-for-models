# テスト実行

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## テストの種類

### 単体テスト

```bash
# 全単体テスト
make test-unit

# 特定のファイル
pytest tests/unit/models/test_judge_result.py

# 特定のテスト
pytest tests/unit/models/test_judge_result.py::test_risk_score_validation
```

### 統合テスト

```bash
# 全統合テスト
make test-integration

# データベース統合テスト
pytest tests/integration/repositories/
```

### E2Eテスト

```bash
# E2Eテスト
make test-e2e

# マーカー指定
pytest -m e2e
```

## カバレッジ

```bash
# カバレッジ付きテスト
make test-cov

# HTMLレポート
open htmlcov/index.html
```

## テスト監視モード

```bash
# ファイル変更時に自動実行
make test-watch
```

## テスト作成ガイドライン

### 命名規則

- ファイル: `test_*.py`
- クラス: `Test*`
- 関数: `test_*`

### 構造

```python
def test_something():
    # Arrange: テストデータ準備
    test_case = TestCase(...)
    
    # Act: 実行
    result = evaluate(test_case)
    
    # Assert: 検証
    assert result.is_safe is True
```

詳細は[テスト設計書](../../design/16_test_design.md)を参照してください。
