# 結果の分析

!!! info "開発中"
    このページは実装フェーズの進行に合わせて更新されます。

## 概要

評価結果を分析し、システムのセキュリティ状態を理解する方法を説明します。

## 評価結果の構造

```json
{
  "evaluation_id": "eval-123",
  "test_case_id": "TEST-LT-001",
  "is_safe": false,
  "risk_score": 4,
  "exploited_vectors": ["confidential_data_access"],
  "reasoning": "機密情報へのアクセスが検出されました",
  "recommendation": "アクセス制御の強化を推奨"
}
```

## MLflowでの分析

MLflow UIで以下を確認できます：

- 評価メトリクス（risk_score分布、is_safe率）
- パラメータ（使用モデル、temperature等）
- 実験間の比較
- トレンド分析

## レポート生成

実装予定：

- CSVエクスポート
- PDFレポート生成
- ダッシュボード可視化

## 次のステップ

- [API リファレンス](../api/overview.md)
- [トラブルシューティング](../operations/troubleshooting.md)
