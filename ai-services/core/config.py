from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    debug: bool = False

    biobert_model: str = "d4data/biomedical-ner-all"
    clinicalbert_model: str = "emilyalsentzer/Bio_ClinicalBERT"
    sentence_bert_model: str = "pritamdeka/S-PubMedBert-MS-MARCO"
    scispacy_model: str = "en_core_sci_md"

    device: str = "cpu"
    use_quantization: bool = True
    max_seq_length: int = 512
    batch_size: int = 8
    nlp_inference_timeout: int = 120

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_embedding_ttl: int = 86400

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "radsight"

    faiss_index_path: str = "./faiss_index/radsight.index"
    faiss_dimension: int = 768

    use_onnx: bool = True
    onnx_cache_dir: str = "./onnx_models"
    l1_cache_maxsize: int = 512
    l1_cache_ttl: int = 300

    ocr_lang: str = "en"
    ocr_use_gpu: bool = False

    backend_url: str = "http://backend:8000"


@lru_cache
def get_ai_settings() -> AISettings:
    return AISettings()
