from ollama import chat

MODEL_NAME = "qwen3"


def detect_intent(user_message):
    prompt = f"""
請判斷使用者需求最適合哪一種模式。

使用者訊息：
{user_message}

請只回答以下其中一個英文代碼，不要解釋：

image
automation
startup
clarify

判斷規則：
- 如果使用者想生成圖片、設計角色、車輛、場景、產品外觀，回答 image
- 如果使用者想自動化工作流程、Excel、報表、公司流程，回答 automation
- 如果使用者想創業、做產品、APP、商業模式，回答 startup
- 如果只是想法模糊、需要整理需求，回答 clarify
"""

    response = chat(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    result = response["message"]["content"].strip().lower()

    if "image" in result:
        return {
            "mode": "image",
            "blueprint": "image"
        }

    if "automation" in result:
        return {
            "mode": "consultant",
            "blueprint": "workflow"
        }

    if "startup" in result:
        return {
            "mode": "clarify",
            "blueprint": "startup"
        }

    return {
        "mode": "clarify",
        "blueprint": "general"
    }