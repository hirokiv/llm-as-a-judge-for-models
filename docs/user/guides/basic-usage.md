# 基本的な使い方

!!! info "開発中"
    このページは現在作成中です。実装フェーズの進行に合わせて更新されます。

## 概要

LLM-as-a-Judge for Enterprise Systemsの基本的な使い方を説明します。

## サーバーの起動

```bash
# FastAPIサーバー起動
make run

# MLflowサーバー起動（別ターミナル）
make mlflow
```

## 基本的な評価の実行

実装完了後、以下のような手順で評価を実行できます：

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "TEST-LT-001",
    "system_output": "テスト出力"
  }'
```

## 次のステップ

- [テストケースの作成](creating-test-cases.md)
- [評価の実行](running-evaluations.md)
- [結果の分析](analyzing-results.md)
