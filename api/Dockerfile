FROM python:3.12-slim AS builder

WORKDIR /build
COPY api/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && rm -rf /install/lib/python3.12/site-packages/sympy \
        /install/lib/python3.12/site-packages/sympy-*.dist-info

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_VERSION=1.0.0 \
    MODEL_VERSION=1.1.0 \
    MODEL_PATH=/app/model/model-1.1.0.onnx

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY --from=builder /install /usr/local
COPY api/main.py /app/main.py
COPY model/model-1.1.0.onnx /app/model/model-1.1.0.onnx

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
