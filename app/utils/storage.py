from pathlib import Path
import uuid

UPLOAD_DIR = Path("test_images")

UPLOAD_DIR.mkdir(exist_ok=True)


def upload_file_to_s3(content: bytes, filename: str, folder: str = ""):

    file_name = f"{uuid.uuid4()}_{filename}"

    folder_path = UPLOAD_DIR / folder
    folder_path.mkdir(parents=True, exist_ok=True)

    file_path = folder_path / file_name

    with open(file_path, "wb") as f:
        f.write(content)

    return str(file_path.resolve())