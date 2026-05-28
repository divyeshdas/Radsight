"""
Export ClinicalBERT and Sentence-BERT backbone to ONNX and apply INT8
dynamic quantization. Run this script once before starting the service:

    python -m optimization.onnx_exporter

Output files (in settings.onnx_cache_dir):
  clinicalbert_fp32.onnx   — FP32 classification model
  clinicalbert_int8.onnx   — INT8 quantized (used at runtime)
  sentencebert_fp32.onnx   — FP32 sentence encoder backbone
  sentencebert_int8.onnx   — INT8 quantized (used at runtime)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
import torch
import torch.nn as nn
import structlog

logger = structlog.get_logger(__name__)


def _quantize(fp32_path: Path, int8_path: Path) -> None:
    from onnxruntime.quantization import quantize_dynamic, QuantType
    quantize_dynamic(str(fp32_path), str(int8_path), weight_type=QuantType.QInt8)
    logger.info("INT8 quantization done", src=str(fp32_path), dst=str(int8_path))


def export_clinicalbert(output_dir: Path) -> None:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    from core.config import get_ai_settings

    settings = get_ai_settings()
    fp32_path = output_dir / "clinicalbert_fp32.onnx"
    int8_path = output_dir / "clinicalbert_int8.onnx"

    if int8_path.exists():
        logger.info("ClinicalBERT INT8 already exported, skipping")
        return

    logger.info("Exporting ClinicalBERT to ONNX", model=settings.clinicalbert_model)
    tokenizer = AutoTokenizer.from_pretrained(settings.clinicalbert_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        settings.clinicalbert_model, num_labels=3, ignore_mismatched_sizes=True
    )
    model.eval()

    seq_len = 64
    dummy_ids   = torch.ones((1, seq_len), dtype=torch.long)
    dummy_mask  = torch.ones((1, seq_len), dtype=torch.long)
    dummy_types = torch.zeros((1, seq_len), dtype=torch.long)

    with torch.no_grad():
        torch.onnx.export(
            model,
            (dummy_ids, dummy_mask, dummy_types),
            str(fp32_path),
            input_names=["input_ids", "attention_mask", "token_type_ids"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids":      {0: "batch", 1: "seq"},
                "attention_mask": {0: "batch", 1: "seq"},
                "token_type_ids": {0: "batch", 1: "seq"},
                "logits":         {0: "batch"},
            },
            opset_version=14,
            do_constant_folding=True,
        )

    logger.info("ClinicalBERT FP32 exported", path=str(fp32_path))
    _quantize(fp32_path, int8_path)


class _SentenceBERTBackbone(nn.Module):
    """Thin wrapper that exposes only last_hidden_state for ONNX export."""

    def __init__(self, backbone: nn.Module):
        super().__init__()
        self.backbone = backbone

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: torch.Tensor,
    ) -> torch.Tensor:
        out = self.backbone(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        )
        return out.last_hidden_state


def export_sentencebert(output_dir: Path) -> None:
    from core.config import get_ai_settings

    settings = get_ai_settings()
    fp32_path = output_dir / "sentencebert_fp32.onnx"
    int8_path = output_dir / "sentencebert_int8.onnx"

    if int8_path.exists():
        logger.info("Sentence-BERT INT8 already exported, skipping")
        return

    logger.info("Exporting Sentence-BERT backbone to ONNX", model=settings.sentence_bert_model)

    from sentence_transformers import SentenceTransformer
    from transformers import AutoTokenizer

    sbert = SentenceTransformer(settings.sentence_bert_model, device="cpu")
    backbone = _SentenceBERTBackbone(sbert._first_module().auto_model)
    backbone.eval()

    tokenizer = AutoTokenizer.from_pretrained(settings.sentence_bert_model)

    seq_len = 64
    dummy_ids   = torch.ones((1, seq_len), dtype=torch.long)
    dummy_mask  = torch.ones((1, seq_len), dtype=torch.long)
    dummy_types = torch.zeros((1, seq_len), dtype=torch.long)

    with torch.no_grad():
        torch.onnx.export(
            backbone,
            (dummy_ids, dummy_mask, dummy_types),
            str(fp32_path),
            input_names=["input_ids", "attention_mask", "token_type_ids"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "input_ids":        {0: "batch", 1: "seq"},
                "attention_mask":   {0: "batch", 1: "seq"},
                "token_type_ids":   {0: "batch", 1: "seq"},
                "last_hidden_state": {0: "batch", 1: "seq"},
            },
            opset_version=14,
            do_constant_folding=True,
        )

    logger.info("Sentence-BERT FP32 exported", path=str(fp32_path))
    _quantize(fp32_path, int8_path)


def run_export() -> None:
    from core.config import get_ai_settings
    import structlog
    structlog.configure(processors=[structlog.dev.ConsoleRenderer()])

    settings = get_ai_settings()
    out = Path(settings.onnx_cache_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        export_clinicalbert(out)
    except Exception as exc:
        logger.error("ClinicalBERT export failed", error=str(exc))

    try:
        export_sentencebert(out)
    except Exception as exc:
        logger.error("Sentence-BERT export failed", error=str(exc))

    logger.info("ONNX export complete", output_dir=str(out))


if __name__ == "__main__":
    run_export()
