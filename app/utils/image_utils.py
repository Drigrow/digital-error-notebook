import os
import base64
import uuid
from PIL import Image
from io import BytesIO


def save_upload(file_storage, upload_folder):
    """Save an uploaded file and return its path relative to upload_folder."""
    ext = os.path.splitext(file_storage.filename)[1].lower() or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_folder, filename)
    file_storage.save(filepath)
    return filename


def image_to_base64(filepath):
    """Read an image file and return a base64-encoded string."""
    with open(filepath, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")


def base64_to_image(b64_string):
    """Decode a base64 string to a PIL Image."""
    data = base64.b64decode(b64_string)
    return Image.open(BytesIO(data))


def crop_image(image_path, bbox, output_dir):
    """
    Crop a region from an image.
    bbox: dict with keys x, y, w, h (as fractions 0-1 of image dimensions)
    Returns: saved crop filename
    """
    img = Image.open(image_path)
    w, h = img.size

    left = int(bbox.get("x", 0) * w)
    top = int(bbox.get("y", 0) * h)
    right = int((bbox.get("x", 0) + bbox.get("w", 1)) * w)
    bottom = int((bbox.get("y", 0) + bbox.get("h", 1)) * h)

    # Clamp
    left = max(0, min(left, w))
    top = max(0, min(top, h))
    right = max(left + 1, min(right, w))
    bottom = max(top + 1, min(bottom, h))

    cropped = img.crop((left, top, right, bottom))
    filename = f"crop_{uuid.uuid4().hex}.png"
    cropped.save(os.path.join(output_dir, filename))
    return filename


def resize_image_for_upload(filepath, max_dim=2048):
    """Resize image so the largest dimension is <= max_dim. Returns base64."""
    img = Image.open(filepath)
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")
