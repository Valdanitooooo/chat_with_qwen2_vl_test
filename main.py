import asyncio
from typing import List

from openai import OpenAI

from image_utils import format_image, convert_image_to_base64

OPENAI_VISION_MODEL = 'Qwen2-VL-7B-Instruct'

openai_vision_client = OpenAI(
    base_url="http://xinference_host:9997/v1",
    api_key="xxx",
)


async def image_sense_qa(prompt: str, image_paths: List[str], compress: bool = True):
    """Identify image content and answer user questions."""
    content = [{"type": "text", "text": f"{prompt}"}]
    for image_path in image_paths:
        if compress:
            image_path = format_image(image_path)
        print(f'image_path: {image_path}')
        b64_img = convert_image_to_base64(image_path)
        image_message = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64_img}",
            },
        }
        content.append(image_message)
    response = openai_vision_client.chat.completions.create(
        model=OPENAI_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": content,
            }
        ],
        stream=True,
        max_tokens=512,
        temperature=1,
    )
    for chunk in response:
        print(chunk.choices[0].delta.content or "", end="")


if __name__ == '__main__':
    prompt = '准确识别图中全部文字内容'
    # prompt = 'Identify all text content in the image'
    image_paths = ["/Users/valdanito/Downloads/test222.jpg"]
    asyncio.run(image_sense_qa(prompt, image_paths, False))
    asyncio.run(image_sense_qa(prompt, image_paths, True))
