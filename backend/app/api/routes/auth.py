from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.models.like_record import LikeRecord
from app.models.user import User
from app.models.work import Work, WorkStatus, WorkVisibility
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    SendVerificationCodeRequest,
    TokenResponse,
    UserPublic,
)
from app.services import email_service, verification_code_service
from app.services.url_resolver import resolve_cover_url
from app.services.oss_storage import OSSStorage, build_oss_key, encode_oss_path

router = APIRouter()


def _count_visible_liked_works(db: Session, *, user_id: int) -> int:
  """
  Count liked works that are still visible in the "liked works" list.

  NOTE:
  - `users.liked_works_count` is an accumulated counter.
  - Liked works list endpoint filters to published + public works.
  - When a liked work is later unpublished/private, the list shrinks but the counter doesn't,
    which makes Profile "喜欢" count inconsistent with the list modal.
  """
  return (
      db.query(LikeRecord)
      .join(Work, Work.id == LikeRecord.work_id)
      .filter(
          LikeRecord.user_id == user_id,
          Work.status == WorkStatus.published,
          Work.visibility == WorkVisibility.public,
      )
      .count()
  )


@router.post("/send-verification-code", summary="send verification code to email")
async def send_verification_code(
    payload: SendVerificationCodeRequest,
    db: Session = Depends(get_db)
):
    """Send verification code to the specified email address."""
    email = payload.email
    
    # 检查邮箱是否已被注册
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )
    
    # 生成验证码
    code = verification_code_service.generate_verification_code()
    
    # 存储验证码（10分钟有效期）
    verification_code_service.store_verification_code(email, code, expire_seconds=600)
    
    # 发送邮件
    success = email_service.send_verification_code_email(email, code)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证码发送失败，请稍后重试"
        )
    
    return {"message": "验证码已发送"}


@router.post("/register", response_model=TokenResponse, summary="register user")
async def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
  # 验证邮箱和验证码
  if not payload.email:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱不能为空")
  
  # 验证验证码
  if not verification_code_service.verify_code(payload.email, payload.code):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="验证码错误或已过期，请重新获取"
    )
  
  # 检查用户名是否已存在
  exists = db.query(User).filter(User.username == payload.username).first()
  if exists:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
  
  # 检查邮箱是否已被注册
  email_exists = db.query(User).filter(User.email == payload.email).first()
  if email_exists:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被注册")

  user = User(
      username=payload.username,
      email=payload.email,
      personal_profile=payload.personal_profile,
      password_hash=hash_password(payload.password),
  )
  db.add(user)
  db.commit()
  db.refresh(user)

  token = create_access_token(user.id)
  return TokenResponse(
      token=token,
      user=UserPublic(
          id=user.id,
          username=user.username,
          email=user.email,
          avatar=user.avatar,
          personal_profile=user.personal_profile,
          following_count=user.following_count,
          followers_count=user.followers_count,
          plays_received=user.plays_received,
          plays_this_month=user.plays_this_month,
          liked_works_count=user.liked_works_count,
          total_likes=user.total_likes,
      ),
  )


@router.post("/login", response_model=TokenResponse, summary="login user")
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
  user = db.query(User).filter(User.username == payload.username).first()
  if not user or not verify_password(payload.password, user.password_hash):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账户或密码错误")

  token = create_access_token(user.id)
  return TokenResponse(
      token=token,
      user=UserPublic(
          id=user.id,
          username=user.username,
          email=user.email,
          avatar=user.avatar,
          personal_profile=user.personal_profile,
          following_count=user.following_count,
          followers_count=user.followers_count,
          plays_received=user.plays_received,
          plays_this_month=user.plays_this_month,
          liked_works_count=user.liked_works_count,
          total_likes=user.total_likes,
      ),
  )


@router.get("/profile", response_model=ProfileResponse, summary="get current user profile")
async def profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
  liked_visible_count = _count_visible_liked_works(db, user_id=current_user.id)
  return ProfileResponse(
      id=current_user.id,
      name=current_user.username,
      email=current_user.email,
      bio=current_user.personal_profile,
      avatar=resolve_cover_url(current_user.avatar),
      tags=["verified", "music-creator"],
      status="active",
      stats={
          "generations": current_user.total_generations or 0,
          "emotionDetections": current_user.emotion_detection_count or 0,
          "likesReceived": current_user.total_likes,
          "playsThisMonth": current_user.plays_this_month,
          "followers": current_user.followers_count,
          "following": current_user.following_count,
          "likedSongs": liked_visible_count,
          "works": current_user.total_works,
      },
  )


@router.put("/profile", response_model=ProfileResponse, summary="update current user profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
  if payload.username and payload.username != current_user.username:
    username_exists = db.query(User).filter(User.username == payload.username).first()
    if username_exists:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    current_user.username = payload.username


  if payload.avatar is not None:
    current_user.avatar = payload.avatar

  if payload.personal_profile is not None:
    current_user.personal_profile = payload.personal_profile

  db.add(current_user)
  db.commit()
  db.refresh(current_user)

  liked_visible_count = _count_visible_liked_works(db, user_id=current_user.id)
  return ProfileResponse(
      id=current_user.id,
      name=current_user.username,
      email=current_user.email,
      bio=current_user.personal_profile,
      avatar=resolve_cover_url(current_user.avatar),
      tags=["verified", "music-creator"],
      status="active",
      stats={
          "generations": current_user.total_generations or 0,
          "emotionDetections": current_user.emotion_detection_count or 0,
          "likesReceived": current_user.total_likes,
          "playsThisMonth": current_user.plays_this_month,
          "followers": current_user.followers_count,
          "following": current_user.following_count,
          "likedSongs": liked_visible_count,
          "works": current_user.total_works,
      },
  )


@router.post("/upload-avatar", summary="Upload avatar image for current user")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
  if not file.content_type or not file.content_type.startswith("image/"):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传图片文件")

  suffix = Path(file.filename or "").suffix or ".png"
  content = await file.read()

  # 优先 OSS
  if settings.OSS_ENABLED:
    try:
      key = build_oss_key(
          category="avatar",
          source="upload",
          user_id=current_user.id,
          original_filename=file.filename,
          ext=suffix,
      )
      OSSStorage().put_bytes(key, content, content_type=file.content_type)
      avatar_path = encode_oss_path(key)
      avatar_url = OSSStorage().get_url(key)
      return {"avatar_url": avatar_url, "avatar_path": avatar_path}
    except Exception as exc:
      print(f"[upload_avatar] Upload to OSS failed, fallback local: {exc}")

  # 本地兜底
  avatars_dir = Path(settings.STATIC_ROOT) / "avatars"
  avatars_dir.mkdir(parents=True, exist_ok=True)
  filename = f"{uuid4()}{suffix}"
  dest = avatars_dir / filename
  dest.write_bytes(content)
  avatar_rel = f"/static/avatars/{filename}"
  return {"avatar_url": avatar_rel, "avatar_path": avatar_rel}


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT, summary="delete current user")
async def delete_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
  db.delete(current_user)
  db.commit()
  

@router.put("/account/password", summary="change current user password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
  # 校验当前密码
  if not verify_password(payload.current_password, current_user.password_hash):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误")

  # 新旧密码不能相同
  if payload.current_password == payload.new_password:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与原密码相同")

  # 保存哈希
  current_user.password_hash = hash_password(payload.new_password)
  db.add(current_user)
  db.commit()

  return {"message": "已修改成功"}
