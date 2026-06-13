from engines.ai_roles import consultant_roles, clarify_roles, image_prompt_roles, startup_roles
from engines.providers.provider_factory import get_ai_provider

ask_model = get_ai_provider()


def get_roles(mode_name):
    if mode_name == "consultant":
        return "AI 顧問模式", consultant_roles
    if mode_name == "clarify":
        return "需求澄清模式", clarify_roles
    if mode_name == "image":
        return "圖片提示詞模式", image_prompt_roles
    if mode_name == "startup":
        return "創業藍圖模式", startup_roles
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
    return ask_model(prompt)


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
- 鏡頭角度：
- 拍攝距離：
- 景深效果：

【場景藍圖】
- 場景位置：
- 背景元素：
- 時間感：

【固定規則】
- 後續生成必須保持：
- 後續生成可以變化：
- 避免出現：

【本次圖片提示詞】
請生成一張......

【建議補充】
1. ...
2. ...
"""

    elif mode_display_name == "AI 顧問模式":
        task_rule = """
你的任務：
請把自動化、系統開發或工作流程需求整理成 Workflow Blueprint。
同時輸出一份可直接使用的自動化流程 JSON（n8n 格式）。

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

【n8n 流程設定】
```json
{
  "nodes": [
    {
      "name": "觸發條件",
      "type": "n8n-nodes-base.webhook",
      "parameters": {}
    }
  ],
  "connections": {}
}
```

【風險與限制】
- 可能風險：
- 缺少資訊：
- 需要確認的問題：

【建議下一步】
1. ...
2. ...
3. ...
"""

    elif mode_display_name == "創業藍圖模式":
        task_rule = """
你的任務：
請把創業或產品想法整理成完整的 Startup Blueprint。

請用以下格式回答：

【需求藍圖】
- 目標客群：
- 核心痛點：
- 現有解決方案的缺點：

【產品藍圖】
- 核心功能：
- MVP 範圍（第一版只做什麼）：
- 使用者旅程：

【商業藍圖】
- 獲利模式：
- 定價策略：
- 成長路徑：

【風險藍圖】
- 最大風險：
- 需要驗證的假設：
- 資源缺口：

【建議下一步】
1. ...
2. ...
3. ...
"""

    else:
        task_rule = """
你的任務：
主動引導使用者把模糊想法說清楚。

請用以下格式回答：

【我理解你的需求是】
一句話總結你理解到的需求

【目前最需要釐清的是】
提出最重要的一個問題，幫助使用者補充需求

【如果你的目標是...，我建議】
根據可能的方向給出初步建議

【你可以這樣告訴我】
給出 2-3 個具體的描述範例，讓使用者知道怎麼說更清楚
"""

    prompt = f"""
你是 AI Creation Architect。

目前模式：{mode_display_name}

目前藍圖：
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
3. 用繁體中文
4. 語氣像助理，不像問卷
5. 如果目前藍圖不是空的，以它為主要資料來源
6. 保留原本藍圖中沒被明確修改的部分
"""

    return ask_model(prompt)


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
        "【建議補充】",
        "【你可以這樣告訴我】"
    ]

    end_positions = []
    for marker in end_markers:
        pos = reply.find(marker)
        if pos != -1 and pos > start:
            end_positions.append(pos)

    if end_positions:
        return reply[start:min(end_positions)].strip()

    return reply[start:].strip()


def run_ai_round(mode_name, user_message, conversation_history, character_profile=""):
    mode_display_name, selected_roles = get_roles(mode_name)

    all_answers = ""
    for role_name, role_prompt in selected_roles.items():
        answer = ask_ai(
            role_name, role_prompt,
            user_message, conversation_history,
            all_answers, character_profile
        )
        all_answers += f"\n\n【{role_name}】\n{answer}"

    final_answer = summarize_answers(
        mode_display_name, user_message,
        conversation_history, all_answers, character_profile
    )

    updated_character_profile = character_profile
    new_blueprint = extract_blueprint(final_answer)
    if new_blueprint:
        updated_character_profile = new_blueprint

    return final_answer, updated_character_profile
