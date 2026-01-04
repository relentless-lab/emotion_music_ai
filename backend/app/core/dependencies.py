from typing import Generator

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User


def get_settings() -> Settings:
  return settings


def get_db() -> Generator[Session, None, None]:
  if SessionLocal is None:
    raise RuntimeError("Database is not configured. Set DATABASE_URL in environment variables.")
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
  if not authorization or not authorization.lower().startswith("bearer "):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先进行注册/登录")

  token = authorization.split(" ", 1)[1]
  try:
    payload = decode_access_token(token)
  except JWTError as exc:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌") from exc

  user_id = payload.get("sub")
  if not user_id:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")

  user = db.query(User).filter(User.id == int(user_id)).first()
  if not user:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已删除")

  return user


def get_current_user_optional(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User | None:
  """
  Optional auth dependency:
  - returns None when token is missing/invalid
  - returns User when token is valid
  It should NEVER raise, so anonymous搜索/详情接口可以安全复用。
  """
  if not authorization or not authorization.lower().startswith("bearer "):
    return None

  token = authorization.split(" ", 1)[1]
  try:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
      return None
    return db.query(User).filter(User.id == int(user_id)).first()
  except Exception:
    return None
