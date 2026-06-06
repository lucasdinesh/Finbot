"""OCR service for receipt text extraction using EasyOCR."""
import concurrent.futures
import gc
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
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
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
                    cls._instance._ocr_lock = Lock()
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
            try:
                devnull_fd = os.open(os.devnull, os.O_RDWR)
            except OSError:
                os.close(old_fd)
                raise
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
        Run OCR on raw image bytes, trying grayscale and adaptive C=25
        preprocessing in parallel, picking the best result.

        Returns a list of (text, confidence) tuples sorted top-to-bottom.
        """
        with self._ocr_lock:
            return self._extract_text_locked(image_bytes)

    def _extract_text_locked(self, image_bytes: bytes) -> List[Tuple[float, float]]:
        import numpy as np
        import cv2

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.error("Failed to decode image bytes")
            return []

        h, w = img.shape[:2]
        if w > 960:
            scale = 960.0 / w
            new_w, new_h = 960, int(h * scale)
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

        # Preprocess variants: grayscale and adaptive C=25
        def make_grayscale(im):
            return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

        def make_adaptive_c25(im):
            g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            return cv2.adaptiveThreshold(
                g, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=31, C=25,
            )

        variant_map = {
            "grayscale": make_grayscale,
            "adaptive C=25": make_adaptive_c25,
        }

        preprocessed = {}
        for name, func in variant_map.items():
            try:
                preprocessed[name] = func(img)
                logger.info("Preprocessed variant: %s", name)
            except Exception as e:
                logger.warning("Variant %s failed: %s", name, e)

        if not preprocessed:
            logger.warning("All variants failed")
            return []

        def run_variant(name):
            start = time.time()
            try:
                r_fd = os.dup(2)
                try:
                    n_fd = os.open(os.devnull, os.O_RDWR)
                except OSError:
                    os.close(r_fd)
                    raise
                os.dup2(n_fd, 2)
                try:
                    results = base_reader.readtext(preprocessed[name])
                finally:
                    os.dup2(r_fd, 2)
                    os.close(n_fd)
                    os.close(r_fd)
            except Exception as exc:
                return name, None, time.time() - start, str(exc)
            elapsed = time.time() - start
            extracted = []
            for item in results:
                _, text, conf = item if len(item) == 3 else (*item, 1.0)
                text = text.strip()
                if text:
                    extracted.append((text, conf))
            return name, extracted, elapsed, None

        per_variant = {}
        for name in preprocessed:
            _, extracted, elapsed, error = run_variant(name)
            score = sum(c for _, c in extracted) / len(extracted) if extracted else 0.0
            per_variant[name] = {
                "extracted": extracted,
                "score": score,
                "time": round(elapsed, 3),
                "error": error,
            }
            if error:
                logger.warning("Variant %s errored: %s", name, error)
            else:
                logger.info("Variant %s: %d lines, score=%.4f, time=%.1fs",
                            name, len(extracted), score, elapsed)

        valid = {n: d for n, d in per_variant.items() if d["error"] is None}
        if not valid:
            logger.warning("All variants failed; returning empty list")
            return []

        best_name = max(valid, key=lambda n: valid[n]["score"])
        best = valid[best_name]
        logger.info("Selected variant: %s (score=%.4f)", best_name, best["score"])
        for text, conf in best["extracted"]:
            logger.info("OCR LINE | conf=%.4f | %s", conf, text)

        # Free memory from the non-selected variant
        gc.collect()

        # Write metrics
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "image": {"width": w, "height": h},
            "selected": best_name,
            "selected_score": best["score"],
            "selected_lines": len(best["extracted"]),
            "variants": {
                n: {
                    "score": d["score"],
                    "lines": len(d.get("extracted", [])),
                    "time_seconds": d["time"],
                    "error": d.get("error"),
                }
                for n, d in per_variant.items()
            },
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

        return best["extracted"]

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
