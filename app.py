from flask import Flask, render_template, request, jsonify
from engines.ai_engine import run_ai_round
from managers.project_manager import list_projects, load_project, save_project, delete_project
import os
from werkzeug.utils import secure_filename
from engines.vision_engine import analyze_image

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

conversation_history = ""
character_profile = ""
generation_blueprint = {}
uploaded_images = []


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/projects", methods=["GET"])
def get_projects():
    projects = list_projects()
    return jsonify({"projects": projects})

@app.route("/chat", methods=["POST"])
def chat_api():
    global conversation_history
    global character_profile

    data = request.get_json()

    mode = data.get("mode", "clarify")
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "請先輸入你的需求。"})

    conversation_history += f"\n使用者：{user_message}"

    reply, updated_character_profile = run_ai_round(
        mode,
        user_message,
        conversation_history,
        character_profile
    )

    character_profile = updated_character_profile
    conversation_history += f"\nAI顧問：{reply}"

    return jsonify({
        "reply": reply,
        "character_profile": character_profile
    })


@app.route("/reset", methods=["POST"])
def reset_chat():
    global conversation_history
    global character_profile
    global uploaded_images


    conversation_history = ""
    character_profile = ""
    uploaded_images = []
    
    return jsonify({"message": "對話已重置"})
@app.route("/load_project", methods=["POST"])
def load_project_api():
    global conversation_history
    global character_profile
    global uploaded_images

    data = request.get_json()
    project_name = data.get("project_name", "")

    project = load_project(project_name)

    if not project:
        return jsonify({"error": "找不到專案"})

    conversation_history = project.get("conversation_history", "")
    character_profile = project.get("character_profile", "")
    uploaded_images = project.get("uploaded_images", [])

    return jsonify({
        "project_name": project_name,
        "conversation_history": conversation_history,
        "character_profile": character_profile,
        "uploaded_images": uploaded_images
    })
@app.route("/save_project", methods=["POST"])
def save_project_api():
    global conversation_history
    global character_profile
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
        character_profile,
        uploaded_images
    )

    return jsonify({
        "message": "專案已儲存",
        "project_name": project_name
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

@app.route("/upload_images", methods=["POST"])
def upload_images():
    global uploaded_images

    files = request.files.getlist("images")

    if not files:
        return jsonify({"error": "沒有收到圖片"})

    image_urls = []

    for file in files:
        if file.filename == "":
            continue

        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        image_url = f"/static/uploads/{filename}"
        image_urls.append(image_url)

        if image_url not in uploaded_images:
            uploaded_images.append(image_url)

    return jsonify({
        "message": "圖片上傳成功",
        "images": uploaded_images
    })

@app.route("/analyze_image", methods=["POST"])
def analyze_image_api():
    global character_profile
    global conversation_history

    data = request.get_json()
    image_url = data.get("image_url", "")

    if not image_url:
        return jsonify({"error": "沒有收到圖片路徑"})

    image_path = image_url.lstrip("/")

    result = analyze_image(image_path)

    generation_blueprint = {
        "subject_blueprint": result,
        "style_blueprint": "",
        "scene_blueprint": "",
        "fixed_rules": ""
    }
    conversation_history += f"\nVision分析：{result}"

    return jsonify({
        "analysis": result,
        "character_profile": character_profile
    })

@app.route("/generate_prompt", methods=["POST"])
def generate_prompt_api():
    global character_profile
    global conversation_history

    if not character_profile:
        return jsonify({"error": "目前沒有生成藍圖，請先輸入需求或分析圖片。"})

    from ollama import chat

    response = chat(
        model="qwen3",
        messages=[
            {
                "role": "user",
                "content": f"""
請根據以下生成藍圖，產生一份完整圖片生成提示詞。

生成藍圖：
{character_profile}

請輸出格式：

【完整提示詞】
...

【負面提示詞】
...

【適合模型】
- Midjourney
- Flux
- SDXL
- GPT Image

回答規則：
1. 用繁體中文
2. 提示詞要完整
3. 要保留生成藍圖中的固定特徵
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
if __name__ == "__main__":
    app.run(debug=True)