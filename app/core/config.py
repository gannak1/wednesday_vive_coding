from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Global Issue Map"
    app_env: str = "local"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "global_issue_map"
    newsapi_api_key: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    papago_api_key_id: str | None = None
    papago_api_key: str | None = None
    papago_client_id: str | None = None
    papago_client_secret: str | None = None
    papago_base_url: str = "https://papago.apigw.ntruss.com"
    papago_source_language: str = "en"
    papago_target_language: str = "ko"
    session_cookie_name: str = "gid_session"
    session_cookie_max_age: int = 2_592_000
    scheduler_timezone: str = "Asia/Seoul"
    news_collection_name: str = "news"
    saved_collection_name: str = "saved_articles"
    home_headline_limit: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def session_cookie_secure(self) -> bool:
        return self.app_env == "prod"

    @property
    def papago_header_key_id(self) -> str | None:
        return self.papago_api_key_id or self.papago_client_id

    @property
    def papago_header_key(self) -> str | None:
        return self.papago_api_key or self.papago_client_secret

    @property
    def papago_configured(self) -> bool:
        return bool(self.papago_header_key_id and self.papago_header_key)


def get_settings() -> Settings:
    return Settings()
