from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
 model_config=SettingsConfigDict(env_file=".env",extra="ignore")
 database_url:str="sqlite+aiosqlite:///./knowledge.db"
 qdrant_url:str="http://localhost:6333"
 redis_url:str="redis://localhost:6379/0"
 ollama_url:str="http://localhost:11434"
 llm_model:str="llama3.2:1b"
 embed_model:str="nomic-embed-text"
 upload_dir:str="./data/uploads"
 max_upload_mb:int=20
settings=Settings()
