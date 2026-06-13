import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)


def ask_model(prompt: str) -> str:
    """
    傳入 prompt 字串，回傳 Claude 的回答文字。
    """
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text

    except anthropic.AuthenticationError:
        return "❌ API Key 無效，請檢查 .env 的 ANTHROPIC_API_KEY"

    except anthropic.RateLimitError:
        return "❌ 超過使用限制，請稍後再試"

    except Exception as e:
        return f"❌ Claude API 錯誤：{str(e)}"
