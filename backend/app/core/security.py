from datetime import datetime, timedelta
from typing import Any, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 密码哈希方案：
# - 默认使用 pbkdf2_sha256，避免部分平台下 passlib+bcrypt 的 72 字节限制探测报错。
# - 保留 bcrypt 以兼容历史数据。
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    default="pbkdf2_sha256",
    deprecated="auto",
)


def hash_password(password: str) -> str:
  """将密码安全哈希后存储。"""
  return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
  """
  校验密码。
  - 优先使用 bcrypt 验证。
  - 若存量数据仍是明文（旧版本遗留），则退回到明文对比，避免老账号无法登录。
  """
  try:
    return pwd_context.verify(password, password_hash)
  except Exception:
    return password == password_hash


def create_access_token(subject: str | int) -> str:
  expire = datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRE_SECONDS)
  to_encode: Dict[str, Any] = {"sub": str(subject), "exp": expire}
  return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
  return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


JWTErrorDetail = JWTError
