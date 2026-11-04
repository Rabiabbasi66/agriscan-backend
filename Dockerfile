FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# CPU-only PyTorch from the official CPU wheel index, installed FIRST and
# pinned to the exact versions the project uses. On Linux the default PyPI
# torch wheels pull the multi-GB CUDA/nvidia stack; the CPU index avoids that.
RUN pip install --no-cache-dir \
    torch==2.5.1 torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
# requirements.txt pins the same torch/torchvision versions; pip sees them
# already satisfied by the CPU wheels above and does not reinstall them.
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Google Cloud Run injects the runtime $PORT; fall back to 8000 for local
# container runs. Shell-based form so ${PORT:-8000} is expanded at startup.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
