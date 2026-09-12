FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CCTV_DATA_DIR=/var/lib/sentinel CCTV_DB_PATH=/var/lib/sentinel/sentinel.db CCTV_MEDIA_DIR=/var/lib/sentinel/media CCTV_DEMO_DIR=/var/lib/sentinel/demo
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/setup_models.py backend/evaluate_run.py ./
COPY deploy /app/deploy
COPY --from=frontend /build/dist /app/frontend/dist
RUN useradd --uid 10001 --create-home sentinel && mkdir -p /var/lib/sentinel/media /var/lib/sentinel/demo /app/backend/app/models && chown -R sentinel:sentinel /var/lib/sentinel /app
USER sentinel
EXPOSE 8000
CMD ["python", "/app/deploy/serve.py"]

FROM runtime AS ai
USER root
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url ${TORCH_INDEX_URL}
COPY backend/requirements-ai.txt ./requirements-ai.txt
RUN pip install --no-cache-dir -r requirements-ai.txt
USER sentinel

# Explicit build-time downloads; the deployed image starts without downloading weights.
USER root
ENV CCTV_OCR_MODEL_DIR=/opt/sentinel-ocr
RUN CCTV_DATA_DIR=/tmp/model-setup python setup_models.py --plate-detector && chown -R sentinel:sentinel /opt/sentinel-ocr /app/backend/app/models && rm -rf /tmp/model-setup
USER sentinel
