-- Initial schema for LLM-as-a-Judge
-- Created: 2024-05-14

-- ==========================================
-- evaluation_results テーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mlflow_run_id VARCHAR(255) NOT NULL UNIQUE,
    test_case_id VARCHAR(50) NOT NULL,
    system_output TEXT NOT NULL,

    -- Judge Result
    is_safe BOOLEAN NOT NULL,
    risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 1 AND 5),
    exploited_vectors TEXT[], -- ARRAY型
    reasoning TEXT NOT NULL,
    recommendation TEXT NOT NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for evaluation_results
CREATE INDEX IF NOT EXISTS idx_evaluation_results_test_case_id ON evaluation_results(test_case_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_mlflow_run_id ON evaluation_results(mlflow_run_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_created_at ON evaluation_results(created_at DESC);

-- Comment on evaluation_results
COMMENT ON TABLE evaluation_results IS 'Judge LLMの評価結果を保存するテーブル';
COMMENT ON COLUMN evaluation_results.mlflow_run_id IS 'MLflow Run ID（一意キー）';
COMMENT ON COLUMN evaluation_results.risk_score IS 'リスクスコア（1: 安全、5: 致命的）';
COMMENT ON COLUMN evaluation_results.exploited_vectors IS 'Lethal Trifectaの悪用された要素';

-- ==========================================
-- idempotency_checks テーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS idempotency_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    input_hash VARCHAR(64) NOT NULL, -- SHA-256
    model_version_key VARCHAR(200) NOT NULL, -- "provider:model:version:temp:seed:prompt"

    -- Model metadata
    provider VARCHAR(50) NOT NULL, -- 例: "openai", "azure_openai"
    model_name VARCHAR(100) NOT NULL, -- 例: "gpt-4", "gpt-3.5-turbo"
    model_version VARCHAR(50), -- 例: "0613", "1106"
    temperature FLOAT NOT NULL, -- 例: 0.0
    seed INTEGER, -- 例: 42
    prompt_version VARCHAR(50) NOT NULL, -- 例: "v1.0", "v2.1"

    -- Test case reference
    test_case_id VARCHAR(50) NOT NULL,

    -- Check results
    is_idempotent BOOLEAN NOT NULL,
    variance_score FLOAT NOT NULL CHECK (variance_score BETWEEN 0 AND 1),
    executions JSONB NOT NULL,
    message TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint
    CONSTRAINT unique_idempotency_check UNIQUE (model_version_key, input_hash)
);

-- Indexes for idempotency_checks
CREATE INDEX IF NOT EXISTS idx_idempotency_checks_input_hash ON idempotency_checks(input_hash);
CREATE INDEX IF NOT EXISTS idx_idempotency_checks_model_version_key ON idempotency_checks(model_version_key);
CREATE INDEX IF NOT EXISTS idx_idempotency_checks_test_case_id ON idempotency_checks(test_case_id);
CREATE INDEX IF NOT EXISTS idx_idempotency_checks_created_at ON idempotency_checks(created_at DESC);

-- Comment on idempotency_checks
COMMENT ON TABLE idempotency_checks IS '冪等性チェック結果を保存するテーブル';
COMMENT ON COLUMN idempotency_checks.input_hash IS '入力のSHA-256ハッシュ値';
COMMENT ON COLUMN idempotency_checks.model_version_key IS 'モデルバージョンの一意キー';
COMMENT ON COLUMN idempotency_checks.variance_score IS '出力の一致度（0: 不一致、1: 完全一致）';
COMMENT ON COLUMN idempotency_checks.executions IS '各実行の詳細（JSON形式）';

-- ==========================================
-- Triggers for updated_at
-- ==========================================

-- updated_at自動更新用の関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- evaluation_results用トリガー
CREATE TRIGGER update_evaluation_results_updated_at
    BEFORE UPDATE ON evaluation_results
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Initial data (optional)
-- ==========================================

-- テーブルが正常に作成されたことを確認するためのコメント
COMMENT ON DATABASE postgres IS 'LLM-as-a-Judge Database';
