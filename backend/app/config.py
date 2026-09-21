from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "mural_multispectral"
    storage_dir: Path = BASE_DIR / "storage"
    max_upload_mb: int = 200

    class Config:
        env_prefix = "MURAL_"


settings = Settings()

UPLOAD_DIR = settings.storage_dir / "uploads"
RESULT_DIR = settings.storage_dir / "results"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)
