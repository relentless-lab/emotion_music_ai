from fastapi import APIRouter

from app.schemas.ui import ClientConfig, ModelOption, UploadPolicy

router = APIRouter()


@router.get("/config", response_model=ClientConfig, summary="Frontend config hints")
async def get_client_config() -> ClientConfig:
    """Provide the frontend with selectable models, upload constraints, and feature flags."""
    return ClientConfig(
        generation_models=[
            ModelOption(name="musicgen-small", label="MusicGen Small", type="generation", notes="Demo option"),
            ModelOption(name="riffusion", label="Riffusion", type="generation", notes="Seed-to-seed transitions"),
        ],
        emotion_models=[
            ModelOption(name="emo-classifier-v1", label="Emotion Classifier v1", type="emotion"),
        ],
        upload_policy=UploadPolicy(
            max_size_mb=25,
            accepted_types=["audio/mpeg", "audio/wav", "audio/x-wav", "audio/flac"],
            max_duration_seconds=600,
        ),
        features=[
            "generation",
            "emotion_analysis",
            "history",
            "waveform_preview",
        ],
    )

