"""Modal.com deployment for the AgriScan 3D FastAPI backend.

Deploy:  modal deploy modal_app.py
Secrets: modal secret create agriscan-secrets \
             MONGODB_URI=... JWT_SECRET_KEY=... \
             ALLOWED_ORIGINS=... ENV=production
"""
import modal

app = modal.App("agriscan-api")

# Same recipe as the Dockerfile: CPU-only torch first (requirements.txt pins
# satisfy the +cpu local versions), then the rest of requirements.txt.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0", "libgomp1", "gcc", "g++")
    .pip_install(
        "torch==2.5.1+cpu",
        "torchvision==0.20.1+cpu",
        index_url="https://download.pytorch.org/whl/cpu",
    )
    .add_local_file("requirements.txt", "/root/requirements.txt", copy=True)
    .run_commands("pip install --no-cache-dir -r /root/requirements.txt")
    # App package + model weights. Paths mirror the repo layout so
    # BACKEND_DIR-relative resolution (models/best.pt, yolov8n-cls.pt,
    # models/domain_guard.npz) keeps working unchanged.
    .add_local_dir("app", "/root/app")
    .add_local_dir("models", "/root/models")
    .add_local_file("yolov8n-cls.pt", "/root/yolov8n-cls.pt")
    .add_local_file("yolov8n.pt", "/root/yolov8n.pt")
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("agriscan-secrets")],
    cpu=1,
    memory=2048,
    min_containers=0,          # scale to zero when idle -> saves free credits
    scaledown_window=300,
    timeout=300,
)
@modal.asgi_app()
def fastapi_app():
    from app.main import app as fastapi

    return fastapi
