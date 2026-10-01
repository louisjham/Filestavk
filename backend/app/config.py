import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROD_DB_URL = f"sqlite+aiosqlite:///{(DATA_DIR / 'filestavk.db').as_posix()}"
DEMO_DB_URL = f"sqlite+aiosqlite:///{(DATA_DIR / 'filestavk_demo.db').as_posix()}"

class Settings(BaseSettings):
    secret_key: str = "changeme-generate-with-openssl-rand"
    admin_username: str = "admin"
    admin_password: str = "changeme"
    database_url: str = PROD_DB_URL
    demo_mode: bool = False
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://localhost:8000/ingestion/gmail/callback"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def model_post_init(self, __context):
        if self.demo_mode or os.getenv("FILESTAVK_DEMO", "").lower() in ("1", "true", "yes"):
            self.demo_mode = True
            self.database_url = DEMO_DB_URL

settings = Settings()


