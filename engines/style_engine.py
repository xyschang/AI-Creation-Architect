import os
import base64
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

STYLE_PROMPT = """
請分析這張圖片的視覺風格，用以下 JSON 格式回答，不要加任何多餘說明，只輸出 JSON：

{
  "color_tone": "色調描述（例如：冷色調、暖色調、高對比、低飽和）",
  "visual_style": "視覺風格（例如：寫實攝影、動漫插畫、油畫、賽博龐克）",
  "lighting": "光線描述（例如：自然光、逆光、霓虹燈、柔光）",
  "composition": "構圖方式（例如：中心構圖、三分法、對稱）",
  "atmosphere": "整體氛圍（例如：神秘、溫馨、壓迫感、夢幻）",
  "style_keywords": "5個英文關鍵字，用逗號分隔，適合放進圖片生成提示詞"
}
"""


def _get_media_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mapping.get(ext, "image/jpeg")


def analyze_style(image_path: str) -> dict:
    """
    分析圖片風格，回傳 dict：
    {
        "raw": "完整 JSON 字串",
        "color_tone": ...,
        "visual_style": ...,
        "lighting": ...,
        "composition": ...,
        "atmosphere": ...,
        "style_keywords": ...
    }
    """
    if not os.path.exists(image_path):
        return {"error": f"找不到圖片：{image_path}"}

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    media_type = _get_media_type(image_path)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
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
                        {"type": "text", "text": STYLE_PROMPT}
                    ],
                }
            ],
        )

        raw = message.content[0].text.strip()

        # 解析 JSON
        import json
        # 去掉可能的 markdown code block
        clean = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
        parsed["raw"] = raw
        return parsed

    except Exception as e:
        return {"error": str(e), "raw": ""}


def build_style_prompt(styles: list) -> str:
    """
    把多筆風格資料合併成一段英文生成提示詞用的風格描述
    """
    if not styles:
        return ""

    all_keywords = []
    visual_styles = []
    color_tones = []
    lightings = []
    atmospheres = []

    for s in styles:
        if s.get("style_keywords"):
            all_keywords.extend([k.strip() for k in s["style_keywords"].split(",")])
        if s.get("visual_style"):
            visual_styles.append(s["visual_style"])
        if s.get("color_tone"):
            color_tones.append(s["color_tone"])
        if s.get("lighting"):
            lightings.append(s["lighting"])
        if s.get("atmosphere"):
            atmospheres.append(s["atmosphere"])

    # 去重
    all_keywords = list(dict.fromkeys(all_keywords))

    summary = f"""
風格關鍵字：{', '.join(all_keywords[:10])}
視覺風格：{' / '.join(list(dict.fromkeys(visual_styles)))}
色調：{' / '.join(list(dict.fromkeys(color_tones)))}
光線：{' / '.join(list(dict.fromkeys(lightings)))}
氛圍：{' / '.join(list(dict.fromkeys(atmospheres)))}
""".strip()

    return summary
