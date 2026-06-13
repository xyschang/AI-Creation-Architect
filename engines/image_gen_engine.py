import os
import replicate
from dotenv import load_dotenv

load_dotenv()

# 設定 Replicate API Token
os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPLICATE_API_TOKEN", "")


def generate_image(prompt: str, negative_prompt: str = "") -> str:
    """
    傳入英文提示詞，用 FLUX.1 生成圖片，回傳圖片 URL。
    """
    try:
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "num_outputs": 1,
                "aspect_ratio": "1:1",
                "output_format": "webp",
                "output_quality": 90
            }
        )

        # output 是 list，取第一張
        if output and len(output) > 0:
            return str(output[0])

        return ""

    except Exception as e:
        return f"ERROR:{str(e)}"
