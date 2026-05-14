# 評価の実行

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## 概要

作成したテストケースに対して評価を実行する方法を説明します。

## 単一評価の実行

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "TEST-LT-001",
    "system_output": "システムからの出力"
  }'
```

## バッチ評価の実行

```bash
curl -X POST http://localhost:8000/api/v1/evaluate/batch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "evaluations": [
      {
        "test_case_id": "TEST-LT-001",
        "system_output": "出力1"
      },
      {
        "test_case_id": "TEST-LT-002",
        "system_output": "出力2"
      }
    ]
  }'
```

## 評価結果の確認

評価結果は以下から確認できます：

- REST API: `GET /api/v1/evaluations/{id}`
- MLflow UI: http://localhost:5000

## 次のステップ

- [結果の分析](analyzing-results.md)
