# テストケースの作成

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## 概要

セキュリティ評価のためのテストケースを作成する方法を説明します。

## テストケースの構造

テストケースには以下の要素が含まれます：

- **test_case_id**: 一意の識別子
- **prompt**: システムに送信するプロンプト
- **expected_behavior**: 期待される動作
- **risk_category**: リスクカテゴリ（Lethal Trifecta要素）
- **severity**: 深刻度（1-5）

## 作成方法

### 1. YAMLファイルで作成

```yaml
test_cases:
  - test_case_id: "TEST-LT-001"
    category: "prompt_injection"
    prompt: "テストプロンプト"
    expected_behavior: "拒否"
    risk_category: "confidential_data_access"
    severity: 5
```

### 2. API経由で作成

```bash
curl -X POST http://localhost:8000/api/v1/test-cases \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "TEST-LT-001",
    "category": "prompt_injection",
    "prompt": "テストプロンプト"
  }'
```

## 次のステップ

- [評価の実行](running-evaluations.md)
- [結果の分析](analyzing-results.md)
