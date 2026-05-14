# 認証・認可仕様

## 概要
本システムは、JWT（JSON Web Token）ベースのBearer Token認証を採用する。すべてのAPIエンドポイント（ヘルスチェックを除く）は認証が必要。

## 認証フロー

### 1. トークン取得（未実装 - 将来拡張）
現在のモックアップでは、事前に生成されたAPIキーを使用する。将来的には、以下のエンドポイントを実装予定。

```http
POST /api/v1/auth/token
Content-Type: application/json

{
    "username": "user@example.com",
    "password": "secure_password"
}
```

### 2. トークン使用
取得したトークンをHTTPヘッダーに含めてリクエストを送信する。

```http
GET /api/v1/test-cases
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## JWT トークン仕様

### トークン構造
```
header.payload.signature
```

### ペイロード例
```json
{
    "sub": "user_id_12345",
    "email": "user@example.com",
    "role": "admin",
    "exp": 1735689600,
    "iat": 1735603200
}
```

### クレーム定義
| クレーム | 型 | 説明 |
|---------|-----|------|
| sub | string | ユーザーID（サブジェクト） |
| email | string | ユーザーのメールアドレス |
| role | string | ユーザーのロール（admin, user, readonly） |
| exp | integer | トークンの有効期限（UNIXタイムスタンプ） |
| iat | integer | トークンの発行時刻（UNIXタイムスタンプ） |

### トークン有効期限
- アクセストークン: 1時間
- リフレッシュトークン（将来実装）: 7日間

## 認可（ロールベースアクセス制御）

### ロール定義

#### 1. admin
すべての操作が可能。

- テストケースの作成・更新・削除
- 評価の実行
- 評価履歴の閲覧
- 冪等性チェックの実行

#### 2. user
通常の操作が可能。

- テストケースの閲覧
- 評価の実行
- 評価履歴の閲覧（自分が実行したもののみ）
- 冪等性チェックの実行

#### 3. readonly
閲覧のみ可能。

- テストケースの閲覧
- 評価履歴の閲覧

### エンドポイント別のアクセス権限

| エンドポイント | admin | user | readonly |
|--------------|-------|------|----------|
| **テストケース管理** |
| GET /test-cases | ✓ | ✓ | ✓ |
| GET /test-cases/{id} | ✓ | ✓ | ✓ |
| POST /test-cases | ✓ | - | - |
| PUT /test-cases/{id} | ✓ | - | - |
| DELETE /test-cases/{id} | ✓ | - | - |
| **評価実行** |
| POST /evaluate | ✓ | ✓ | - |
| POST /idempotency-check | ✓ | ✓ | - |
| GET /evaluations | ✓ | ✓ (自分のみ) | ✓ |
| **Judge LLM設定管理** |
| GET /judge-llm-configs | ✓ | ✓ | ✓ |
| GET /judge-llm-configs/{id} | ✓ | ✓ | ✓ |
| POST /judge-llm-configs | ✓ | - | - |
| PUT /judge-llm-configs/{id} | ✓ | - | - |
| DELETE /judge-llm-configs/{id} | ✓ | - | - |
| POST /judge-llm-configs/{id}/verify-idempotency | ✓ | ✓ | - |
| POST /judge-llm-configs/{id}/set-default | ✓ | - | - |
| **プロンプトバージョン管理** |
| GET /prompt-versions | ✓ | ✓ | ✓ |
| POST /prompt-versions | ✓ | - | - |
| PUT /prompt-versions/{id}/activate | ✓ | - | - |

## 実装詳細

### 1. 設定（`app/core/config.py`）

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # JWT設定
    SECRET_KEY: str  # 環境変数から読み込み
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # API Key（モックアップ用）
    API_KEYS: List[str] = []  # カンマ区切りの環境変数から読み込み

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 2. セキュリティユーティリティ（`app/core/security.py`）

```python
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """アクセストークンを生成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict]:
    """トークンを検証しペイロードを返す"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None  # トークンの有効期限切れ
    except jwt.InvalidTokenError:
        return None  # 無効なトークン

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワードを検証"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """パスワードをハッシュ化"""
    return pwd_context.hash(password)

def verify_api_key(api_key: str) -> bool:
    """API Keyを検証（モックアップ用）"""
    return api_key in settings.API_KEYS
```

### 3. 依存性注入（`app/api/dependencies.py`）

```python
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict
from app.core.security import verify_token, verify_api_key

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    """
    トークンを検証し、現在のユーザー情報を返す
    """
    token = credentials.credentials

    # モックアップモード: API Keyとして検証
    if verify_api_key(token):
        return {
            "sub": "mock_user",
            "email": "mock@example.com",
            "role": "admin"
        }

    # JWT検証
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return payload

async def require_role(required_role: str):
    """
    特定のロールを要求する依存性注入ファクトリー
    """
    async def role_checker(
        current_user: Dict = Depends(get_current_user)
    ) -> Dict:
        user_role = current_user.get("role", "readonly")

        # ロールの階層: admin > user > readonly
        role_hierarchy = {
            "admin": 3,
            "user": 2,
            "readonly": 1
        }

        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 99):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )

        return current_user

    return role_checker
```

### 4. エンドポイントでの使用例（`app/api/routes.py`）

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from app.api.dependencies import get_current_user, require_role
from app.models.schemas import TestCaseScenario

router = APIRouter()

@router.get("/test-cases")
async def list_test_cases(
    current_user: Dict = Depends(get_current_user)
):
    """
    テストケース一覧取得（すべてのロールで可能）
    """
    # 実装...
    pass

@router.post("/test-cases")
async def create_test_case(
    scenario: TestCaseScenario,
    current_user: Dict = Depends(require_role("admin"))
):
    """
    テストケース作成（adminロールのみ）
    """
    # 実装...
    pass

@router.post("/evaluate")
async def run_evaluation(
    request: EvaluationRequest,
    current_user: Dict = Depends(require_role("user"))
):
    """
    評価実行（userロール以上）
    """
    # 実装...
    pass
```

## 環境変数設定

### `.env.example`
```bash
# JWT設定
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# モックアップ用API Key（カンマ区切り）
API_KEYS=test_key_1,test_key_2,test_key_3

# 本番環境では削除し、JWT認証のみを使用
```

### 本番環境での注意事項

1. **SECRET_KEYの生成**
```bash
# 暗号学的に安全なランダム文字列を生成
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **環境変数の安全な管理**
- AWS Secrets Manager
- Azure Key Vault
- Databricks Secrets
などを使用してSECRET_KEYを管理する

3. **API Keyの廃止**
本番環境では、API_KEYSを使用せず、JWT認証のみを使用する

## セキュリティ考慮事項

### 1. トークン保存
- クライアント側でトークンを保存する際は、HttpOnly Cookieまたはメモリ上に保持
- LocalStorageは避ける（XSS攻撃のリスク）

### 2. HTTPS必須
- 本番環境では必ずHTTPSを使用
- トークンが平文で送信されるのを防ぐ

### 3. トークンの定期的なローテーション
- アクセストークンの有効期限を短く設定
- リフレッシュトークンによる更新機構を実装

### 4. レート制限
- 認証エンドポイントにレート制限を設定
- ブルートフォース攻撃を防ぐ

### 5. 監査ログ
- 認証試行（成功・失敗）をログに記録
- 不正アクセスの検出

## テスト用トークン生成スクリプト

```python
# scripts/generate_test_token.py
from datetime import timedelta
from app.core.security import create_access_token

def generate_test_tokens():
    """テスト用のトークンを生成"""

    # Admin user
    admin_token = create_access_token(
        data={
            "sub": "test_admin",
            "email": "admin@example.com",
            "role": "admin"
        },
        expires_delta=timedelta(days=30)
    )
    print(f"Admin Token:\n{admin_token}\n")

    # Normal user
    user_token = create_access_token(
        data={
            "sub": "test_user",
            "email": "user@example.com",
            "role": "user"
        },
        expires_delta=timedelta(days=30)
    )
    print(f"User Token:\n{user_token}\n")

    # Readonly user
    readonly_token = create_access_token(
        data={
            "sub": "test_readonly",
            "email": "readonly@example.com",
            "role": "readonly"
        },
        expires_delta=timedelta(days=30)
    )
    print(f"Readonly Token:\n{readonly_token}\n")

if __name__ == "__main__":
    generate_test_tokens()
```

## 今後の拡張

### 1. OAuth 2.0統合
- Azure AD
- Okta
- Auth0
などの外部IDプロバイダーとの統合

### 2. API Key管理UI
- Web UIからAPI Keyの発行・無効化

### 3. 多要素認証（MFA）
- TOTP（Time-based One-Time Password）

### 4. 監査ログダッシュボード
- 認証イベントの可視化
