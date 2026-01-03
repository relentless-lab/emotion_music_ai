from functools import lru_cache
from pathlib import Path

import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "My FastAPI Service"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    ENVIRONMENT: str = "local"
    # NOTE:
    # - In pydantic-settings v2, complex env values (like list[str]) are decoded as JSON by default.
    # - For ease of deployment, we accept BOTH:
    #   1) Comma-separated string: "http://a.com,http://b.com"
    #   2) JSON array string: '["http://a.com","http://b.com"]'
    #
    # We store it as a plain string to avoid startup failures when operators use comma-separated values.
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    DATABASE_URL: str | None = None

    # JWT
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_SECONDS: int = 60 * 60 * 24  # 1 day

    # File storage
    MEDIA_ROOT: str = str(BASE_DIR / "uploads")

    # LLM / OpenAI-compatible provider
    # IMPORTANT: do NOT hardcode real API keys in code or git.
    # Configure via environment variables / deploy secrets.
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.siliconflow.cn/v1"  # 如用代理，填代理地址；不用可省略
    OPENAI_MODEL: str = "qwen/Qwen2.5-7B-Instruct"
    # 用于专辑封面生成的图片模型（Qwen-image）
    IMAGE_MODEL: str = "Qwen/Qwen2-XL-Image"

    # Static assets (for generated audio)
    STATIC_ROOT: str = "static"

    # OSS / Object storage
    OSS_ENABLED: bool = False
    OSS_ENDPOINT: str | None = None
    OSS_BUCKET: str | None = None
    OSS_ACCESS_KEY_ID: str | None = None
    OSS_ACCESS_KEY_SECRET: str | None = None
    OSS_PUBLIC_BASE_URL: str | None = None  # 公共读桶可配置，直接拼公开 URL
    OSS_SIGN_EXPIRES: int = 3600  # 私有桶签名有效期，公共桶可忽略

    # 可选：当生成音频已成功上传 OSS 后，是否删除本地 static/audio 缓存文件
    # 说明：仍会先落盘到 static/audio 再上传（需要本地文件进行 put_file）。
    # 默认开启：如果你明确希望保留本地文件（例如不用 OSS URL 播放），可在环境变量里设为 false。
    DELETE_LOCAL_AUDIO_AFTER_OSS_UPLOAD: bool = True

    # Music generation
    # 远程推理服务器地址 (如 http://1.2.3.4:8000)，如果不配置则使用本地模型
    REMOTE_INFERENCE_URL: str | None = None

    # SongGeneration(full-new) 4090 推理服务地址（如 http://x.x.x.x:8000）
    # 配置后：对话生成将优先走 SongGen（替换 MusicGen）。
    SONGGEN_REMOTE_URL: str | None = None
    # SongGeneration（with prompt audio）推理服务地址（建议跑在独立端口/独立模型，如 base-full:8001）
    # 仅用于“音乐仿写”功能，避免影响现有 base-new 生成链路。
    SONGGEN_PROMPT_AUDIO_REMOTE_URL: str | None = None
    SONGGEN_POLL_INTERVAL_SECONDS: float = 2.0
    SONGGEN_TOTAL_TIMEOUT_SECONDS: int = 15 * 60  # 主后端轮询总超时（秒）
    SONGGEN_REQUEST_TIMEOUT_SECONDS: int = 60     # 单次 HTTP 请求超时（秒）
    # Some music models mis-handle negative tags like "no drums" and produce the opposite.
    # Default: disable negative tags; rely on hard flags (--bgm/--vocal/--separate) for vocals control.
    SONGGEN_ALLOW_NEGATIVE_TAGS: bool = False

    # SongGen LLM enhancer (Qwen2.5) for descriptions + lyric writing
    SONGGEN_LLM_ENABLED: bool = False
    SONGGEN_LLM_TIMEOUT_SECONDS: int = 40
    SONGGEN_LLM_MAX_LYRIC_CHARS: int = 1200
    SONGGEN_LLM_MAX_PROMPT_CHARS: int = 800
    
    # 默认改为更省显存的模型，方便本地直接跑
    MUSICGEN_MODEL_ID: str = "facebook/musicgen-medium"
    MUSICGEN_MAX_SINGLE_CLIP_SEC: float = 28.0
    MUSICGEN_TOKENS_PER_SECOND: float = 50.0
    MUSICGEN_CHUNK_SEC: float = 25.0
    MUSICGEN_USE_CUDA_IF_AVAILABLE: bool = True
    MUSICGEN_PREFERRED_DEVICE: str | None = None

    # Local model weights
    MODEL_WEIGHTS_DIR: str = "model_weights"

    # Email configuration (QQ邮箱)
    QQ_EMAIL: str | None = None  # QQ邮箱地址（通过环境变量配置）
    QQ_EMAIL_AUTH_CODE: str | None = None  # QQ邮箱授权码（通过环境变量配置）

    # Always load backend/.env regardless of current working directory.
    model_config = SettingsConfigDict(
        env_file=[str(BASE_DIR / ".env"), ".env"],
        case_sensitive=False,
        # Deployment may add extra environment keys (e.g., HF_ENDPOINT/HF_HOME).
        # Do not fail startup on unknown keys from dotenv.
        extra="ignore",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    def split_origins(cls, v):  # noqa: N805
        # Keep backward compatibility if some runtime passes a list already.
        if isinstance(v, list):
            return ",".join(str(item).strip() for item in v if str(item).strip())
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        raw = (self.ALLOWED_ORIGINS or "").strip()
        if not raw:
            return []

        # JSON array
        if raw.startswith("["):
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return [str(item).strip() for item in data if str(item).strip()]
            except Exception:
                # Fall back to comma-split below
                pass

        # Comma-separated
        return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
