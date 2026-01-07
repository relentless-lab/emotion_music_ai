from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[EmailStr] = None
    code: str = Field(..., min_length=4, max_length=10)  # 验证码
    personal_profile: Optional[str] = None


class SendVerificationCodeRequest(BaseModel):
    email: EmailStr  # 接收验证码的邮箱



class LoginRequest(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    avatar: Optional[str] = None
    personal_profile: Optional[str] = None
    following_count: int
    followers_count: int
    plays_received: int = 0
    plays_this_month: int = 0
    liked_works_count: int = 0
    total_likes: int = 0


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: UserPublic


class ProfileStats(BaseModel):
    generations: int = 0
    emotionDetections: int = 0
    likesReceived: int = 0
    playsThisMonth: int = 0
    followers: int = 0
    following: int = 0
    likedSongs: int = 0
    works: int = 0


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    tags: list[str]
    status: str
    stats: ProfileStats


class ProfileUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    avatar: Optional[str] = None
    personal_profile: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)
