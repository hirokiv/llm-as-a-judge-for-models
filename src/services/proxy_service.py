"""
Proxy Service for Target AI System Communication

ユーザーの生成AIシステムとの通信を管理するプロキシサービス
"""

import json
import os
from pathlib import Path
from string import Template
from typing import Any

import httpx
import yaml
from jsonpath_ng.ext import parse

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProxyServiceError(Exception):
    """Proxy Service のエラー"""

    pass


class TargetAISystemConfig:
    """ターゲットAIシステムの設定"""

    def __init__(self, config_path: str | Path | None = None):
        """設定ファイルを読み込む

        Args:
            config_path: 設定ファイルのパス（省略時はデフォルトパス）
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "target_ai_system.yaml"

        self.config_path = Path(config_path)
        self._load_config()

    def _load_config(self) -> None:
        """設定ファイルを読み込む"""
        if not self.config_path.exists():
            raise ProxyServiceError(f"設定ファイルが見つかりません: {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        target_config = config.get("target_ai_system", {})

        # URL
        self.url = target_config.get("url", "stub")

        # ヘッダー（環境変数を展開）
        headers = target_config.get("headers", {})
        self.headers = {k: self._expand_env_var(v) for k, v in headers.items()}

        # タイムアウト
        self.timeout = target_config.get("timeout", 30)

        # リクエストフォーマット
        request_format = target_config.get("request_format", {})
        self.request_body_template = request_format.get("body_template", "")
        self.request_method = request_format.get("method", "POST")

        # レスポンスパーサー
        response_parser = target_config.get("response_parser", {})
        self.output_path = response_parser.get("output_path", "$.choices[0].message.content")
        self.error_path = response_parser.get("error_path", "$.error.message")

        # スタブ設定
        stub_config = config.get("stub_config", {})
        self.stub_enabled = stub_config.get("enabled", True)
        self.stub_response_patterns = stub_config.get("response_patterns", {})

        logger.info(
            "Target AI system config loaded",
            url=self.url,
            method=self.request_method,
            stub_enabled=self.stub_enabled,
        )

    def _expand_env_var(self, value: str) -> str:
        """環境変数を展開する

        Args:
            value: 展開する文字列（例: "Bearer ${TARGET_AI_API_KEY}"）

        Returns:
            展開された文字列
        """
        if "${" in value:
            # ${VAR_NAME} を環境変数の値に置き換え
            import re

            pattern = r"\$\{([^}]+)\}"
            matches = re.findall(pattern, value)

            for var_name in matches:
                env_value = os.getenv(var_name, "")
                value = value.replace(f"${{{var_name}}}", env_value)

        return value


class ProxyService:
    """ターゲットAIシステムへのプロキシサービス"""

    def __init__(self, config: TargetAISystemConfig | None = None):
        """プロキシサービスを初期化

        Args:
            config: ターゲットAIシステムの設定（省略時はデフォルト設定）
        """
        self.config = config or TargetAISystemConfig()
        self.client = httpx.AsyncClient(timeout=self.config.timeout)

    async def send_to_target_ai(self, user_input: str) -> str:
        """ターゲットAIシステムにリクエストを送信

        Args:
            user_input: ユーザーからの入力プロンプト

        Returns:
            AIシステムからの出力

        Raises:
            ProxyServiceError: 通信エラー発生時
        """
        # スタブモード
        if self.config.url == "stub" and self.config.stub_enabled:
            return self._get_stub_response(user_input)

        try:
            # リクエストボディを構築
            request_body = self._build_request_body(user_input)

            logger.info(
                "Sending request to target AI system",
                url=self.config.url,
                method=self.config.request_method,
                input_length=len(user_input),
            )

            # HTTPリクエスト送信
            response = await self.client.request(
                method=self.config.request_method,
                url=self.config.url,
                headers=self.config.headers,
                json=request_body,
            )

            response.raise_for_status()

            # レスポンスをパース
            response_json = response.json()
            output = self._parse_response(response_json)

            logger.info(
                "Received response from target AI system",
                output_length=len(output),
            )

            return output

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error from target AI system",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise ProxyServiceError(
                f"ターゲットAIシステムからエラー応答: {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            logger.error("Request error to target AI system", error=str(e))
            raise ProxyServiceError(f"ターゲットAIシステムへのリクエストエラー: {str(e)}") from e

        except Exception as e:
            logger.error(
                "Unexpected error in proxy service", error=str(e), error_type=type(e).__name__
            )
            raise ProxyServiceError(f"プロキシサービスエラー: {str(e)}") from e

    def _build_request_body(self, user_input: str) -> dict[str, Any]:
        """リクエストボディを構築

        Args:
            user_input: ユーザー入力

        Returns:
            リクエストボディ（辞書形式）
        """
        # テンプレートに user_input を埋め込む
        template = Template(self.config.request_body_template)
        body_str = template.safe_substitute(user_input=user_input)

        # JSON文字列をパース
        try:
            return json.loads(body_str)
        except json.JSONDecodeError as e:
            raise ProxyServiceError(f"リクエストボディのJSON解析エラー: {str(e)}") from e

    def _parse_response(self, response_json: dict[str, Any]) -> str:
        """レスポンスをパースしてAI出力を抽出

        Args:
            response_json: レスポンスJSON

        Returns:
            AI出力テキスト

        Raises:
            ProxyServiceError: パースエラー発生時
        """
        # エラーチェック
        if self.config.error_path:
            error_expr = parse(self.config.error_path)
            error_matches = error_expr.find(response_json)
            if error_matches:
                error_message = error_matches[0].value
                raise ProxyServiceError(f"ターゲットAIシステムエラー: {error_message}")

        # 出力抽出
        output_expr = parse(self.config.output_path)
        output_matches = output_expr.find(response_json)

        if not output_matches:
            raise ProxyServiceError(
                f"レスポンスから出力を抽出できませんでした（JSONPath: {self.config.output_path}）"
            )

        return output_matches[0].value

    def _get_stub_response(self, user_input: str) -> str:
        """スタブレスポンスを返す（開発用）

        Args:
            user_input: ユーザー入力

        Returns:
            スタブレスポンス
        """
        # プロンプトインジェクション攻撃を検出
        if any(
            keyword in user_input.lower()
            for keyword in ["ignore", "システムプロンプト", "previous instructions", "admin"]
        ):
            pattern_name = "prompt_injection"
        else:
            pattern_name = "default"

        response = self.stub_response_patterns.get(
            pattern_name,
            "これはスタブAIシステムからの応答です。",
        )

        logger.info(
            "Returning stub response",
            pattern=pattern_name,
            output_length=len(response),
        )

        return response

    async def close(self) -> None:
        """クライアントをクローズ"""
        await self.client.aclose()


def get_proxy_service(config: TargetAISystemConfig | None = None) -> ProxyService:
    """ProxyServiceのファクトリ関数

    Args:
        config: ターゲットAIシステムの設定（省略時はデフォルト設定）

    Returns:
        ProxyService インスタンス
    """
    return ProxyService(config=config)
