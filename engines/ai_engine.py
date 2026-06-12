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

目前生成藍圖：
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
1. 整理或更新「生成藍圖」
2. 產生「本次圖片提示詞」
3. 讓後續圖片可以維持同一個主體、風格、場景或重要特徵
4. 使用者後續補充時，要更新原本生成藍圖，而不是重新開始

請用以下格式回答：

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

【本次圖片提示詞】
請生成一張......

【你可以再補充】
1. ...
2. ...
3. ...
"""
    else:
        task_rule = """
你的任務：
1. 把使用者模糊的需求整理成清楚方向
2. 優先告訴使用者現在該怎麼做
3. 如果資訊不足，只問最重要的 1 到 3 個問題
4. 使用者後續補充時，要把新內容加入原本需求中，而不是重新開始

請用以下格式回答：

我先幫你整理成這樣：

【目前理解】
...

【建議下一步】
1. ...
2. ...
3. ...

【你可以再補充】
1. ...
2. ...
3. ...
"""

    prompt = f"""
你是 AI 需求整理顧問。

目前模式：
{mode_display_name}

目前生成藍圖：
{character_profile}

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
3. 不要一次問太多問題
4. 回答不要太長
5. 用繁體中文
6. 語氣要像助理，不要像問卷
7. 如果已有生成藍圖，要優先保留原本設定，只加入使用者新補充的內容
"""

    response = chat(
        model=MODEL_NAME,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response["message"]["content"]


def extract_character_profile(reply):
    start_markers = [
        "【主體藍圖】",
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

    end = reply.find("【本次圖片提示詞】")

    if end == -1:
        return reply[start:].strip()

    return reply[start:end].strip()


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

    if mode_name == "image":
        new_profile = extract_character_profile(final_answer)

        if new_profile:
            updated_character_profile = new_profile

    return final_answer, updated_character_profile