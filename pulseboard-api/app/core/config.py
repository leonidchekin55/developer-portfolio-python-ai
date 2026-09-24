from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file=".env", extra="ignore")
    app_env:str="local"
    secret_key:str="unsafe-demo-secret"
    webhook_secret:str="local-demo-webhook-secret"
    database_url:str="sqlite+aiosqlite:///./pulseboard.db"
    redis_url:str="redis://localhost:6379/0"
    celery_broker_url:str="redis://localhost:6379/1"
settings=Settings()
