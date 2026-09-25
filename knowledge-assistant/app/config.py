from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file=".env",extra="ignore")
    database_url:str="sqlite+aiosqlite:///./knowledge.db"
    qdrant_url:str="http://localhost:6333"
    qdrant_hostport:str=""
    redis_url:str="redis://localhost:6379/0"
    rag_mode:str="ollama"
    openrouter_api_key:str=""
    openrouter_model:str="openrouter/free"
    ollama_url:str="http://localhost:11434"
    ollama_hostport:str=""
    llm_model:str="llama3.2:1b"
    embed_model:str="nomic-embed-text"
    upload_dir:str="./data/uploads"
    max_upload_mb:int=20
    allow_public_uploads:bool=False
settings=Settings()

def normalize_database_url(url: str) -> str:
 if url.startswith("postgres://"):
  return url.replace("postgres://", "postgresql+asyncpg://", 1)
 if url.startswith("postgresql://"):
  return url.replace("postgresql://", "postgresql+asyncpg://", 1)
 return url

def qdrant_url() -> str:
 return f"http://{settings.qdrant_hostport}" if settings.qdrant_hostport else settings.qdrant_url

def ollama_url() -> str:
 return f"http://{settings.ollama_hostport}" if settings.ollama_hostport else settings.ollama_url
