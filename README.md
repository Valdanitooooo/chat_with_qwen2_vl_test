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


