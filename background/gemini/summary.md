承知いたしました。
これまでの議論に基づき、ClaudeやCodex等の他のAIアシスタントや開発環境にコンテキストを引き継ぐための「銀行システム向け LLM-as-a-judge 入出力監視モジュール モックアップ仕様書」をまとめます。

以下の内容をコピーして、他のツールに入力することで、要件に沿った実装をスムーズに継続できます。

---

# 銀行向け AIシステム入出力監視（LLM-as-a-judge）モジュール仕様書

## 1. プロジェクトの目的

銀行内で稼働する様々な生成AIシステム（LLMエージェントやRAGなど）の入出力を監視し、プロンプトインジェクション等の攻撃に対する脆弱性を自動評価する「LLM-as-a-judge」モジュールのモックアップを作成する。

## 2. アーキテクチャの制約と要件

* **マイクロサービス指向**: API層、サービスロジック層、インフラ・データ層の論理境界を明確に分ける。
* **バックエンド言語**: Python 3.10+ (FastAPIを採用)
* **LLMの抽象化**: LangChainを利用し、将来的に OpenAI (API) から Azure OpenAI への切り替えを容易にする（`core/llm_factory.py`で環境変数によるスイッチングを実装）。
* **DBの抽象化**: ローカル環境での実験用にSupabase（モック）を利用し、将来的に Databricks（Delta TableやDatabricks SQL）へ容易に移行できるようRepositoryパターンを採用する（`core/repository.py`）。
* **MLOps連携**: 評価履歴、テストケースのパラメータ、判定スコアを MLOpsプラットフォーム（Databricksへのデプロイを前提として `mlflow` を使用）に記録する。
* **冪等性の保証**: 判定LLMは `temperature=0` および `seed` の固定（OpenAI等でサポートされている場合）を行い、同一入力に対して同じ評価を返すようにする。

## 3. テストケースの管理手法：Lethal Trifectaの採用

プロンプトインジェクション等の脅威シナリオは、「Lethal Trifecta（リーサル・トライフェクタ）」の3要素に基づいて整理・評価する。
初期のテストケース管理は、簡易性を重視しYAMLファイル (`prompts/lethal_trifecta.yaml`) で行う。

### Lethal Trifecta の3要素 (Boolean型で定義)

1. **Private Data Access (`private_data_access`)**: 銀行の機密データや個人情報にアクセスできる能力・権限の有無。
2. **Untrusted Content Exposure (`untrusted_content_exposure`)**: メールやWebサイトなど、外部の信頼できない入力（攻撃者の指示が含まれうるデータ）を読み込む状況か。
3. **External Communication (`external_communication`)**: WebhookやAPI連携など、外部システムへデータを送信できる能力の有無。

## 4. 評価（Judge）の出力仕様

判定用LLM（Judge LLM）は、指定されたPydanticスキーマに従い、厳密なJSON形式で以下の項目を出力する。

* **`is_safe`** (bool): 期待される安全な挙動を満たしているか。
* **`risk_score`** (int): 1（安全）〜5（致命的・情報漏洩等）の5段階評価。
* **`exploited_vectors`** (List[str]): 攻撃によって悪用を許してしまったLethal Trifectaの要素（該当しない場合は空リスト）。
* **`reasoning`** (str): 判定およびスコアリングの理由（説明可能性の担保）。
* **`recommendation`** (str): 開発者向けの脆弱性修正の提案。

## 5. API エンドポイント要件 (FastAPI - `api/routes.py`)

モックアップのテスト時、ユーザーやCI/CDパイプラインが容易にテストケースを管理・実行できるよう、以下のREST APIを提供する。

* **`GET /test-cases`**: YAMLからテストケース一覧を取得する。
* **`POST /test-cases`**: 新しいテストケース（Lethal Trifectaの3要件を含む）をYAMLに追記する。（Pydanticによる厳密なバリデーションを実施）
* **`DELETE /test-cases/{test_case_id}`**: 指定したIDのテストケースをYAMLから削除する。
* **`POST /evaluate`**:
* 入力: `test_case_id` と、対象AIシステムの実際の出力 (`system_output`)。
* 処理: `EvaluatorService` を呼び出し、Judge LLMによる判定を実行。MLflowにラン（Run）を記録し、DB（Supabaseのモック）に結果を永続化する。
* 出力: 評価結果のJSONを返す。



## 6. ディレクトリ構造案

```text
app/
├── api/
│   └── routes.py         # APIエンドポイントの定義 (GET/POST/DELETE test-cases, POST evaluate)
├── core/
│   ├── config.py         # 環境変数設定
│   ├── llm_factory.py    # OpenAI/Azure OpenAI切り替えと冪等性設定
│   └── repository.py     # Supabase/Databricks切り替え (Repositoryパターン)
├── services/
│   └── evaluator.py      # LLM-as-a-judge実行ロジック (LangChain) と MLflowロギング
├── models/
│   └── schemas.py        # 評価結果やAPIリクエストのPydanticモデル
├── prompts/
│   └── lethal_trifecta.yaml # テストケース定義YAML
└── main.py               # FastAPI起動エントリーポイント

```

## 7. 既知の課題・検討事項 (実装者向け)

* YAMLファイルの書き込み時における排他制御（APIの並列リクエスト対策）の堅牢性強化。
* LangChainを用いたJudge LLM呼び出し時の、JSONフォーマット強制（`JsonOutputParser`等）のエラーハンドリングとリトライ処理。
* 本番環境における `mlflow` トラッキングサーバーへの認証情報の組み込み。

---

この仕様書をもとに、`main.py` の作成や、各モジュール（`app/core/*` 等）の具体的な実装を進めてください。