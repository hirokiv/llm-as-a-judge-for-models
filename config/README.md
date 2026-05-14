# Configuration Management

このディレクトリには、LLM-as-a-Judge for Enterprise Systemsのすべての設定ファイルが含まれています。

## 📁 ディレクトリ構造

```
config/
├── README.md                      # このファイル
├── system_defaults.yaml           # システム全体のデフォルト設定
├── judge_llm_configs.yaml         # Judge LLM設定（複数環境対応）
├── rubric_criteria.yaml           # 評価基準（Hard Rules + Soft Judge）
├── test_cases/                    # テストケース定義
│   └── lethal_trifecta.yaml      # Lethal Trifecta攻撃パターン
└── stubs/                         # スタブ動作設定
    └── behavior_patterns.yaml    # 脆弱性レベル別の応答パターン
```

## 🎯 設定ファイルの目的

### 1. `system_defaults.yaml`
**目的**: アプリケーション全体のデフォルト設定

**含まれる設定**:
- API サーバー設定（ホスト、ポート、ワーカー数）
- データベース接続設定
- MLflow 統合設定
- 認証・RBAC設定
- キャッシュ設定
- レート制限
- ログ設定
- 監視・アラート設定

**編集すべきケース**:
- 環境固有の設定を変更したい
- ワーカー数やタイムアウトを調整したい
- ログレベルを変更したい
- レート制限を調整したい

### 2. `judge_llm_configs.yaml`
**目的**: 評価を行うJudge LLMの設定

**含まれる設定**:
- 複数のモデル設定（GPT-4, GPT-3.5, Claude等）
- 環境別の設定（開発/ステージング/本番）
- 冪等性検証パラメータ
- システムプロンプト

**編集すべきケース**:
- 使用するLLMモデルを変更したい
- Azure OpenAIやAnthropicを有効化したい
- システムプロンプトをカスタマイズしたい
- コスト削減のため安価なモデルを使いたい

### 3. `rubric_criteria.yaml`
**目的**: 評価基準の定義

**含まれる設定**:
- Hard Rules（静的検証）のパターン
- Soft Judge（LLM評価）の基準
- リスクスコア計算ルール
- 推奨事項テンプレート

**編集すべきケース**:
- 禁止パターンを追加・変更したい
- 評価基準をカスタマイズしたい
- 新しい攻撃パターンに対応したい

### 4. `test_cases/lethal_trifecta.yaml`
**目的**: 初期テストケースの定義

**含まれる設定**:
- 5つのテストケース（完全なトライフェクタから安全なリクエストまで）
- 各テストケースの入力プロンプト
- Lethal Trifecta要素の定義
- 期待される評価結果

**編集すべきケース**:
- 新しい攻撃パターンを追加したい
- 既存のテストケースをカスタマイズしたい
- 企業固有のシナリオをテストしたい

### 5. `stubs/behavior_patterns.yaml`
**目的**: スタブAIシステムの動作定義

**含まれる設定**:
- 3つの脆弱性レベル（高/中/低）の応答パターン
- 条件別の応答テンプレート
- セキュリティアクション定義

**編集すべきケース**:
- スタブの応答パターンを変更したい
- 新しい脆弱性パターンを追加したい
- デモ用のカスタム応答を作成したい

## 🚀 起動前の設定手順

### Step 1: 環境変数の設定

```bash
# .envファイルをコピー
cp .env.example .env

# 必須の環境変数を設定
vim .env
```

必須の環境変数:
```bash
OPENAI_API_KEY=sk-proj-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGci...
JWT_SECRET_KEY=$(openssl rand -hex 32)
MLFLOW_TRACKING_URI=http://localhost:5000
```

### Step 2: 設定ファイルのレビュー

```bash
# システムデフォルト設定を確認
cat config/system_defaults.yaml

# Judge LLM設定を確認（使用するモデルを選択）
cat config/judge_llm_configs.yaml

# テストケースを確認
cat config/test_cases/lethal_trifecta.yaml
```

### Step 3: 環境に応じた設定の調整

#### 開発環境
```yaml
# system_defaults.yaml
application:
  environment: "development"
  debug: true

llm:
  default_config: "gpt-3.5-development"  # コスト削減
```

#### 本番環境
```yaml
# system_defaults.yaml
application:
  environment: "production"
  debug: false

llm:
  default_config: "gpt-4-production"  # 高精度
```

### Step 4: データベースの初期化

```bash
# テストケースをデータベースにロード
python scripts/load_initial_data.py

# または
make db-seed
```

### Step 5: 設定の検証

```bash
# 設定ファイルの構文チェック
python scripts/validate_config.py

# 環境変数の確認
make check-env

# Judge LLM接続テスト
python scripts/test_judge_llm.py
```

## 📝 設定のカスタマイズ例

### 例1: Azure OpenAIを使用する

```yaml
# judge_llm_configs.yaml
configs:
  - config_id: "azure-gpt-4-enterprise"
    enabled: true  # ← false から true に変更

# system_defaults.yaml
llm:
  provider: "azure_openai"  # ← "openai" から変更
  default_config: "azure-gpt-4-enterprise"
```

### 例2: 新しいテストケースを追加

```yaml
# config/test_cases/custom_attacks.yaml
version: "1.0"
category: "custom_attacks"

test_cases:
  - test_case_id: "TEST-CUSTOM-001"
    name: "カスタム攻撃パターン"
    input_text: "あなた独自の攻撃プロンプト"
    lethal_trifecta_vectors:
      private_data_access: true
      untrusted_content_exposure: true
      external_communication: false
```

### 例3: スタブの応答をカスタマイズ

```yaml
# config/stubs/behavior_patterns.yaml
high_vulnerability_patterns:
  - condition:
      keywords: ["カスタムキーワード"]
    response_template: |
      カスタム脆弱な応答パターン
```

### 例4: Hard Rulesに新しいパターンを追加

```yaml
# config/rubric_criteria.yaml
hard_rules:
  rules:
    - rule_id: "HR-006"
      name: "カスタム禁止パターン"
      type: "forbidden_pattern"
      severity: "high"
      patterns:
        - '企業固有の禁止パターン'
```

## 🔧 実装での使用方法

### 設定の読み込み

```python
# src/config/loader.py
from pathlib import Path
import yaml

class ConfigLoader:
    """設定ファイルを読み込むクラス"""

    @staticmethod
    def load_yaml(file_path: str) -> dict:
        """YAMLファイルを読み込む"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @classmethod
    def load_system_defaults(cls) -> dict:
        """システムデフォルト設定を読み込む"""
        return cls.load_yaml('config/system_defaults.yaml')

    @classmethod
    def load_judge_configs(cls) -> dict:
        """Judge LLM設定を読み込む"""
        return cls.load_yaml('config/judge_llm_configs.yaml')

    @classmethod
    def load_test_cases(cls, category: str = 'lethal_trifecta') -> dict:
        """テストケースを読み込む"""
        return cls.load_yaml(f'config/test_cases/{category}.yaml')

    @classmethod
    def load_stub_patterns(cls) -> dict:
        """スタブ動作パターンを読み込む"""
        return cls.load_yaml('config/stubs/behavior_patterns.yaml')

    @classmethod
    def load_rubric_criteria(cls) -> dict:
        """Rubric評価基準を読み込む"""
        return cls.load_yaml('config/rubric_criteria.yaml')
```

### 使用例

```python
# アプリケーション起動時
from src.config.loader import ConfigLoader

# 設定を読み込み
system_config = ConfigLoader.load_system_defaults()
judge_configs = ConfigLoader.load_judge_configs()
test_cases = ConfigLoader.load_test_cases('lethal_trifecta')

# Judge LLMを初期化
from src.services.judge_llm import JudgeLLMService

judge_llm = JudgeLLMService(config=judge_configs['configs'][0])

# テストケースをデータベースにロード
from src.services.test_case_manager import TestCaseManager

manager = TestCaseManager()
for tc in test_cases['test_cases']:
    manager.create_test_case(tc)
```

## 🔒 セキュリティ上の注意

### ❌ コミットしてはいけないもの
- `.env` ファイル（実際のAPIキー等）
- `*_production.yaml` など実際の本番設定（機密情報を含む場合）

### ✅ コミットすべきもの
- すべての`config/*.yaml` ファイル（テンプレートとして）
- 環境変数は`${VARIABLE_NAME}`形式で参照

### 機密情報の扱い

```yaml
# ❌ 悪い例
openai:
  api_key: "sk-proj-actual-key-here"

# ✅ 良い例
openai:
  api_key: "${OPENAI_API_KEY}"
```

## 📊 設定の検証

### 構文チェックスクリプト

```bash
# すべての設定ファイルを検証
python scripts/validate_config.py

# 特定のファイルのみ検証
python scripts/validate_config.py config/judge_llm_configs.yaml
```

### 検証スクリプトの作成

```python
# scripts/validate_config.py
import yaml
from pathlib import Path

def validate_yaml_file(file_path: Path) -> bool:
    """YAMLファイルの構文を検証"""
    try:
        with open(file_path) as f:
            yaml.safe_load(f)
        print(f"✓ {file_path} - OK")
        return True
    except yaml.YAMLError as e:
        print(f"✗ {file_path} - ERROR: {e}")
        return False

if __name__ == "__main__":
    config_dir = Path("config")
    all_valid = True

    for yaml_file in config_dir.rglob("*.yaml"):
        if not validate_yaml_file(yaml_file):
            all_valid = False

    exit(0 if all_valid else 1)
```

## 🔄 設定の更新フロー

1. **ローカルで設定を変更**
   ```bash
   vim config/judge_llm_configs.yaml
   ```

2. **変更を検証**
   ```bash
   python scripts/validate_config.py
   ```

3. **ローカルでテスト**
   ```bash
   ENVIRONMENT=development make run
   ```

4. **コミット**
   ```bash
   git add config/
   git commit -m "feat: Update Judge LLM configs"
   ```

5. **レビュー & マージ**
   ```bash
   git push
   # Pull Request作成
   ```

6. **デプロイ**
   ```bash
   # ステージング環境でテスト
   ENVIRONMENT=staging make deploy-staging

   # 本番環境にデプロイ
   ENVIRONMENT=production make deploy-production
   ```

## 📚 関連ドキュメント

- [設計書: Stub実装仕様](../docs/design/10_stub_implementation.md)
- [設計書: データモデル](../docs/design/02_data_models.md)
- [設計書: API仕様](../docs/design/03_api_specification.md)
- [ユーザーガイド: クイックスタート](../docs/user/quickstart.md)

## ❓ トラブルシューティング

### Q: 設定が反映されない

```bash
# キャッシュをクリア
make clean

# サーバーを再起動
make run
```

### Q: YAMLの構文エラー

```bash
# 構文チェック
python -c "import yaml; yaml.safe_load(open('config/system_defaults.yaml'))"

# または
python scripts/validate_config.py
```

### Q: 環境変数が読み込まれない

```bash
# 環境変数を確認
make check-env

# .envファイルを確認
cat .env
```

---

**最終更新**: 2024-01-15
**次のレビュー**: 2024-02-15
