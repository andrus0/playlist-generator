from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLG_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./playlist.db"
    static_dir: str = "static"
    # Comma-separated list of allowed origins for CORS (empty = same-origin only)
    cors_origins: str = ""
    # Public app: throttle per client IP
    rate_limit: str = "60/minute"
    # Import chart data on startup if the database is empty
    auto_import: bool = False
    billboard_url: str = (
        "https://raw.githubusercontent.com/mhollingshead/billboard-hot-100/main/all.json"
    )
    # Hard cap on playlist length
    max_count: int = 200


settings = Settings()
