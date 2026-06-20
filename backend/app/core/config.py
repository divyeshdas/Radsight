from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "RadSight"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = False

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_workers: int = 4

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # MongoDB
    mongodb_uri: str
    mongodb_db_name: str = "radsight"
    mongodb_max_pool_size: int = 20
    mongodb_min_pool_size: int = 5

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_cache_ttl: int = 3600
    redis_embedding_ttl: int = 86400

    # AI Models
    biobert_model: str = "dmis-lab/biobert-base-cased-v1.2"
    clinicalbert_model: str = "emilyalsentzer/Bio_ClinicalBERT"
    sentence_bert_model: str = "pritamdeka/S-PubMedBert-MS-MARCO"
    scispacy_model: str = "en_core_sci_md"

    # FAISS
    faiss_index_path: str = "./faiss_index/radsight.index"
    faiss_dimension: int = 768
    faiss_nlist: int = 100
    faiss_nprobe: int = 10

    # OCR
    ocr_lang: str = "en"
    ocr_use_gpu: bool = False
    ocr_batch_size: int = 4

    # Analytics
    prophet_seasonality_mode: str = "additive"
    anomaly_contamination: float = 0.05
    trend_window_days: int = 30

    # File Upload
    max_upload_size_mb: int = 50
    upload_dir: str = "./uploads"
    allowed_extensions: str = "pdf,txt,png,jpg,jpeg,tiff"

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 20

    # CORS
    cors_origins: str = "http://localhost:3000,https://radsight.vercel.app"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [e.strip().lower() for e in self.allowed_extensions.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
