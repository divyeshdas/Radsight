import torch
from typing import Optional, Any
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    AutoModelForSequenceClassification,
    pipeline,
)
from core.config import get_ai_settings
import structlog

logger = structlog.get_logger(__name__)
settings = get_ai_settings()


class ModelRegistry:
    """
    Singleton model loader. All transformer models are loaded once at startup
    and reused across requests to avoid repeated initialization overhead.
    ONNX INT8 sessions are preferred over PyTorch for CPU inference when available.
    """

    _instance: Optional["ModelRegistry"] = None

    def __new__(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._biobert_pipeline = None
        self._clinicalbert_tokenizer = None
        self._clinicalbert_model = None
        self._spacy_nlp = None
        self._sentence_model = None
        self._ort_clinicalbert = None
        self._ort_sentencebert = None
        self._ort_loaded = False
        self._initialized = True

    def load_onnx_sessions(self) -> None:
        if self._ort_loaded:
            return
        self._ort_loaded = True

        if not settings.use_onnx:
            return

        from optimization.onnx_inference import load_clinicalbert_ort, load_sentencebert_ort
        self._ort_clinicalbert = load_clinicalbert_ort(
            settings.onnx_cache_dir, settings.clinicalbert_model
        )
        self._ort_sentencebert = load_sentencebert_ort(
            settings.onnx_cache_dir, settings.sentence_bert_model
        )

    @property
    def ort_clinicalbert(self):
        return self._ort_clinicalbert

    @property
    def ort_sentencebert(self):
        return self._ort_sentencebert

    def load_biobert(self) -> Any:
        if self._biobert_pipeline is not None:
            return self._biobert_pipeline

        logger.info("Loading BioBERT NER model", model=settings.biobert_model)
        self._biobert_pipeline = pipeline(
            "ner",
            model=settings.biobert_model,
            tokenizer=settings.biobert_model,
            aggregation_strategy="simple",
            device=0 if settings.device == "cuda" and torch.cuda.is_available() else -1,
        )

        if settings.use_quantization and settings.device == "cpu":
            try:
                self._biobert_pipeline.model = torch.quantization.quantize_dynamic(
                    self._biobert_pipeline.model,
                    {torch.nn.Linear},
                    dtype=torch.qint8,
                )
                logger.info("BioBERT quantized to INT8")
            except Exception as e:
                logger.warning("Quantization failed, using fp32", error=str(e))

        return self._biobert_pipeline

    def load_clinicalbert(self) -> tuple:
        if self._clinicalbert_tokenizer is not None:
            return self._clinicalbert_tokenizer, self._clinicalbert_model

        logger.info("Loading ClinicalBERT", model=settings.clinicalbert_model)
        self._clinicalbert_tokenizer = AutoTokenizer.from_pretrained(settings.clinicalbert_model)
        self._clinicalbert_model = AutoModelForSequenceClassification.from_pretrained(
            settings.clinicalbert_model,
            num_labels=3,
            ignore_mismatched_sizes=True,
        )
        self._clinicalbert_model.eval()

        if settings.use_quantization and settings.device == "cpu":
            try:
                self._clinicalbert_model = torch.quantization.quantize_dynamic(
                    self._clinicalbert_model,
                    {torch.nn.Linear},
                    dtype=torch.qint8,
                )
                logger.info("ClinicalBERT quantized to INT8")
            except Exception as e:
                logger.warning("ClinicalBERT quantization failed", error=str(e))

        return self._clinicalbert_tokenizer, self._clinicalbert_model

    def load_spacy(self) -> Any:
        if self._spacy_nlp is not None:
            return self._spacy_nlp

        logger.info("Loading scispaCy model", model=settings.scispacy_model)
        import spacy
        try:
            self._spacy_nlp = spacy.load(settings.scispacy_model)
        except OSError:
            logger.warning("scispaCy model not found, using en_core_web_sm fallback")
            self._spacy_nlp = spacy.load("en_core_web_sm")
        return self._spacy_nlp

    def load_sentence_model(self) -> Any:
        if self._sentence_model is not None:
            return self._sentence_model

        logger.info("Loading Sentence-BERT", model=settings.sentence_bert_model)
        from sentence_transformers import SentenceTransformer
        self._sentence_model = SentenceTransformer(
            settings.sentence_bert_model,
            device=settings.device if torch.cuda.is_available() else "cpu",
        )
        return self._sentence_model


registry = ModelRegistry()
