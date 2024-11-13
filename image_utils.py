import base64
import hashlib
import os
import uuid
import warnings
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageSequence, PngImagePlugin, ImageOps

# Modified from: https://github.com/gradio-app/gradio/blob/main/gradio/processing_utils.py

CACHE_DIR = '/tmp'
HASH_SEED_PATH = f'{CACHE_DIR}/hash_seed.txt'


def get_pil_exif_bytes(pil_image):
    if "exif" in pil_image.info:
        return pil_image.info["exif"]


def get_pil_metadata(pil_image):
    # Copy any text-only metadata
    metadata = PngImagePlugin.PngInfo()
    for key, value in pil_image.info.items():
        if isinstance(key, str) and isinstance(value, str):
            metadata.add_text(key, value)

    return metadata


def encode_pil_to_bytes(pil_image, format="png"):
    with BytesIO() as output_bytes:
        if format.lower() == "gif":
            frames = [frame.copy() for frame in ImageSequence.Iterator(pil_image)]
            frames[0].save(
                output_bytes,
                format=format,
                save_all=True,
                append_images=frames[1:],
                loop=0,
            )
        else:
            if format.lower() == "png":
                params = {"pnginfo": get_pil_metadata(pil_image)}
            else:
                exif = get_pil_exif_bytes(pil_image)
                params = {"exif": exif} if exif else {}
            pil_image.save(output_bytes, format, **params)
        return output_bytes.getvalue()


def get_hash_seed() -> str:
    try:
        if os.path.exists(HASH_SEED_PATH):
            with open(HASH_SEED_PATH) as j:
                return j.read().strip()
        else:
            with open(HASH_SEED_PATH, "w") as j:
                seed = uuid.uuid4().hex
                j.write(seed)
                return seed
    except Exception:
        return uuid.uuid4().hex


hash_seed = get_hash_seed().encode("utf-8")


def hash_bytes(bytes: bytes):
    sha = hashlib.sha256()
    sha.update(hash_seed)
    sha.update(bytes)
    return sha.hexdigest()


def save_pil_to_cache(
        img: Image.Image,
        cache_dir: str,
        name: str = "image",
        format: str = "webp",
) -> str:
    bytes_data = encode_pil_to_bytes(img, format)
    temp_dir = Path(cache_dir) / hash_bytes(bytes_data)
    temp_dir.mkdir(exist_ok=True, parents=True)
    filename = str((temp_dir / f"{name}.{format}").resolve())
    (temp_dir / f"{name}.{format}").resolve().write_bytes(bytes_data)
    return filename


# 对分辨率较大的图片进行压缩，提升识别效果
# 仅对部分图片有效，对那种图片很大，但是要识别的内容在图片中占比很小的情况会起负面效果
def resize_image(input_image):
    width, height = input_image.size
    max_size = 500

    if width > max_size or height > max_size:
        if width > height:
            new_width = max_size
            new_height = int(max_size * height / width)
        else:
            new_height = max_size
            new_width = int(max_size * width / height)

        resized_image = input_image.resize((new_width, new_height), Image.LANCZOS)
        return resized_image
    return input_image


def format_image(
        image_path: str,
        cache_dir: str = CACHE_DIR,
        resize: bool = True,
) -> Image.Image | str | None:
    if image_path.startswith("http://") or image_path.startswith("https://"):
        image_obj = Image.open(requests.get(image_path, stream=True).raw)
    elif image_path.startswith("file://"):
        image_obj = Image.open(image_path[7:])
    elif image_path.startswith("data:image"):
        if "base64," in image_path:
            _, base64_data = image_path.split("base64,", 1)
            data = base64.b64decode(base64_data)
            image_obj = Image.open(BytesIO(data))
    else:
        image_obj = Image.open(image_path)
    if image_obj is None:
        raise ValueError(
            f"Unrecognized image input, support local path, http url, base64 and PIL.Image, got {image_path}")

    image_name_arr = os.path.basename(image_path).split(".")
    image_name = image_name_arr[0]
    image_ext = image_name_arr[1]

    # 把 png 转成 jpg 提升识别效果
    if "png" == image_ext:
        rgb_img = image_obj.convert("RGB")
        image_path = f"{CACHE_DIR}/{image_name}.jpg"
        rgb_img.save(image_path)
        image_ext = "jpg"
        image_obj = Image.open(f"{CACHE_DIR}/{image_name}.jpg")

    if resize:
        image_obj = resize_image(image_obj)

    exif = image_obj.getexif()
    # 274 is the code for image rotation and 1 means "correct orientation"
    if exif.get(274, 1) != 1 and hasattr(ImageOps, "exif_transpose"):
        try:
            image_obj = ImageOps.exif_transpose(image_obj)
        except Exception:
            warnings.warn(
                f"Failed to transpose image {image_path} based on EXIF data."
            )

    if image_ext in ["jpg", "jpeg"]:
        image_ext = "jpeg"
    try:
        path = save_pil_to_cache(
            image_obj, cache_dir=cache_dir, name=image_name, format=image_ext
        )
    # Catch error if format is not supported by PIL
    except (KeyError, ValueError):
        path = save_pil_to_cache(
            image_obj,
            cache_dir=cache_dir,
            name=image_name,
            format="png",  # type: ignore
        )
    return path


def convert_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
