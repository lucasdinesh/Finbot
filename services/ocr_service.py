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
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
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

            import contextlib
            with open(os.devnull, "w") as devnull, contextlib.redirect_stderr(devnull):
                import easyocr
                self._reader = easyocr.Reader(['en', 'pt'], gpu=False)
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
        Run OCR on raw image bytes, trying multiple preprocessing variants
        and selecting the one that yields the best LLM extraction (or highest
        OCR confidence if LLM unavailable).

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

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = gray.mean()
        contrast = gray.std()
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        logger.info("Image | brightness=%.1f contrast=%.1f sharpness=%.1f",
                     brightness, contrast, sharpness)

        if sharpness < 40:
            start_variant = "CLAHE"
            threshold = 0.50
            heuristic_reason = "low_sharpness"
            logger.info("Heuristic: low sharpness -> start with CLAHE, threshold=0.50")
        elif brightness < 80:
            start_variant = "grayscale"
            threshold = 0.50
            heuristic_reason = "low_brightness"
            logger.info("Heuristic: low brightness -> start with grayscale, threshold=0.50")
        else:
            start_variant = "grayscale"
            threshold = 0.70
            heuristic_reason = "clean_image"
            logger.info("Heuristic: clean image -> start with grayscale, threshold=0.70")

        # Define preprocessing variants
        def make_grayscale(im):
            return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

        def make_adaptive(im):
            h, w = im.shape[:2]
            gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=31,
                C=10,
            )
            return binary

        def make_adaptive_c25(im):
            h, w = im.shape[:2]
            gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=31,
                C=25,
            )
            return binary

        def make_clahe(im):
            h, w = im.shape[:2]
            gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(gray)

        variant_map = {
            "grayscale": ("grayscale", make_grayscale),
            "adaptive C=10": ("adaptive C=10", make_adaptive),
            "adaptive C=25": ("adaptive C=25", make_adaptive_c25),
            "CLAHE": ("CLAHE", make_clahe),
        }

        # Order: start variant first, then the remaining
        ordered = ["grayscale", "adaptive C=10", "adaptive C=25", "CLAHE"]
        ordered.remove(start_variant)
        ordered.insert(0, start_variant)

        best_results = None
        best_score = -1.0
        best_variant_name = None

        base_reader = self._get_reader()

        # Per-variant metrics collection
        run_id = uuid.uuid4().hex[:8]
        per_variant_metrics = {}

        for name in ordered:
            prep_func = variant_map[name][1]
            logger.info("Trying OCR variant: %s", name)
            variant_start = time.time()
            try:
                prep_img = prep_func(img)
            except Exception as e:
                logger.warning("Variant %s preprocessing failed: %s", name, e)
                continue

            try:
                results = base_reader.readtext(prep_img)
            except Exception as exc:
                logger.warning("EasyOCR inference failed for variant %s: %s", name, exc)
                continue

            elapsed = time.time() - variant_start

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

            logger.info("Variant %s: OCR found %d lines", name, len(extracted))
            if extracted:
                for i, (text, conf) in enumerate(extracted[:3]):
                    logger.info("Variant %s line %d: conf=%.4f | %s", name, i+1, conf, text)
                if len(extracted) > 3:
                    logger.info("Variant %s: ... and %d more lines", name, len(extracted)-3)

            if extracted:
                avg_conf = sum(c for _, c in extracted) / len(extracted)
            else:
                avg_conf = 0.0

            score = avg_conf

            per_variant_metrics[name] = {
                "num_lines": len(extracted),
                "avg_confidence": round(avg_conf, 4),
                "time_seconds": round(elapsed, 3),
                "texts": [t for t, _ in extracted],
                "confidences": [round(c, 4) for _, c in extracted],
                "score": round(score, 4),
                "threshold_met": score >= threshold,
            }

            if score > best_score:
                best_score = score
                best_results = extracted
                best_variant_name = name

            if score >= threshold:
                logger.info("Variant %s met threshold (%.4f >= %.4f), early exit",
                            name, score, threshold)
                break

        if best_results is None:
            logger.warning("All OCR variants failed; returning empty list")
            return []

        logger.info("Selected OCR variant: %s (score=%.4f)", best_variant_name, best_score)
        logger.info("Total OCR lines extracted: %d", len(best_results))
        for text, conf in best_results:
            logger.info("OCR LINE | conf=%.4f | %s", conf, text)

        # Write per-variant metrics to disk
        metrics = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "image": {
                "width": w,
                "height": h,
                "brightness": round(float(brightness), 1),
                "contrast": round(float(contrast), 1),
                "sharpness": round(float(sharpness), 1),
            },
            "heuristic": {
                "start_variant": start_variant,
                "threshold": threshold,
                "reason": heuristic_reason,
            },
            "variants": per_variant_metrics,
            "selected": {
                "variant": best_variant_name,
                "score": round(best_score, 4),
                "num_lines": len(best_results),
            },
        }
        try:
            metrics_dir = "ocr_metrics"
            os.makedirs(metrics_dir, exist_ok=True)
            fname = f"{metrics_dir}/{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)
            logger.info("OCR metrics written to %s", fname)
        except Exception as e:
            logger.warning("Failed to write OCR metrics: %s", e)

        return best_results

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
