from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    remote_inference_url: str | None = None
    songgen_remote_url: str | None = None
    oss_enabled: bool | None = None

