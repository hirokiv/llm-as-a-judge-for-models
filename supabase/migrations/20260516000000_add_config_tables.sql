-- Add configuration management tables for DB-based config
-- Created: 2026-05-16
-- Purpose: Migrate YAML configurations to database for dynamic updates

-- ==========================================
-- system_configs テーブル
-- ==========================================
-- Flattened hierarchical configuration
-- Example: config_key = "application.api.port", value = "8000"
CREATE TABLE IF NOT EXISTS system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(200) NOT NULL UNIQUE, -- Dot-separated key path
    value TEXT NOT NULL,                      -- Configuration value (can be JSON)
    value_type VARCHAR(50) NOT NULL,          -- string | integer | float | boolean | json

    -- Environment-specific configuration
    environment VARCHAR(50) DEFAULT 'default', -- default | development | staging | production

    -- Metadata
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure one active config per key per environment
    CONSTRAINT unique_config_key_env UNIQUE (config_key, environment)
);

-- Indexes for system_configs
CREATE INDEX IF NOT EXISTS idx_system_configs_config_key ON system_configs(config_key);
CREATE INDEX IF NOT EXISTS idx_system_configs_environment ON system_configs(environment);
CREATE INDEX IF NOT EXISTS idx_system_configs_is_active ON system_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_system_configs_created_at ON system_configs(created_at DESC);

-- Comments
COMMENT ON TABLE system_configs IS 'システム設定をフラット構造で管理（YAML system_defaults.yamlの代替）';
COMMENT ON COLUMN system_configs.config_key IS 'ドット区切りの設定キー（例: application.api.port）';
COMMENT ON COLUMN system_configs.value IS '設定値（文字列、数値、JSON等）';
COMMENT ON COLUMN system_configs.value_type IS '値の型（string, integer, float, boolean, json）';
COMMENT ON COLUMN system_configs.environment IS '環境別設定（default, development, staging, production）';

-- ==========================================
-- target_ai_systems テーブル
-- ==========================================
-- Proxy target AI system configurations
CREATE TABLE IF NOT EXISTS target_ai_systems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,        -- System name (e.g., "default", "production")
    description TEXT,

    -- Connection settings
    url TEXT NOT NULL,                        -- Target endpoint URL
    timeout_seconds INTEGER DEFAULT 30,       -- Request timeout

    -- Authentication headers (stored as JSONB)
    headers JSONB DEFAULT '{}'::jsonb,        -- {"Authorization": "Bearer xxx", "Content-Type": "..."}

    -- Request format configuration (stored as JSONB)
    request_config JSONB NOT NULL,            -- {method, body_template, etc.}

    -- Response parser configuration (stored as JSONB)
    response_config JSONB NOT NULL,           -- {output_path, error_path}

    -- Stub configuration for testing
    stub_enabled BOOLEAN DEFAULT false,
    stub_responses JSONB DEFAULT '{}'::jsonb, -- {default, prompt_injection, etc.}

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for target_ai_systems
CREATE INDEX IF NOT EXISTS idx_target_ai_systems_name ON target_ai_systems(name);
CREATE INDEX IF NOT EXISTS idx_target_ai_systems_is_active ON target_ai_systems(is_active);
CREATE INDEX IF NOT EXISTS idx_target_ai_systems_created_at ON target_ai_systems(created_at DESC);

-- Comments
COMMENT ON TABLE target_ai_systems IS 'プロキシターゲットAIシステム設定（YAML target_ai_system.yamlの代替）';
COMMENT ON COLUMN target_ai_systems.name IS 'システム名（例: default, production）';
COMMENT ON COLUMN target_ai_systems.url IS 'ターゲットエンドポイントURL';
COMMENT ON COLUMN target_ai_systems.headers IS '認証ヘッダー（JSONB）';
COMMENT ON COLUMN target_ai_systems.request_config IS 'リクエスト設定（method, body_template等）';
COMMENT ON COLUMN target_ai_systems.response_config IS 'レスポンスパーサー設定（output_path, error_path）';
COMMENT ON COLUMN target_ai_systems.stub_responses IS 'スタブ応答パターン（テスト用）';

-- ==========================================
-- evaluation_criteria テーブル
-- ==========================================
-- Rubric evaluation criteria configurations
CREATE TABLE IF NOT EXISTS evaluation_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,               -- Criteria name (e.g., "default", "strict")
    version VARCHAR(50) NOT NULL,             -- Version (e.g., "1.0")
    description TEXT,

    -- Hard Rules configuration (stored as JSONB)
    hard_rules_enabled BOOLEAN DEFAULT false,
    hard_rules JSONB DEFAULT '[]'::jsonb,     -- Array of hard rule definitions

    -- Soft Judge (Rubric) criteria (stored as JSONB)
    soft_judge_criteria JSONB DEFAULT '[]'::jsonb, -- Array of rubric criteria

    -- Risk score calculation rules (stored as JSONB)
    risk_score_config JSONB DEFAULT '{}'::jsonb,   -- {method, weights, thresholds, etc.}

    -- Recommendation templates (stored as JSONB)
    recommendation_templates JSONB DEFAULT '{}'::jsonb, -- Templates by risk_score

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure unique name-version combinations
    CONSTRAINT unique_criteria_name_version UNIQUE (name, version)
);

-- Indexes for evaluation_criteria
CREATE INDEX IF NOT EXISTS idx_evaluation_criteria_name ON evaluation_criteria(name);
CREATE INDEX IF NOT EXISTS idx_evaluation_criteria_version ON evaluation_criteria(version);
CREATE INDEX IF NOT EXISTS idx_evaluation_criteria_is_active ON evaluation_criteria(is_active);
CREATE INDEX IF NOT EXISTS idx_evaluation_criteria_created_at ON evaluation_criteria(created_at DESC);

-- Comments
COMMENT ON TABLE evaluation_criteria IS 'Rubric評価基準設定（YAML rubric_criteria.yamlの代替）';
COMMENT ON COLUMN evaluation_criteria.name IS '基準名（例: default, strict）';
COMMENT ON COLUMN evaluation_criteria.version IS 'バージョン（例: 1.0）';
COMMENT ON COLUMN evaluation_criteria.hard_rules IS 'Hard Rules定義（パターンマッチング）';
COMMENT ON COLUMN evaluation_criteria.soft_judge_criteria IS 'Soft Judge基準（Rubric評価項目）';
COMMENT ON COLUMN evaluation_criteria.risk_score_config IS 'リスクスコア計算ルール';
COMMENT ON COLUMN evaluation_criteria.recommendation_templates IS '推奨事項テンプレート';

-- ==========================================
-- Triggers for updated_at
-- ==========================================

-- system_configs用トリガー
CREATE TRIGGER update_system_configs_updated_at
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- target_ai_systems用トリガー
CREATE TRIGGER update_target_ai_systems_updated_at
    BEFORE UPDATE ON target_ai_systems
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- evaluation_criteria用トリガー
CREATE TRIGGER update_evaluation_criteria_updated_at
    BEFORE UPDATE ON evaluation_criteria
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- Initial seed data (minimal examples)
-- ==========================================

-- Example system config entry (will be populated by seed script)
INSERT INTO system_configs (config_key, value, value_type, environment, description)
VALUES
    ('application.name', 'LLM-as-a-Judge for Enterprise Systems', 'string', 'default', 'Application name'),
    ('application.version', '1.0.0', 'string', 'default', 'Application version')
ON CONFLICT (config_key, environment) DO NOTHING;

-- Example target AI system entry (will be populated by seed script)
INSERT INTO target_ai_systems (
    name,
    description,
    url,
    timeout_seconds,
    headers,
    request_config,
    response_config,
    stub_enabled
) VALUES (
    'default',
    'Default target AI system configuration',
    'http://localhost:8080/api/chat',
    30,
    '{"Content-Type": "application/json"}'::jsonb,
    '{"method": "POST", "body_template": "{\"messages\": [{\"role\": \"user\", \"content\": \"{user_input}\"}]}"}'::jsonb,
    '{"output_path": "$.choices[0].message.content", "error_path": "$.error.message"}'::jsonb,
    true
) ON CONFLICT (name) DO NOTHING;

-- Example evaluation criteria entry (will be populated by seed script)
INSERT INTO evaluation_criteria (
    name,
    version,
    description,
    hard_rules_enabled,
    soft_judge_criteria,
    risk_score_config
) VALUES (
    'default',
    '1.0',
    'Default evaluation criteria',
    false,
    '[]'::jsonb,
    '{"method": "weighted_average", "weights": {"private_data_access": 0.35, "untrusted_content_exposure": 0.30, "external_communication": 0.35}}'::jsonb
) ON CONFLICT (name, version) DO NOTHING;
