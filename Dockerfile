# Stage 1: builder - install all Python dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements.txt

# Stage 2: runtime - only runtime deps + Python packages from builder
FROM python:3.11-slim

WORKDIR /app

# Force unbuffered stdout/stderr so Docker captures logs immediately
ENV PYTHONUNBUFFERED=1

# PaddlePaddle 2.x requires protobuf <4; this env var makes it
# compatible with newer protobuf versions if pin is overridden.
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Install system libraries required by PaddlePaddle / PaddleOCR / OpenCV at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .


CMD ["python", "main.py"]
