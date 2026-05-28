"""OCR service for receipt text extraction using EasyOCR (primary) and PaddleOCR (fallback)."""
import logging
import os
import re
from threading import Lock
from typing import Optional, List, Tuple

# Suppress PaddleOCR's tqdm download progress bars — they use \r carriage
# returns that overwrite our application logs in Docker's output.
os.environ["TQDM_DISABLE"] = "1"

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
        """Lazy-load OCR engine: PaddleOCR primary, EasyOCR fallback."""
        if self._reader is not None:
            return self._reader

        with self._init_lock:
            if self._reader is not None:
                return self._reader

            try:
                from paddleocr import PaddleOCR
                self._reader = PaddleOCR(
                    use_angle_cls=False,
                    lang='en',
                    use_gpu=False,
                    show_log=False,
                )
                self._engine = 'paddleocr'
                logger.info("Using PaddleOCR engine")
            except Exception as exc:
                logger.warning("PaddleOCR failed (%s), falling back to EasyOCR", exc)
                try:
                    import easyocr
                    self._reader = easyocr.Reader(['en', 'pt'], gpu=False)
                    self._engine = 'easyocr'
                    logger.info("Using EasyOCR engine")
                except Exception as exc2:
                    logger.error("EasyOCR also failed: %s", exc2)
                    raise
        return self._reader

    def _get_ocr(self):
        """Pre-download models at startup (warm-up)."""
        return self._get_reader()

    def _preprocess_image(self, img):
        import cv2
        h, w = img.shape[:2]
        logger.info("Image dimensions: %dx%d", w, h)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=31,
            C=25,
        )
        logger.info("Image preprocessed (grayscale + adaptive threshold)")
        return binary

    def extract_text(self, image_bytes: bytes) -> List[Tuple[str, float]]:
        """
        Run OCR on raw image bytes.

        Returns a list of (text, confidence) tuples sorted top-to-bottom.
        """
        import numpy as np
        import cv2

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.error("Failed to decode image bytes")
            return []

        img = self._preprocess_image(img)

        reader = self._get_reader()
        extracted = []

        if self._engine == 'easyocr':
            try:
                results = reader.readtext(img)
            except Exception as exc:
                logger.error("EasyOCR inference failed: %s", exc)
                return []
            logger.info("EasyOCR returned %d raw results", len(results))
            for _bbox, text, confidence in results:
                text = text.strip()
                if text:
                    extracted.append((text, confidence))
                    logger.debug("OCR: \"%s\" (conf=%.4f)", text, confidence)
        else:
            try:
                results = reader.ocr(img, cls=False)
            except Exception as exc:
                logger.error("PaddleOCR inference failed: %s — falling back to EasyOCR", exc)
                try:
                    import easyocr
                    easy_reader = easyocr.Reader(['en', 'pt'], gpu=False)
                    results = easy_reader.readtext(img)
                    self._reader = easy_reader
                    self._engine = 'easyocr'
                    for _bbox, text, confidence in results:
                        text = text.strip()
                        if text:
                            extracted.append((text, confidence))
                    logger.info("EasyOCR fallback returned %d results", len(extracted))
                    return extracted
                except Exception as exc2:
                    logger.error("EasyOCR fallback also failed: %s", exc2)
                    return []
            for page in results:
                if page is None:
                    continue
                for item in page:
                    if item and len(item) >= 2:
                        _, (text, confidence) = item
                        text = text.strip()
                        if text:
                            extracted.append((text, confidence))
                            logger.debug("OCR: \"%s\" (conf=%.4f)", text, confidence)

        logger.info("Total OCR lines extracted: %d", len(extracted))
        for text, conf in extracted:
            logger.info("OCR LINE | conf=%.4f | %s", conf, text)
        return extracted

    def parse_receipt(self, ocr_results: List[Tuple[str, float]]) -> dict:
        """
        Parse OCR results into structured receipt data.

        Uses AI (LLM) first when available; falls back to regex heuristics.

        Returns a dict with keys:
          amount, store_name, date, raw_text, confidence
        """
        texts = [t for t, _ in ocr_results]
        raw_text = "\n".join(texts)

        confidence = (
            sum(c for _, c in ocr_results) / len(ocr_results)
            if ocr_results else 0.0
        )

        if self._llm_service:
            try:
                llm_fields = self._llm_service.extract_receipt_fields(raw_text)
                if llm_fields:
                    logger.info("LLM extraction succeeded: %s", llm_fields)
                    return {
                        "amount": llm_fields.get("amount"),
                        "date": llm_fields.get("date"),
                        "store_name": llm_fields.get(
                            "store_name", "Despesa não identificada"
                        ),
                        "raw_text": raw_text,
                        "confidence": confidence,
                    }
                logger.info("LLM returned no fields, falling back to regex")
            except Exception as exc:
                logger.warning("LLM extraction failed: %s", exc)
        else:
            logger.info("LLM service not available, using regex fallback")

        logger.info("=== REGEX FALLBACK ===")
        amount = self._extract_amount(texts)
        date = self._extract_date(texts)
        store_name = self._extract_store_name(texts)
        logger.info("Regex result — amount=%s, date=%s, store_name=%s", amount, date, store_name)

        return {
            "amount": amount,
            "date": date,
            "store_name": store_name,
            "raw_text": raw_text,
            "confidence": confidence,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    _AMOUNT_PATTERNS = [
        re.compile(r'(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*\,\d{2})'),
        re.compile(r'(?:R\$\s*)?(\d+\,\d{2})'),
    ]

    def _extract_amount(self, texts: List[str]) -> Optional[float]:
        """Extract the largest monetary value from text lines."""
        candidates = []
        for text in texts:
            for pattern in self._AMOUNT_PATTERNS:
                for match in pattern.findall(text):
                    normalized = match.replace('.', '').replace(',', '.')
                    candidates.append(float(normalized))
        return max(candidates) if candidates else None

    _DATE_PATTERNS = [
        re.compile(r'(\d{2})[/-](\d{2})[/-](\d{4})'),
        re.compile(r'(\d{2})[/-](\d{2})[/-](\d{2})'),
    ]

    def _extract_date(self, texts: List[str]) -> Optional[str]:
        """Extract first date found and return as DD-MM-YYYY."""
        for text in texts:
            for pattern in self._DATE_PATTERNS:
                match = pattern.search(text)
                if match:
                    day, month, year = match.groups()
                    if len(year) == 2:
                        year = '20' + year
                    return f"{day}-{month}-{year}"
        return None

    _SKIP_KEYWORDS = [
        'cupom', 'nfce', 'sat', 'nfe', 'nota', 'fiscal', 'cnpj',
        'cpf', 'ie', 'im', 'data', 'hora', 'telefone', 'endereco',
        'endereço', 'www', 'http', 'com.br', '.com', 'protocolo',
        'documento', 'código', 'codigo', 'chave', 'consumidor',
    ]

    def _extract_store_name(self, texts: List[str]) -> str:
        """Guess the store / establishment name from OCR lines."""
        if not texts:
            return "Despesa não identificada"

        for text in texts:
            stripped = text.strip()
            lower = stripped.lower()

            if any(kw in lower for kw in self._SKIP_KEYWORDS):
                continue
            if re.match(r'^[\d\s,\.\$R%]+$', stripped):
                continue
            if re.match(r'^\d{2}[/-]\d{2}[/-]\d{2,4}$', stripped):
                continue
            if len(stripped) < 3:
                continue

            return stripped

        return "Despesa não identificada"
