import os
import bcrypt
from datetime import datetime, timedelta, timezone
import jwt
from config import tenant_id_ctx
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader, APIKeyQuery
from sqlalchemy.orm import Session
from database import get_db
import models

from dotenv import load_dotenv
load_dotenv()

# Constants
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "super-secret-jwt-key-replace-in-prod":
    raise RuntimeError("CRITICAL SECURITY RISK: JWT_SECRET_KEY is missing or insecure in .env.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 Days for dashboard

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# Passwords
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# Tokens
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency for Dashboard (JWT)
def get_current_client(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        client_id: str = payload.get("sub")
        if client_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    client = db.query(models.Client).filter(models.Client.id == int(client_id)).first()
    if client is None or not client.is_active:
        raise credentials_exception

    tenant_id_ctx.set(f"Client_{client.id}")
    return client

# Dependency for Ingestion/Webhooks (API Key)
def get_client_by_api_key(
    api_key_h: str = Security(api_key_header),
    api_key_q: str = Security(api_key_query),
    db: Session = Depends(get_db)
):
    api_key = api_key_h or api_key_q
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header or api_key query parameter",
        )

    client = db.query(models.Client).filter(models.Client.api_key == api_key).first()
    if not client or not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API Key",
        )

    tenant_id_ctx.set(f"Client_{client.id}")
    return client