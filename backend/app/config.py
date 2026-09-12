from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    secret_key: str = "changeme-generate-with-openssl-rand"
    admin_username: str = "admin"
    admin_password: str = "changeme"
    database_url: str = "sqlite+aiosqlite:///./data/filestavk.db"
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://localhost:8000/ingestion/gmail/callback"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
