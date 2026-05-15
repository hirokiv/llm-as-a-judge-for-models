-- Add evaluation_type to test_cases table
-- Created: 2026-05-15

-- ==========================================
-- evaluation_type 列の追加
-- ==========================================

-- ENUMタイプを作成
CREATE TYPE evaluation_type_enum AS ENUM ('input', 'output');

-- test_casesテーブルにevaluation_type列を追加
ALTER TABLE test_cases
    ADD COLUMN evaluation_type evaluation_type_enum NOT NULL DEFAULT 'output';

-- インデックス追加（検索効率化）
CREATE INDEX IF NOT EXISTS idx_test_cases_evaluation_type ON test_cases(evaluation_type);

-- コメント追加
COMMENT ON COLUMN test_cases.evaluation_type IS '評価対象: input（入力プロンプト評価）/ output（AIシステム出力評価）';

-- 既存データはすべてoutput評価として設定（デフォルト値が適用される）

-- ==========================================
-- 確認用クエリ
-- ==========================================
-- SELECT evaluation_type, COUNT(*)
-- FROM test_cases
-- GROUP BY evaluation_type;
