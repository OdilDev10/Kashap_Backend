FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc git \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy pyproject.toml
COPY pyproject.toml ./

# Install dependencies with uv
RUN uv pip install --system -e ".[dev]"

# Pre-download PaddleOCR models to avoid first-run slowness
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='es', use_gpu=False)" || true

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
