#!/usr/bin/env python3
"""OCR Analysis Tool — Compare preprocessing models for receipt OCR.

Usage:
  1. Place .jpg receipt images in the receipts/ folder
  2. Run: python preprocess.py

Output (all auto-generated):
  - Pre-processed images/  → folders per image with model variants + collage
  - metrics/               → CSV with scores, lines, timing
  - charts/                → bar charts and scatter plots
"""

import os
import sys
import time
import warnings
import logging
import concurrent.futures as cf
from datetime import datetime

import cv2
import numpy as np
import pandas as pd

os.environ["TQDM_DISABLE"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
warnings.filterwarnings("ignore", message="Could not initialize NNPACK")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
OUTPUT_DIR = os.path.join(BASE_DIR, "Pre-processed images")
METRICS_DIR = os.path.join(BASE_DIR, "metrics")
CHARTS_DIR = os.path.join(BASE_DIR, "charts")
MAX_WIDTH = 1280

# ---------------------------------------------------------------------------
# EasyOCR reader (lazy loaded)
# ---------------------------------------------------------------------------
_reader = None


def get_reader():
    global _reader
    if _reader is None:
        logger.info("Loading EasyOCR reader (en, pt) …")
        import easyocr
        _reader = easyocr.Reader(["en", "pt"], gpu=False)
        logger.info("EasyOCR reader ready")
    return _reader


# ---------------------------------------------------------------------------
# Preprocessing models
# Each function receives the original BGR image (resized) and returns
# either a single-channel (grayscale/binary) or 3-channel image.
# ---------------------------------------------------------------------------
MODELS = []


def register(name):
    def decorator(fn):
        MODELS.append((name, fn))
        return fn
    return decorator


@register("Original")
def original(im):
    return im.copy()


@register("Grayscale")
def grayscale(im):
    return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)


@register("Adaptive C=25")
def adaptive_c25(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(
        g, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31, C=25,
    )


@register("Otsu")
def otsu(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


@register("CLAHE")
def clahe(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    clahe_obj = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe_obj.apply(g)


@register("Sharpen + Denoise")
def sharpen_denoise(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(g, h=10)
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    return cv2.filter2D(denoised, -1, kernel)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_imwrite(path, img):
    if img.ndim == 3:
        cv2.imwrite(path, img)
    else:
        cv2.imwrite(path, img)


def load_and_resize(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Failed to read {image_path}")
    h, w = img.shape[:2]
    if w > MAX_WIDTH:
        scale = MAX_WIDTH / w
        new_w, new_h = MAX_WIDTH, int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img


def run_ocr(reader, img):
    """Run EasyOCR, suppressing its stderr chatter."""
    old = os.dup(2)
    null = os.open(os.devnull, os.O_RDWR)
    os.dup2(null, 2)
    try:
        results = reader.readtext(img)
    except Exception:
        results = []
    finally:
        os.dup2(old, 2)
        os.close(null)
        os.close(old)

    extracted = []
    for item in results:
        _, text, conf = item if len(item) == 3 else (*item, 1.0)
        text = text.strip()
        if text:
            extracted.append((text, conf))
    return extracted


def sanitise(name):
    return name.replace(" ", "_").replace("=", "")


# ---------------------------------------------------------------------------
# Per-image processing
# ---------------------------------------------------------------------------

def process_image(image_name, image_path):
    img = load_and_resize(image_path)
    stem = os.path.splitext(image_name)[0]

    img_out_dir = os.path.join(OUTPUT_DIR, stem)
    os.makedirs(img_out_dir, exist_ok=True)

    reader = get_reader()
    rows = []

    for model_name, func in MODELS:
        t0 = time.time()
        try:
            processed = func(img)
            pre_time = time.time() - t0

            out_name = f"{stem}-{sanitise(model_name)}.jpg"
            out_path = os.path.join(img_out_dir, out_name)
            _safe_imwrite(out_path, processed)

            ocr_t0 = time.time()
            extracted = run_ocr(reader, processed)
            ocr_time = time.time() - ocr_t0

            score = (sum(c for _, c in extracted) / len(extracted)
                     if extracted else 0.0)
            lines = len(extracted)

            rows.append({
                "recibo": stem,
                "modelo": model_name,
                "score": round(score, 4),
                "linhas": lines,
                "tempo_ocr_s": round(ocr_time, 3),
                "tempo_preproc_s": round(pre_time, 3),
            })

            logger.info("  %-20s | score=%.4f | linhas=%2d | OCR=%.1fs",
                        model_name, score, lines, ocr_time)

        except Exception as e:
            logger.warning("  %-20s | ERRO: %s", model_name, e)
            rows.append({
                "recibo": stem,
                "modelo": model_name,
                "score": 0.0,
                "linhas": 0,
                "tempo_ocr_s": 0.0,
                "tempo_preproc_s": round(time.time() - t0, 3),
            })

    _create_collage(stem, img_out_dir)
    return rows


# ---------------------------------------------------------------------------
# Collage (2 × 3 grid)
# ---------------------------------------------------------------------------

def _create_collage(stem, img_out_dir):
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()
    for i, (model_name, _) in enumerate(MODELS):
        path = os.path.join(img_out_dir,
                            f"{stem}-{sanitise(model_name)}.jpg")
        if os.path.exists(path):
            im = cv2.imread(path)
            if im is None:
                axes[i].text(0.5, 0.5, "error", ha="center", va="center")
            else:
                rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
                axes[i].imshow(rgb)
        axes[i].set_title(f"({i+1}) {model_name}",
                          fontsize=13, fontweight="bold")
        axes[i].axis("off")
    plt.tight_layout()
    out = os.path.join(img_out_dir, "collage.jpg")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("  Collage → %s", out)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _bar_chart(df, col, ylabel, title, filename, ylim=None):
    order = df.groupby("modelo")[col].mean().sort_values(ascending=False).index
    fig, ax = plt.subplots(figsize=(10, 6))
    data = [df[df["modelo"] == m][col].values for m in order]
    bp = ax.boxplot(data, labels=order, patch_artist=True,
                    boxprops=dict(facecolor="#AED6F1", alpha=0.7))
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Modelo")
    if ylim:
        ax.set_ylim(*ylim)
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, filename), dpi=150, bbox_inches="tight")
    plt.close(fig)


def _scatter_chart(df):
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = plt.cm.tab10(np.linspace(0, 1, len(MODELS)))
    for m, c in zip(MODELS, colors):
        sub = df[df["modelo"] == m[0]]
        ax.scatter(sub["linhas"], sub["score"],
                   label=m[0], alpha=0.7, s=65,
                   color=c, edgecolors="black", linewidth=0.4)
    ax.set_title("Linhas detectadas vs Score de confiança",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Linhas detectadas")
    ax.set_ylabel("Score (confiança média)")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "linhas_vs_score.png"),
                dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_charts(df):
    os.makedirs(CHARTS_DIR, exist_ok=True)
    _bar_chart(df, "score",
               "Score (confiança média)",
               "Score médio de confiança por modelo",
               "score_por_modelo.png", ylim=(0, 1))
    _bar_chart(df, "linhas",
               "Linhas detectadas",
               "Linhas detectadas por modelo",
               "linhas_por_modelo.png")
    _scatter_chart(df)
    logger.info("Charts saved to %s", CHARTS_DIR)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(METRICS_DIR, exist_ok=True)

    exts = (".jpg", ".jpeg", ".png")
    images = sorted(f for f in os.listdir(RECEIPTS_DIR)
                    if f.lower().endswith(exts))
    if not images:
        logger.error("Nenhuma imagem .jpg encontrada em: %s", RECEIPTS_DIR)
        logger.info("Coloque seus recibos na pasta 'receipts/' e rode novamente.")
        sys.exit(1)

    logger.info("Encontradas %d imagem(ns) em '%s'", len(images), RECEIPTS_DIR)

    all_rows = []
    for image_name in images:
        path = os.path.join(RECEIPTS_DIR, image_name)
        logger.info("\n=== %s ===", image_name)
        try:
            all_rows.extend(process_image(image_name, path))
        except Exception as e:
            logger.error("Falha ao processar %s: %s", image_name, e)

    # --- Save metrics CSV ---
    df = pd.DataFrame(all_rows)
    csv_path = os.path.join(METRICS_DIR, "resultados.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info("\nMétricas salvas → %s", csv_path)

    # --- Best model per receipt ---
    best_idx = df.loc[df.groupby("recibo")["score"].idxmax()]
    best_path = os.path.join(METRICS_DIR, "melhor_modelo_por_recibo.csv")
    best_idx[["recibo", "modelo", "score", "linhas"]].to_csv(
        best_path, index=False, encoding="utf-8-sig")
    logger.info("Melhor modelo por recibo → %s", best_path)

    # --- Charts ---
    if len(images) > 1:
        logger.info("\nGerando gráficos …")
        generate_charts(df)
    else:
        logger.info("\nApenas 1 imagem — gráficos comparativos não gerados.")

    # --- Summary ---
    logger.info("\n" + "=" * 65)
    logger.info("RESUMO")
    logger.info("=" * 65)
    gb = df.groupby("modelo")[["score", "linhas"]].agg(
        ["mean", "std", "max", "count"])
    logger.info("\n%s", gb.to_string())

    wins = (df.loc[df.groupby("recibo")["score"].idxmax()]
            ["modelo"].value_counts())
    logger.info("\nVitórias por modelo (melhor score):")
    for m, c in wins.items():
        logger.info("  %-22s  %d/%d", m, c, len(images))

    logger.info("\nProcesso concluído com sucesso!")


if __name__ == "__main__":
    main()
