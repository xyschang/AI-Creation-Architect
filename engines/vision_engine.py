import os
import base64
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

PROMPT = """
請用繁體中文分析這張圖片，並整理成 Generation Blueprint。

重點：
1. 請先判斷誰是主要主體，不要誤把背景或人物當主體。
2. 如果圖片主要是車，就不要把駕駛者或人物設為主要主體。
3. 請分析主體佔畫面比例、構圖、角度與鏡頭距離。
4. 目標是讓之後生成圖片時，能盡量接近原圖的主體、位置、角度與構圖。

請務必使用以下格式回答：

【主體優先級】
- 主要主體：
- 主體類型：
- 主體權重：
- 次要主體：
- 背景權重：
- 是否有人物：
- 禁止替換主體：

【主體藍圖】
- 主體名稱：
- 主體外觀：
- 主體顏色：
- 重要特徵：
- 不要改變的部分：

【風格藍圖】
- 視覺風格：
- 色調：
- 光線：
- 質感：
- 整體氛圍：

【場景藍圖】
- 場景位置：
- 背景元素：
- 時間感：
- 場景比例：

【構圖藍圖】
- 主體位置：
- 主體朝向：
- 鏡頭角度：
- 拍攝高度：
- 拍攝距離：
- 畫面比例：
- 主體佔畫面比例：
- 景深效果：

【攝影分析】
- 攝影類型：
- 鏡頭類型：
- 焦段推測：
- 視角：
- 攝影高度：
- 主體朝向：
- 主體佔畫面比例：
- 是否裁切主體：
- 攝影目的：

【固定規則】
- 後續生成必須保持：
- 後續生成可以變化：
- 避免出現：

【完整提示詞】
請生成一張......
"""


def _get_media_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    mapping = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".gif":  "image/gif",
        ".webp": "image/webp",
    }
    return mapping.get(ext, "image/jpeg")


def analyze_image(image_path: str) -> str:
    """
    傳入圖片路徑（相對或絕對），用 Claude Vision 分析並回傳 blueprint 文字。
    """
    if not os.path.exists(image_path):
        return f"❌ 找不到圖片：{image_path}"

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    media_type = _get_media_type(image_path)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": PROMPT
                        }
                    ],
                }
            ],
        )
        return message.content[0].text

    except anthropic.AuthenticationError:
        return "❌ API Key 無效，請檢查 .env 的 ANTHROPIC_API_KEY"

    except anthropic.RateLimitError:
        return "❌ 超過使用限制，請稍後再試"

    except Exception as e:
        return f"❌ Claude Vision 錯誤：{str(e)}"
