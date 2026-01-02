from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthCheckResponse

router = APIRouter()


@router.get("", response_model=HealthCheckResponse, summary="Health check")
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="ok",
        remote_inference_url=settings.REMOTE_INFERENCE_URL,
        songgen_remote_url=settings.SONGGEN_REMOTE_URL,
        oss_enabled=bool(settings.OSS_ENABLED),
    )

