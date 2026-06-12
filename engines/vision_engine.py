from ollama import chat

VISION_MODEL = "qwen2.5vl:7b"


def analyze_image(image_path):
    response = chat(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": """
請用繁體中文分析這張圖片，並整理成 Generation Blueprint。

請務必使用以下格式回答：

【主體藍圖】
- 主體類型：
- 主體名稱：
- 主體外觀：
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
- 構圖：
- 鏡頭角度：

【固定規則】
- 後續生成必須保持：
- 後續生成可以變化：
- 避免出現：

【完整提示詞】
請生成一張......
""",
                "images": [image_path]
            }
        ]
    )

    return response["message"]["content"]