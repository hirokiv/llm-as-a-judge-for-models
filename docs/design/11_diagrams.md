# アーキテクチャ図・ER図 詳細

## 概要
本ドキュメントでは、システムの各種図を詳細に記載します。

## 1. システム全体のコンポーネント図

```mermaid
graph TB
    subgraph "Frontend / Client"
        UI[Web Dashboard]
        CLI[CLI Tool]
        SCRIPT[Automation Scripts]
    end

    subgraph "API Layer"
        LB[Load Balancer]
        API1[FastAPI Instance 1]
        API2[FastAPI Instance 2]
        API3[FastAPI Instance N...]
    end

    subgraph "Business Logic Layer"
        EVAL[Evaluation Service]
        TC[Test Case Service]
        IDEM[Idempotency Service]
        REPORT[Reporting Service]
    end

    subgraph "Data Access Layer"
        REPO_EVAL[Evaluation Repository]
        REPO_TC[Test Case Repository]
        YAML_MGR[YAML Manager]
    end

    subgraph "External Dependencies"
        subgraph "LLM Providers"
            OPENAI_API[OpenAI API]
            AZURE_API[Azure OpenAI API]
        end

        subgraph "Data Storage"
            PG[(PostgreSQL/Supabase)]
            DELTA[(Databricks Delta Lake)]
            S3[(S3/Object Storage)]
        end

        subgraph "MLOps"
            MLFLOW_SERVER[MLflow Tracking Server]
            MLFLOW_DB[(MLflow Backend DB)]
            MLFLOW_S3[(Artifact Storage)]
        end

        subgraph "Monitoring & Logging"
            PROMETHEUS[Prometheus]
            GRAFANA[Grafana]
            LOKI[Loki]
            SENTRY[Sentry]
        end
    end

    UI --> LB
    CLI --> LB
    SCRIPT --> LB

    LB --> API1
    LB --> API2
    LB --> API3

    API1 --> EVAL
    API1 --> TC
    API1 --> IDEM

    API2 --> EVAL
    API2 --> TC
    API2 --> IDEM

    API3 --> EVAL
    API3 --> TC
    API3 --> IDEM

    EVAL --> REPO_EVAL
    EVAL --> OPENAI_API
    EVAL --> AZURE_API
    EVAL --> MLFLOW_SERVER

    TC --> REPO_TC
    TC --> YAML_MGR

    IDEM --> EVAL
    IDEM --> REPO_EVAL

    REPO_EVAL --> PG
    REPO_EVAL --> DELTA

    REPO_TC --> YAML_MGR
    YAML_MGR --> S3

    MLFLOW_SERVER --> MLFLOW_DB
    MLFLOW_SERVER --> MLFLOW_S3

    API1 --> PROMETHEUS
    API2 --> PROMETHEUS
    API3 --> PROMETHEUS

    PROMETHEUS --> GRAFANA

    API1 --> SENTRY
    API2 --> SENTRY
    API3 --> SENTRY

    style EVAL fill:#fff9c4
    style MLFLOW_SERVER fill:#e8f5e9
    style PG fill:#fce4ec
    style OPENAI_API fill:#e1f5ff
```

## 2. 評価処理の詳細シーケンス図

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI
    participant Auth as Auth Middleware
    participant RateLimit as Rate Limiter
    participant EvalSvc as Evaluator Service
    participant LLMFactory as LLM Factory
    participant JudgeLLM as Judge LLM (OpenAI)
    participant MLflow as MLflow Server
    participant Repo as Repository
    participant DB as Database

    Client->>API: POST /api/v1/evaluate
    Note over Client,API: Authorization: Bearer token<br/>{test_case_id, system_output}

    API->>Auth: verify_token(token)
    Auth->>Auth: JWT検証
    Auth-->>API: user_info

    API->>RateLimit: check_rate_limit(user)
    RateLimit-->>API: OK (or 429 Too Many Requests)

    API->>EvalSvc: evaluate_test_case(test_case, system_output)

    EvalSvc->>EvalSvc: load_test_case(test_case_id)
    Note over EvalSvc: YAMLファイルから読み込み

    EvalSvc->>MLflow: start_run(run_name)
    MLflow-->>EvalSvc: run_id

    EvalSvc->>MLflow: log_params({vectors, model_config})

    EvalSvc->>LLMFactory: get_judge_llm()
    LLMFactory-->>EvalSvc: llm_instance

    EvalSvc->>EvalSvc: build_prompt(test_case, system_output)
    Note over EvalSvc: Judge用プロンプトテンプレート適用

    EvalSvc->>JudgeLLM: invoke(prompt, config)
    Note over EvalSvc,JudgeLLM: temperature=0, seed=42

    JudgeLLM-->>EvalSvc: raw_response

    EvalSvc->>EvalSvc: parse_json(raw_response)
    Note over EvalSvc: Pydantic JudgeResultに変換

    alt JSON Parse成功
        EvalSvc->>MLflow: log_metrics({risk_score, is_safe})
        EvalSvc->>MLflow: log_artifact(reasoning.txt)
        EvalSvc->>MLflow: log_artifact(recommendation.txt)
        EvalSvc->>MLflow: set_tags({exploited_vectors, env})

        EvalSvc->>Repo: save_result(run_id, evaluation)
        Repo->>DB: INSERT INTO evaluation_results
        DB-->>Repo: success
        Repo-->>EvalSvc: success

        EvalSvc-->>API: {evaluation, mlflow_run_id}
        API-->>Client: 200 OK<br/>{status: "success", data: {...}}
    else JSON Parse失敗
        EvalSvc->>MLflow: log_param("error", "JSON parse failed")
        EvalSvc->>MLflow: set_tag("status", "failed")
        EvalSvc-->>API: LLMError
        API-->>Client: 422 Unprocessable Entity
    end
```

## 3. データベースER図（詳細版）

```mermaid
erDiagram
    TEST_CASES ||--o{ EVALUATION_RESULTS : evaluates
    TEST_CASES {
        varchar id PK "TEST-LT-001"
        varchar name "テストケース名"
        text description
        boolean private_data_access
        boolean untrusted_content_exposure
        boolean external_communication
        text input_text "攻撃プロンプト"
        text expected_safe_behavior
        timestamp created_at
        timestamp updated_at
    }

    EVALUATION_RESULTS ||--|| MLFLOW_RUNS : logs_to
    EVALUATION_RESULTS ||--o{ IDEMPOTENCY_CHECKS : validated_by
    EVALUATION_RESULTS {
        uuid id PK
        varchar mlflow_run_id UK
        varchar test_case_id FK
        text system_output "対象システムの出力"
        boolean is_safe
        integer risk_score "1-5"
        varchar_array exploited_vectors
        text reasoning
        text recommendation
        timestamp created_at
        timestamp updated_at
    }

    IDEMPOTENCY_CHECKS {
        uuid id PK
        varchar input_hash UK "SHA-256"
        varchar test_case_id FK
        boolean is_idempotent
        float variance_score "0.0-1.0"
        jsonb executions "実行詳細の配列"
        text message
        timestamp created_at
    }

    MLFLOW_RUNS {
        varchar run_id PK
        varchar experiment_id FK
        varchar run_name
        jsonb params
        jsonb metrics
        jsonb tags
        varchar artifact_uri
        varchar status "RUNNING/FINISHED/FAILED"
        timestamp start_time
        timestamp end_time
    }

    MLFLOW_EXPERIMENTS {
        varchar experiment_id PK
        varchar experiment_name UK
        varchar artifact_location
        varchar lifecycle_stage
        timestamp creation_time
        timestamp last_update_time
    }

    MLFLOW_EXPERIMENTS ||--o{ MLFLOW_RUNS : contains

    USERS ||--o{ EVALUATION_RESULTS : creates
    USERS {
        uuid id PK
        varchar email UK
        varchar role "admin/user/readonly"
        varchar password_hash
        timestamp created_at
        timestamp last_login_at
    }

    API_KEYS ||--|| USERS : belongs_to
    API_KEYS {
        uuid id PK
        varchar key_hash UK
        uuid user_id FK
        varchar name "APIキー名"
        boolean is_active
        timestamp expires_at
        timestamp created_at
    }
```

## 4. MLflow統合の詳細図

```mermaid
graph TB
    subgraph "Evaluation Process"
        START[評価開始] --> CREATE_RUN[MLflow Run作成]
        CREATE_RUN --> LOG_PARAMS[パラメータ記録]
        LOG_PARAMS --> INVOKE_LLM[Judge LLM呼び出し]
        INVOKE_LLM --> LOG_METRICS[メトリクス記録]
        LOG_METRICS --> LOG_ARTIFACTS[アーティファクト記録]
        LOG_ARTIFACTS --> END_RUN[Run終了]
    end

    subgraph "MLflow Tracking Server"
        TRACKING_API[Tracking API]
        BACKEND_STORE[(Backend Store<br/>PostgreSQL)]
        ARTIFACT_STORE[(Artifact Store<br/>S3/DBFS)]
    end

    subgraph "Recorded Data"
        subgraph "Parameters"
            PARAM_TC[test_case_id]
            PARAM_VEC[lethal_trifecta_vectors]
            PARAM_MODEL[model_config]
        end

        subgraph "Metrics"
            METRIC_RISK[risk_score]
            METRIC_SAFE[is_safe]
            METRIC_TIME[execution_time_ms]
        end

        subgraph "Artifacts"
            ART_REASON[reasoning.txt]
            ART_RECOMMEND[recommendation.txt]
            ART_FULL[full_evaluation.json]
            ART_INPUT[input_prompt.txt]
            ART_OUTPUT[system_output.txt]
        end

        subgraph "Tags"
            TAG_VECTORS[exploited_vectors]
            TAG_ENV[environment]
            TAG_VERSION[evaluator_version]
        end
    end

    CREATE_RUN --> TRACKING_API
    LOG_PARAMS --> TRACKING_API
    LOG_METRICS --> TRACKING_API
    LOG_ARTIFACTS --> TRACKING_API
    END_RUN --> TRACKING_API

    TRACKING_API --> BACKEND_STORE
    TRACKING_API --> ARTIFACT_STORE

    PARAM_TC --> BACKEND_STORE
    PARAM_VEC --> BACKEND_STORE
    PARAM_MODEL --> BACKEND_STORE

    METRIC_RISK --> BACKEND_STORE
    METRIC_SAFE --> BACKEND_STORE
    METRIC_TIME --> BACKEND_STORE

    ART_REASON --> ARTIFACT_STORE
    ART_RECOMMEND --> ARTIFACT_STORE
    ART_FULL --> ARTIFACT_STORE
    ART_INPUT --> ARTIFACT_STORE
    ART_OUTPUT --> ARTIFACT_STORE

    TAG_VECTORS --> BACKEND_STORE
    TAG_ENV --> BACKEND_STORE
    TAG_VERSION --> BACKEND_STORE

    style CREATE_RUN fill:#fff9c4
    style INVOKE_LLM fill:#f3e5f5
    style TRACKING_API fill:#e8f5e9
```

## 5. 冪等性チェックのフロー図

```mermaid
flowchart TD
    START[冪等性チェック開始] --> HASH[入力のハッシュ計算]
    HASH --> LOOP_START{実行回数 < N?}

    LOOP_START -->|Yes| EVAL[評価実行 i回目]
    EVAL --> STORE[結果を配列に保存]
    STORE --> INC[カウンタ++]
    INC --> LOOP_START

    LOOP_START -->|No| ANALYZE[結果を分析]

    ANALYZE --> CALC_VAR[一致度計算]
    CALC_VAR --> CHECK_RISK[risk_scoreの一致度]
    CALC_VAR --> CHECK_SAFE[is_safeの一致度]
    CALC_VAR --> CHECK_VEC[exploited_vectorsの一致度]

    CHECK_RISK --> WEIGHT[重み付け平均]
    CHECK_SAFE --> WEIGHT
    CHECK_VEC --> WEIGHT

    WEIGHT --> THRESHOLD{variance_score >= 0.9?}

    THRESHOLD -->|Yes| PASS[冪等性: TRUE]
    THRESHOLD -->|No| FAIL[冪等性: FALSE]

    PASS --> SAVE_DB[DBに保存]
    FAIL --> SAVE_DB

    SAVE_DB --> RETURN[結果を返す]
    RETURN --> END[終了]

    style START fill:#e1f5ff
    style PASS fill:#c8e6c9
    style FAIL fill:#ffcdd2
    style ANALYZE fill:#fff9c4
```

## 6. デプロイメント図（Kubernetes）

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Ingress"
            INGRESS[Nginx Ingress Controller]
        end

        subgraph "API Pods"
            API_POD1[FastAPI Pod 1<br/>CPU: 1core, RAM: 2GB]
            API_POD2[FastAPI Pod 2<br/>CPU: 1core, RAM: 2GB]
            API_POD3[FastAPI Pod 3<br/>CPU: 1core, RAM: 2GB]
        end

        subgraph "Worker Pods"
            WORKER1[Evaluation Worker 1]
            WORKER2[Evaluation Worker 2]
        end

        subgraph "Services"
            API_SVC[API Service<br/>ClusterIP]
            MLFLOW_SVC[MLflow Service<br/>ClusterIP]
        end

        subgraph "Persistent Volumes"
            PV_MLFLOW[MLflow PV<br/>100GB]
            PV_LOGS[Logs PV<br/>50GB]
        end

        subgraph "Config & Secrets"
            CONFIGMAP[ConfigMap<br/>App Config]
            SECRET[Secret<br/>API Keys, DB Credentials]
        end

        subgraph "Monitoring"
            PROM_POD[Prometheus Pod]
            GRAF_POD[Grafana Pod]
        end
    end

    subgraph "External Services"
        RDS[(RDS PostgreSQL)]
        S3[(S3 Bucket)]
        OPENAI_EXT[OpenAI API]
    end

    INGRESS --> API_SVC
    API_SVC --> API_POD1
    API_SVC --> API_POD2
    API_SVC --> API_POD3

    API_POD1 --> MLFLOW_SVC
    API_POD2 --> MLFLOW_SVC
    API_POD3 --> MLFLOW_SVC

    MLFLOW_SVC --> PV_MLFLOW

    API_POD1 --> RDS
    API_POD2 --> RDS
    API_POD3 --> RDS

    API_POD1 --> S3
    API_POD2 --> S3
    API_POD3 --> S3

    API_POD1 --> OPENAI_EXT
    API_POD2 --> OPENAI_EXT
    API_POD3 --> OPENAI_EXT

    CONFIGMAP --> API_POD1
    CONFIGMAP --> API_POD2
    CONFIGMAP --> API_POD3

    SECRET --> API_POD1
    SECRET --> API_POD2
    SECRET --> API_POD3

    PROM_POD --> API_POD1
    PROM_POD --> API_POD2
    PROM_POD --> API_POD3

    GRAF_POD --> PROM_POD

    style API_POD1 fill:#e1f5ff
    style API_POD2 fill:#e1f5ff
    style API_POD3 fill:#e1f5ff
    style MLFLOW_SVC fill:#e8f5e9
```

## 図の読み方・凡例

### Mermaid記法について
本仕様書で使用している図は、Mermaid記法で記述されています。GitHubやVS Code、Notion等で自動的にレンダリングされます。

### 色の意味
- **青系（#e1f5ff）**: APIレイヤー、クライアント
- **黄色系（#fff9c4）**: ビジネスロジック、サービス層
- **紫系（#f3e5f5）**: LLM関連
- **緑系（#e8f5e9）**: MLOps、モニタリング
- **ピンク系（#fce4ec）**: データベース、ストレージ
- **緑系（#c8e6c9）**: 成功状態
- **赤系（#ffcdd2）**: エラー状態

### 記号の意味
- `[]`: プロセス、サービス
- `()`: 開始/終了
- `{}`: 判断分岐
- `[()]`: データベース
- `-->`: データフロー
- `===>`: 強調されたフロー
