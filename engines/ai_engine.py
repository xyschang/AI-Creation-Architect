from ollama import chat
from ai_roles import consultant_roles, clarify_roles, image_prompt_roles

MODEL_NAME = "qwen3"


def get_roles(mode_name):
    if mode_name == "consultant":
        return "AI 顧問模式", consultant_roles

    if mode_name == "clarify":
        return "需求澄清模式", clarify_roles

    if mode_name == "image":
        return "圖片提示詞模式", image_prompt_roles

    return "需求澄清模式", clarify_roles


def ask_ai(role_name, role_prompt, user_message, conversation_history, previous_answers="", character_profile=""):
    prompt = f"""
你是{role_name}

你的任務：
{role_prompt}

目前藍圖：
{character_profile}

歷史對話：
{conversation_history}

目前使用者訊息：
{user_message}

前面其他 AI 的內部分析：
{previous_answers}

回答規則：
1. 請用繁體中文
2. 這是內部分析，不要寫太多廢話
3. 重點是幫助最後整合 AI 判斷
"""

    response = chat(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response["message"]["content"]


def summarize_answers(mode_display_name, user_message, conversation_history, all_answers, character_profile=""):

    if mode_display_name == "圖片提示詞模式":
        task_rule = """
你的任務：
請把圖片創作需求整理成 Image Generation Blueprint。

請用以下格式回答：
【主體優先級】
- 主要主體：
- 主體類型：
- 主體權重：
- 次要主體：
- 背景權重：
- 是否有人物：
- 禁止替換主體：

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

【構圖藍圖】
- 主體位置：
- 主體朝向：
- 鏡頭角度：
- 拍攝高度：
- 拍攝距離：
- 畫面比例：
- 主體佔畫面比例：
- 景深效果：

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

【本次圖片提示詞】
請生成一張......

【你可以再補充】
1. ...
2. ...
3. ...
"""

    elif mode_display_name == "AI 顧問模式":
        task_rule = """
你的任務：
請把自動化、系統開發或工作流程需求整理成 Workflow Blueprint。

請用以下格式回答：

【流程藍圖】
- 目前流程：
- 主要痛點：
- 重複性工作：
- 資料來源：
- 輸出結果：

【自動化藍圖】
- 可自動化步驟：
- 推薦工具：
- 技術方向：
- 第一版 MVP：

【風險與限制】
- 可能風險：
- 缺少資訊：
- 需要確認的問題：

【建議下一步】
1. ...
2. ...
3. ...
"""

    else:
        task_rule = """
你的任務：
請把使用者的模糊想法整理成需求藍圖。

如果使用者是在講創業、APP、產品或服務，請偏向 Startup Blueprint。
如果只是一般模糊需求，請偏向一般需求整理。

請用以下格式回答：

【需求藍圖】
- 目標：
- 使用者/對象：
- 核心問題：
- 想達成的結果：

【解決方案藍圖】
- 可能方案：
- 核心功能：
- 第一版 MVP：
- 差異化特色：

【風險與限制】
- 可能風險：
- 缺少資訊：
- 需要確認的問題：

【建議下一步】
1. ...
2. ...
3. ...
"""

    prompt = f"""
你是 AI Creation Architect。

目前模式：
{mode_display_name}

目前藍圖：
{character_profile}
請注意：
如果目前藍圖已有內容，請以目前藍圖為主，不要重新開始。
使用者最新訊息通常是在補充或修改原本需求。

歷史對話：
{conversation_history}

使用者最新訊息：
{user_message}

以下是多位 AI 的內部分析：
{all_answers}

{task_rule}

回答規則：
1. 不要提到有多個 AI
2. 不要顯示內部分析過程
3. 回答不要太長
4. 用繁體中文
5. 語氣要像助理，不要像問卷
6. 如果目前藍圖不是空的，請把它當成主要資料來源
7. 使用者最新訊息只代表新增、修改或刪除某些內容
8. 不要重新建立整份藍圖
9. 請保留原本藍圖中沒有被使用者明確修改的部分
"""

    response = chat(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response["message"]["content"]


def extract_blueprint(reply):
    start_markers = [
        "【主體藍圖】",
        "【流程藍圖】",
        "【需求藍圖】",
        "【生成藍圖】",
        "【角色卡】"
    ]

    start = -1

    for marker in start_markers:
        start = reply.find(marker)
        if start != -1:
            break

    if start == -1:
        return ""

    end_markers = [
        "【本次圖片提示詞】",
        "【建議下一步】",
        "【你可以再補充】"
    ]

    end_positions = []

    for marker in end_markers:
        pos = reply.find(marker)
        if pos != -1 and pos > start:
            end_positions.append(pos)

    if end_positions:
        end = min(end_positions)
        return reply[start:end].strip()

    return reply[start:].strip()


def run_ai_round(mode_name, user_message, conversation_history, character_profile=""):
    mode_display_name, selected_roles = get_roles(mode_name)

    all_answers = ""

    for role_name, role_prompt in selected_roles.items():
        answer = ask_ai(
            role_name,
            role_prompt,
            user_message,
            conversation_history,
            all_answers,
            character_profile
        )

        all_answers += f"\n\n【{role_name}】\n{answer}"

    final_answer = summarize_answers(
        mode_display_name,
        user_message,
        conversation_history,
        all_answers,
        character_profile
    )

    updated_character_profile = character_profile

    new_blueprint = extract_blueprint(final_answer)

    if new_blueprint:
        updated_character_profile = new_blueprint

    return final_answer, updated_character_profile