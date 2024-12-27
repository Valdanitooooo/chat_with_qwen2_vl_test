# chat_with_qwen2_vl_test

## About

https://github.com/xorbitsai/inference/issues/2493

I use qwen2-vl model to understand the content of images, and I have found that images compressed by gradio have very good recognition effects, surpassing the original images. 
So I copied the [code for processing images in Gradio](https://github.com/gradio-app/gradio/blob/main/gradio/processing_utils.py) and made some modifications to test it, hoping to find the best practice for using the qwen2-vl model.

## Usage

### 0. Install necessary dependencies

```
pip install -r requirements.txt
```

### 1. Deploying the qwen2-vl model using vllm or xinference

If you are a beginner, you can refer to my deployment script in the `deploy` directory

1. Be sure to modify the volumes configuration in `deploy/docker-compose.yml` in order to find the correct model weight directory on your hard drive
2. Modify the parameters in `deploy/.env` to what you need
3. Run `docker compose up -d` in the `deploy` directory to start the vllm service
4. Then modify the API configuration in main.py
```
OPENAI_VISION_MODEL = 'Qwen2-VL-7B-Instruct'

openai_vision_client = OpenAI(
    base_url="http://xinference_host:9997/v1",
    api_key="xxx",
)
```

### 2. Modify parameters

Change the `prompt` and `image_paths` variables of the main method in main.py to what you want.


## Other effective methods derived from practice

### Rotate the image to the correct orientation based on the text direction

1. Using [RapidOrientation](https://github.com/RapidAI/RapidOrientation) to classify image orientation
2. Rotate the image based on the classification results (0 | 90 | 180 | 270)
3. Identify the processed image using qwen2-vl

```
import cv2
from PIL import Image
from rapid_orientation import RapidOrientation


def adjust_image_orientation(image_path):
    orientation_engine = RapidOrientation()
    img = cv2.imread(image_path)
    cls_result, _ = orientation_engine(img)
    rotation_angle = int(cls_result)
    print(rotation_angle)
    if rotation_angle == 0:
        return image_path
    image = Image.open(image_path)
    # Rotate image
    rotated_image = image.rotate(rotation_angle, expand=True)
    rotated_image.save(image_path)
    return image_path
```

### Extract main content from large-sized images to achieve the effect of reducing the size of the image

1. Deploy RMBG2.0 API service，More in https://github.com/valdanitooooo/RMBG2-docker
2. Remove the background of the image and only retain the main content
3. Crop off excess transparent background around the image
4. Identify the processed image using qwen2-vl

```
from pathlib import Path

import numpy as np
import requests
from PIL import Image

RMBG_API = 'http://xxx:9006/api/remove-bg'

## 抠图
def remove_bg(image_path, output_path):
    data = {}
    files = {"file": open(image_path, "rb")}
    response = requests.post(RMBG_API, data=data, files=files)
    if response.status_code == 200:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "wb") as f:
            f.write(response.content)
        output_file = remove_transparent_background(output_file, output_path)
        print(f"背景去除后的图片已保存到: {output_file}")
        return str(output_file)
    else:
        print(f"请求失败！状态码: {response.status_code}, 错误信息: {response.text}")
        return image_path

def remove_transparent_background(image_path, output_path, max_size=600):
    """
    裁剪掉抠图后周围多余的透明背景，并将其缩小到指定尺寸（长或宽不超过 max_size）。

    Args:
        image_path (str): 输入图片路径。
        output_path (str): 输出图片路径。
        max_size (int): 缩小后图片的最大边长（默认600px）。
    """
    # 打开图片并转换为 RGBA 模式
    img = Image.open(image_path).convert("RGBA")
    arr = np.array(img)

    # 获取 Alpha 通道
    alpha = arr[:, :, 3]

    # 找到非透明区域的边界
    non_transparent_coords = np.where(alpha > 0)
    top, left = np.min(non_transparent_coords[0]), np.min(non_transparent_coords[1])
    bottom, right = np.max(non_transparent_coords[0]), np.max(non_transparent_coords[1])

    # 裁剪图片
    cropped_arr = arr[top:bottom + 1, left:right + 1]
    cropped_img = Image.fromarray(cropped_arr, "RGBA")

    # 计算缩放比例，使裁剪后的图片的宽或高不超过 max_size
    width, height = cropped_img.size
    scale_factor = min(1.0, max_size / max(width, height))  # 确保缩放比例不超过 1.0（放大不考虑）
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    # 缩放图片
    resized_img = cropped_img.resize((new_width, new_height), resample=Image.Resampling.LANCZOS)

    # 保存结果
    resized_img.save(output_path)
    print(f"裁剪图片完成！已保存到: {output_path}")
    return output_path

```
