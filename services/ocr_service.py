"""OCR service for receipt text extraction using EasyOCR."""
import json
import logging
import os
import time
import uuid
import warnings
from datetime import datetime
from threading import Lock
from typing import List, Tuple

os.environ["TQDM_DISABLE"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
warnings.filterwarnings("ignore", message="Could not initialize NNPACK")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class OcrService:
    """Singleton service for extracting and parsing text from receipt images."""

    _instance = None
    _init_lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._reader = None
                    cls._instance._engine = None
                    cls._instance._llm_service = None
        return cls._instance

    @property
    def llm_service(self):
        return self._llm_service

    @llm_service.setter
    def llm_service(self, service):
        self._llm_service = service

    def _get_reader(self):
        """Lazy-load EasyOCR reader."""
        if self._reader is not None:
            return self._reader

        with self._init_lock:
            if self._reader is not None:
                return self._reader

            old_fd = os.dup(2)
            devnull_fd = os.open(os.devnull, os.O_RDWR)
            os.dup2(devnull_fd, 2)
            try:
                import easyocr
                self._reader = easyocr.Reader(['en', 'pt'], gpu=False)
            finally:
                os.dup2(old_fd, 2)
                os.close(devnull_fd)
                os.close(old_fd)
            self._engine = 'easyocr'
            logger.info("Using EasyOCR engine")
        return self._reader

    def _get_ocr(self):
        """Pre-download models at startup (warm-up)."""
        return self._get_reader()

    # ------------------------------------------------------------------
    # OCR extraction
    # ------------------------------------------------------------------

    def extract_text(self, image_bytes: bytes) -> List[Tuple[float, float]]:
        """
        Run OCR on raw image bytes using adaptive C=25 preprocessing.

        Returns a list of (text, confidence) tuples sorted top-to-bottom.
        """
        import numpy as np
        import cv2

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.error("Failed to decode image bytes")
            return []

        h, w = img.shape[:2]
        if w > 1280:
            scale = 1280.0 / w
            new_w, new_h = 1280, int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            logger.info("Downscaled image from %dx%d to %dx%d", w, h, new_w, new_h)
            h, w = new_h, new_w

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = gray.mean()
        contrast = gray.std()
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        logger.info("Image | brightness=%.1f contrast=%.1f sharpness=%.1f",
                     brightness, contrast, sharpness)

        base_reader = self._get_reader()

        # Preprocess with adaptive C=25
        prep_img = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=31,
            C=25,
        )
        logger.info("Preprocessed with adaptive C=25")

        ocr_start = time.time()
        try:
            r_fd = os.dup(2)
            n_fd = os.open(os.devnull, os.O_RDWR)
            os.dup2(n_fd, 2)
            try:
                results = base_reader.readtext(prep_img)
            finally:
                os.dup2(r_fd, 2)
                os.close(n_fd)
                os.close(r_fd)
        except Exception as exc:
            logger.error("OCR failed: %s", exc)
            return []

        elapsed = time.time() - ocr_start
        extracted = []
        for item in results:
            if len(item) == 3:
                _bbox, text, confidence = item
            else:
                _bbox, text = item
                confidence = 1.0
            text = text.strip()
            if text:
                extracted.append((text, confidence))

        avg_conf = sum(c for _, c in extracted) / len(extracted) if extracted else 0.0
        logger.info("OCR found %d lines (avg confidence=%.4f, time=%.1fs)",
                     len(extracted), avg_conf, elapsed)
        for text, conf in extracted:
            logger.info("OCR LINE | conf=%.4f | %s", conf, text)

        # Write OCR metrics to disk
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "image": {"width": w, "height": h},
            "variant": "adaptive C=25",
            "num_lines": len(extracted),
            "avg_confidence": round(avg_conf, 4),
            "time_seconds": round(elapsed, 3),
        }
        try:
            metrics_dir = "ocr_metrics"
            os.makedirs(metrics_dir, exist_ok=True)
            fname = f"{metrics_dir}/{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)
            logger.info("OCR metrics written to %s", fname)
        except Exception as e:
            logger.warning("Failed to write OCR metrics: %s", e)

        return extracted

    # ------------------------------------------------------------------
    # Receipt parsing
    # ------------------------------------------------------------------

    def parse_receipt(self, ocr_results: List[Tuple[str, float]]) -> dict:
        """
        Parse OCR results into structured receipt data using LLM.

        Falls back to raw text if LLM is unavailable or fails — the handler
        will then prompt the user to fill in the fields manually.
        """
        texts = [t for t, _ in ocr_results]
        raw_text = "\n".join(texts)

        confidence = (
            sum(c for _, c in ocr_results) / len(ocr_results)
            if ocr_results else 0.0
        )

        if self._llm_service:
            try:
                fields = self._llm_service.extract_receipt_fields(raw_text)
                if fields:
                    logger.info("LLM extraction succeeded: %s", fields)
                    return {
                        "amount": fields.get("amount"),
                        "date": fields.get("date"),
                        "store_name": fields.get("store_name"),
                        "raw_text": raw_text,
                        "confidence": confidence,
                    }
                logger.info("LLM returned no fields")
            except Exception as exc:
                logger.warning("LLM extraction failed: %s", exc)
        else:
            logger.info("LLM service not available")

        logger.info("No LLM result — returning raw text for manual input")
        return {
            "amount": None,
            "date": None,
            "store_name": None,
            "raw_text": raw_text,
            "confidence": confidence,
        }
