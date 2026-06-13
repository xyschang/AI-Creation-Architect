from flask import Flask, render_template, request, jsonify
from engines.ai_engine import run_ai_round
from engines.intent_engine import detect_intent
from engines.vision_engine import analyze_image
from managers.project_manager import (
    list_projects,
    load_project,
    save_project,
    delete_project
)
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

conversation_history = ""

image_blueprint = ""
workflow_blueprint = ""
startup_blueprint = ""

uploaded_images = []


def get_current_blueprint(blueprint_type):
    if blueprint_type == "image":
        return image_blueprint
    elif blueprint_type == "workflow":
        return workflow_blueprint
    elif blueprint_type == "startup":
        return startup_blueprint
    return ""


def update_blueprint(blueprint_type, new_blueprint):
    global image_blueprint
    global workflow_blueprint
    global startup_blueprint

    if blueprint_type == "image":
        image_blueprint = new_blueprint
    elif blueprint_type == "workflow":
        workflow_blueprint = new_blueprint
    elif blueprint_type == "startup":
        startup_blueprint = new_blueprint


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat_api():
    global conversation_history

    data = request.get_json()

    mode = data.get("mode", "auto")
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "請先輸入你的需求。"})

    blueprint_type = "general"

    if mode == "auto":
        intent = detect_intent(user_message)
        mode = intent["mode"]
        blueprint_type = intent["blueprint"]
    else:
        if mode == "image":
            blueprint_type = "image"
        elif mode == "consultant":
            blueprint_type = "workflow"
        elif mode == "clarify":
            blueprint_type = "general"

    current_blueprint = get_current_blueprint(blueprint_type)

    conversation_history += f"\n使用者：{user_message}"

    reply, updated_blueprint = run_ai_round(
        mode,
        user_message,
        conversation_history,
        current_blueprint
    )

    if blueprint_type in ["image", "workflow", "startup"]:
        update_blueprint(blueprint_type, updated_blueprint)

    conversation_history += f"\nAI顧問：{reply}"

    return jsonify({
        "reply": reply,
        "blueprint": updated_blueprint,
        "blueprint_type": blueprint_type,
        "detected_mode": mode
    })


@app.route("/upload_images", methods=["POST"])
def upload_images():
    global uploaded_images

    files = request.files.getlist("images")

    if not files:
        return jsonify({"error": "沒有收到圖片"})

    for file in files:
        if file.filename == "":
            continue

        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        image_url = f"/static/uploads/{filename}"

        if image_url not in uploaded_images:
            uploaded_images.append(image_url)

    return jsonify({
        "message": "圖片上傳成功",
        "images": uploaded_images
    })


@app.route("/analyze_image", methods=["POST"])
def analyze_image_api():
    global conversation_history
    global image_blueprint

    data = request.get_json()
    image_url = data.get("image_url", "")

    if not image_url:
        return jsonify({"error": "沒有收到圖片路徑"})

    image_path = image_url.lstrip("/")

    result = analyze_image(image_path)

    image_blueprint = result
    conversation_history += f"\nVision分析：{result}"

    return jsonify({
        "analysis": result,
        "blueprint": image_blueprint,
        "blueprint_type": "image"
    })


@app.route("/generate_prompt", methods=["POST"])
def generate_prompt_api():
    global image_blueprint
    global conversation_history

    if not image_blueprint:
        return jsonify({"error": "目前沒有生成藍圖，請先輸入需求或分析圖片。"})

    from ollama import chat

    response = chat(
        model="qwen3",
        messages=[
            {
                "role": "user",
                "content": f"""
請根據以下 Generation Blueprint，產生一份可直接用於 AI 圖片生成模型的完整提示詞。

Generation Blueprint：
{image_blueprint}

請特別遵守：
1. 必須優先保留【主體優先級】中的主要主體。
2. 不可以把次要主體或背景元素變成主要主體。
3. 如果標示「是否有人物：否」，提示詞中必須明確寫出 no people, no human, no driver。
4. 如果標示「禁止替換主體：是」，提示詞中必須強調 primary subject must remain the same。
5. 必須把【構圖藍圖】中的主體位置、鏡頭角度、拍攝高度、拍攝距離、畫面比例寫進提示詞。
6. 提示詞要完整，不要只寫摘要。

請輸出格式：

【完整提示詞】
請生成一張......

【英文提示詞】
...

【負面提示詞】
...

【構圖控制重點】
- 主體位置：
- 鏡頭角度：
- 拍攝高度：
- 拍攝距離：
- 畫面比例：
- 主體佔畫面比例：

【適合模型】
- Midjourney
- Flux
- SDXL
- GPT Image

回答規則：
1. 用繁體中文
2. 英文提示詞要可以直接拿去生成圖片
3. 要保留主要主體，不要擅自加入人物
4. 不要產生圖片，只產生提示詞
"""
            }
        ]
    )

    result = response["message"]["content"]

    conversation_history += f"\nAI生成完整提示詞：{result}"

    return jsonify({
        "prompt": result
    })


@app.route("/projects", methods=["GET"])
def get_projects():
    projects = list_projects()
    return jsonify({"projects": projects})


@app.route("/save_project", methods=["POST"])
def save_project_api():
    global conversation_history
    global image_blueprint
    global workflow_blueprint
    global startup_blueprint
    global uploaded_images

    data = request.get_json()
    project_name = data.get("project_name", "").strip()

    if not project_name:
        return jsonify({"error": "請輸入專案名稱"})

    valid_images = []

    for image_url in uploaded_images:
        image_path = image_url.lstrip("/")

        if os.path.exists(image_path):
            valid_images.append(image_url)

    uploaded_images = valid_images

    save_project(
        project_name,
        conversation_history,
        image_blueprint,
        workflow_blueprint,
        startup_blueprint,
        uploaded_images
    )

    return jsonify({
        "message": "專案已儲存",
        "project_name": project_name
    })


@app.route("/load_project", methods=["POST"])
def load_project_api():
    global conversation_history
    global image_blueprint
    global workflow_blueprint
    global startup_blueprint
    global uploaded_images

    data = request.get_json()
    project_name = data.get("project_name", "")

    project = load_project(project_name)

    if not project:
        return jsonify({"error": "找不到專案"})

    conversation_history = project.get("conversation_history", "")

    image_blueprint = project.get("image_blueprint", project.get("character_profile", ""))
    workflow_blueprint = project.get("workflow_blueprint", "")
    startup_blueprint = project.get("startup_blueprint", "")

    uploaded_images = project.get("uploaded_images", [])

    return jsonify({
        "project_name": project_name,
        "conversation_history": conversation_history,
        "image_blueprint": image_blueprint,
        "workflow_blueprint": workflow_blueprint,
        "startup_blueprint": startup_blueprint,
        "uploaded_images": uploaded_images
    })


@app.route("/delete_project", methods=["POST"])
def delete_project_api():
    data = request.get_json()
    project_name = data.get("project_name", "").strip()

    if not project_name:
        return jsonify({"error": "請提供專案名稱"})

    success = delete_project(project_name)

    if not success:
        return jsonify({"error": "找不到專案"})

    return jsonify({
        "message": "專案已刪除",
        "project_name": project_name
    })


@app.route("/reset", methods=["POST"])
def reset_chat():
    global conversation_history
    global image_blueprint
    global workflow_blueprint
    global startup_blueprint
    global uploaded_images

    conversation_history = ""
    image_blueprint = ""
    workflow_blueprint = ""
    startup_blueprint = ""
    uploaded_images = []

    return jsonify({"message": "對話已重置"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )