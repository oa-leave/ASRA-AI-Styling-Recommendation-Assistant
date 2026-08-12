import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _load_env_file() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


class Settings:
    def __init__(self) -> None:
        self.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./asra.db")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
        self.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.login_lockout_minutes = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
        self.vision_enabled = os.getenv("VISION_ENABLED", "false").lower() in {
            "1",
            "true",
            "yes",
        }
        self.vision_base_url = os.getenv(
            "VISION_BASE_URL",
            "http://127.0.0.1:11434/v1",
        )
        self.vision_model = os.getenv("VISION_MODEL", "llava")
        self.vision_api_key = os.getenv("VISION_API_KEY", "ollama")
        self.vision_timeout = int(os.getenv("VISION_TIMEOUT", "30"))
        self.vision_max_image_size = int(os.getenv("VISION_MAX_IMAGE_SIZE", "1024"))
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "").split(",")
            if origin.strip()
        ]


settings = Settings()
