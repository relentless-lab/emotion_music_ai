from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # songgeneration 工作目录（必须包含 generate.sh / generate.py 等）
    SONGGEN_WORKDIR: str = "/home/featurize/work/songgeneration"

    # 任务输出根目录
    SONGGEN_JOBS_DIR: str = "/tmp/songgen_jobs"

    # 并发限制（单卡建议 1）
    SONGGEN_CONCURRENCY: int = 1

    # 单任务超时（秒），默认 15 分钟
    SONGGEN_TIMEOUT_SECONDS: int = 15 * 60

    # 默认输出格式（wav | flac）
    SONGGEN_DEFAULT_FORMAT: str = "wav"

    # 运行模型名（固定参数位置，不要改 generate.sh 参数结构）
    SONGGEN_MODEL_NAME: str = "songgeneration_base_new"

    # 可选：指定 python/conda venv 的 bin 目录（用于保证 generate.sh 命中正确环境）
    # 例如：/home/featurize/work/songgen_env/bin
    SONGGEN_ENV_BIN: str | None = None

    # 后处理：是否把输出裁剪到请求的 duration_sec（当模型输出更长时）
    SONGGEN_TRIM_TO_DURATION: bool = True

    # 后处理：是否在音频结尾做淡出（缓解“突然断掉”的听感）
    SONGGEN_FADE_OUT: bool = True
    SONGGEN_FADE_OUT_SECONDS: float = 4.0

    model_config = SettingsConfigDict(env_file=[".env"], case_sensitive=False)


settings = Settings()


