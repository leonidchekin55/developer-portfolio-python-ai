from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file=".env", extra="ignore")
    app_env:str="local"
    secret_key:str="unsafe-demo-secret"
    webhook_secret:str="local-demo-webhook-secret"
    demo_password:str=""
    database_url:str="sqlite+aiosqlite:///./pulseboard.db"
    redis_url:str="redis://localhost:6379/0"
    celery_broker_url:str="redis://localhost:6379/1"
    celery_eager:bool=False

    @model_validator(mode="after")
    def require_production_secrets(self):
        if self.app_env.lower() in {"production", "prod"}:
            if self.secret_key == "unsafe-demo-secret" or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be a unique random value of at least 32 characters in production")
            if self.webhook_secret == "local-demo-webhook-secret" or len(self.webhook_secret) < 32:
                raise ValueError("WEBHOOK_SECRET must be a unique random value of at least 32 characters in production")
        return self

settings=Settings()
