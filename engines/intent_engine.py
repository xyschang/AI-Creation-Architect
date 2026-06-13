from engines.providers.provider_factory import get_ai_provider

ask_model = get_ai_provider()


def detect_intent(user_message):
    prompt = f"""
請判斷使用者需求最適合哪一種模式。

使用者訊息：
{user_message}

請只回答以下其中一個英文代碼，不要解釋，不要加任何標點符號：

image
automation
startup
clarify

判斷規則：
- 如果使用者想生成圖片、設計角色、車輛、場景、產品外觀，回答 image
- 如果使用者想自動化工作流程、Excel、報表、公司流程、串接系統，回答 automation
- 如果使用者想創業、做產品、APP、商業模式，回答 startup
- 如果只是想法模糊、需要整理需求，回答 clarify
"""

    try:
        answer = ask_model(prompt).strip().lower()

        # 只取第一個字，防止 AI 多輸出東西
        for mode in ["image", "automation", "startup", "clarify"]:
            if mode in answer:
                blueprint_map = {
                    "image": "image",
                    "automation": "workflow",
                    "startup": "startup",
                    "clarify": "general"
                }
                return {
                    "mode": "image" if mode == "image" else
                            "consultant" if mode == "automation" else
                            "consultant" if mode == "startup" else
                            "clarify",
                    "blueprint": blueprint_map[mode]
                }
    except Exception:
        pass

    # 預設 fallback
    return {"mode": "clarify", "blueprint": "general"}
