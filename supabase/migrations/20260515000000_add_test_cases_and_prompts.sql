-- Add test_cases, prompt_versions, and judge_llm_configs tables
-- Created: 2026-05-15

-- ==========================================
-- test_cases テーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS test_cases (
    id VARCHAR(50) PRIMARY KEY, -- 例: TEST-LT-001
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,

    -- Lethal Trifecta Vectors
    private_data_access BOOLEAN NOT NULL DEFAULT false,
    untrusted_content_exposure BOOLEAN NOT NULL DEFAULT false,
    external_communication BOOLEAN NOT NULL DEFAULT false,

    -- Test content
    input_text TEXT NOT NULL,
    expected_safe_behavior TEXT NOT NULL,

    -- Risk level
    risk_level INTEGER NOT NULL CHECK (risk_level BETWEEN 1 AND 5),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for test_cases
CREATE INDEX IF NOT EXISTS idx_test_cases_name ON test_cases(name);
CREATE INDEX IF NOT EXISTS idx_test_cases_risk_level ON test_cases(risk_level);
CREATE INDEX IF NOT EXISTS idx_test_cases_created_at ON test_cases(created_at DESC);

-- Comments
COMMENT ON TABLE test_cases IS 'テストケース定義を保存するテーブル';
COMMENT ON COLUMN test_cases.id IS 'テストケースID（例: TEST-LT-001）';
COMMENT ON COLUMN test_cases.private_data_access IS 'Lethal Trifecta: 機密データアクセス';
COMMENT ON COLUMN test_cases.untrusted_content_exposure IS 'Lethal Trifecta: 非信頼コンテンツ曝露';
COMMENT ON COLUMN test_cases.external_communication IS 'Lethal Trifecta: 外部通信能力';
COMMENT ON COLUMN test_cases.risk_level IS '期待されるリスクレベル（1: 低、5: 高）';

-- ==========================================
-- prompt_versions テーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL, -- 例: "judge_evaluation_prompt"
    version VARCHAR(50) NOT NULL, -- 例: "1.0.0-0125"

    -- Prompt content
    template TEXT NOT NULL,
    description TEXT,

    -- Model configuration
    model_provider VARCHAR(50), -- 例: "openai", "anthropic"
    model_name VARCHAR(100), -- 例: "gpt-4", "claude-3-opus"
    model_version VARCHAR(50), -- 例: "0613", "20240229"
    temperature FLOAT,

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint
    CONSTRAINT unique_prompt_version UNIQUE (name, version)
);

-- Indexes for prompt_versions
CREATE INDEX IF NOT EXISTS idx_prompt_versions_name ON prompt_versions(name);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_version ON prompt_versions(version);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_is_active ON prompt_versions(is_active);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_created_at ON prompt_versions(created_at DESC);

-- Comments
COMMENT ON TABLE prompt_versions IS 'プロンプトバージョン管理テーブル（MLflow Prompt Registryと同期）';
COMMENT ON COLUMN prompt_versions.name IS 'プロンプト名';
COMMENT ON COLUMN prompt_versions.version IS 'バージョン番号（セマンティックバージョニング）';
COMMENT ON COLUMN prompt_versions.template IS 'プロンプトテンプレート本文';
COMMENT ON COLUMN prompt_versions.is_active IS '現在アクティブなバージョンかどうか';

-- ==========================================
-- judge_llm_configs テーブル
-- ==========================================
CREATE TABLE IF NOT EXISTS judge_llm_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE, -- 例: "default", "strict", "permissive"

    -- LLM configuration
    provider VARCHAR(50) NOT NULL, -- 例: "openai", "azure_openai", "anthropic"
    model_name VARCHAR(100) NOT NULL, -- 例: "gpt-4", "gpt-3.5-turbo"
    model_version VARCHAR(50), -- 例: "0613", "0125"
    temperature FLOAT NOT NULL DEFAULT 0.0,
    seed INTEGER, -- For reproducibility

    -- Prompt configuration
    prompt_name VARCHAR(100) NOT NULL, -- Reference to prompt_versions
    prompt_version VARCHAR(50) NOT NULL, -- Reference to prompt_versions

    -- Evaluation settings
    enable_idempotency_check BOOLEAN DEFAULT false,
    idempotency_runs INTEGER DEFAULT 3, -- Number of runs for idempotency check

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for judge_llm_configs
CREATE INDEX IF NOT EXISTS idx_judge_llm_configs_name ON judge_llm_configs(name);
CREATE INDEX IF NOT EXISTS idx_judge_llm_configs_provider ON judge_llm_configs(provider);
CREATE INDEX IF NOT EXISTS idx_judge_llm_configs_is_active ON judge_llm_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_judge_llm_configs_created_at ON judge_llm_configs(created_at DESC);

-- Comments
COMMENT ON TABLE judge_llm_configs IS 'Judge LLMの設定を保存するテーブル';
COMMENT ON COLUMN judge_llm_configs.name IS '設定名（例: default, strict, permissive）';
COMMENT ON COLUMN judge_llm_configs.provider IS 'LLMプロバイダー';
COMMENT ON COLUMN judge_llm_configs.temperature IS 'Temperature設定（冪等性のため0.0推奨）';
COMMENT ON COLUMN judge_llm_configs.enable_idempotency_check IS '冪等性チェックを有効にするか';
COMMENT ON COLUMN judge_llm_configs.idempotency_runs IS '冪等性チェックの実行回数';

-- ==========================================
-- Triggers for updated_at
-- ==========================================

-- test_cases用トリガー
CREATE TRIGGER update_test_cases_updated_at
    BEFORE UPDATE ON test_cases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- prompt_versions用トリガー
CREATE TRIGGER update_prompt_versions_updated_at
    BEFORE UPDATE ON prompt_versions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- judge_llm_configs用トリガー
CREATE TRIGGER update_judge_llm_configs_updated_at
    BEFORE UPDATE ON judge_llm_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Foreign key constraints (optional)
-- ==========================================

-- evaluation_resultsにtest_case_idの外部キーを追加（データ整合性保証）
-- ALTER TABLE evaluation_results
--     ADD CONSTRAINT fk_evaluation_results_test_case_id
--     FOREIGN KEY (test_case_id)
--     REFERENCES test_cases(id)
--     ON DELETE CASCADE;

-- Note: 外部キー制約はコメントアウトしています。
-- 理由: 既存のevaluation_resultsにデータが存在し、test_casesテーブルにまだ対応するレコードがないため。
-- データマイグレーション後に有効化することを推奨します。
