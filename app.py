from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from engines.ai_engine import run_ai_round
from engines.intent_engine import detect_intent
from engines.vision_engine import analyze_image
from engines.image_gen_engine import generate_image
from engines.style_engine import analyze_style, build_style_prompt
from managers.project_manager import (
    list_projects, load_project, save_project, delete_project
)
from db import init_db, save_style, get_styles, delete_style, save_generated_image, get_generated_images
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()

conversation_history = ""
image_blueprint = ""
workflow_blueprint = ""
startup_blueprint = ""
uploaded_images = []
current_project = ""


def get_current_blueprint(blueprint_type):
    if blueprint_type == "image": return image_blueprint
    elif blueprint_type == "workflow": return workflow_blueprint
    elif blueprint_type == "startup": return startup_blueprint
    return ""


def update_blueprint(blueprint_type, new_blueprint):
    global image_blueprint, workflow_blueprint, startup_blueprint
    if blueprint_type == "image": image_blueprint = new_blueprint
    elif blueprint_type == "workflow": workflow_blueprint = new_blueprint
    elif blueprint_type == "startup": startup_blueprint = new_blueprint


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
        # 安全處理 detect_intent 可能回傳 None
        try:
            intent = detect_intent(user_message)
            if intent and isinstance(intent, dict):
                mode = intent.get("mode", "clarify")
                blueprint_type = intent.get("blueprint", "general")
            else:
                mode = "clarify"
                blueprint_type = "general"
        except Exception:
            mode = "clarify"
            blueprint_type = "general"
    else:
        if mode == "image": blueprint_type = "image"
        elif mode == "consultant": blueprint_type = "workflow"
        elif mode == "clarify": blueprint_type = "general"

    current_blueprint = get_current_blueprint(blueprint_type)
    conversation_history += f"\n使用者：{user_message}"

    reply, updated_blueprint = run_ai_round(
        mode, user_message, conversation_history, current_blueprint
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



@app.route("/chat_stream", methods=["POST"])
def chat_stream_api():
    global conversation_history
    data = request.get_json()
    mode = data.get("mode", "auto")
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "請先輸入你的需求。"})

    blueprint_type = "general"

    if mode == "auto":
        try:
            intent = detect_intent(user_message)
            if intent and isinstance(intent, dict):
                mode = intent.get("mode", "clarify")
                blueprint_type = intent.get("blueprint", "general")
            else:
                mode = "clarify"
                blueprint_type = "general"
        except Exception:
            mode = "clarify"
            blueprint_type = "general"
    else:
        if mode == "image": blueprint_type = "image"
        elif mode == "consultant": blueprint_type = "workflow"
        elif mode == "clarify": blueprint_type = "general"

    current_blueprint = get_current_blueprint(blueprint_type)
    conversation_history += f"\n使用者：{user_message}"

    import anthropic
    import json as json_mod

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    from engines.ai_roles import consultant_roles, clarify_roles, image_prompt_roles, startup_roles

    role_map = {
        "consultant": ("AI 顧問模式", consultant_roles),
        "clarify": ("需求澄清模式", clarify_roles),
        "image": ("圖片提示詞模式", image_prompt_roles),
        "startup": ("創業藍圖模式", startup_roles),
    }
    mode_display_name, _ = role_map.get(mode, ("需求澄清模式", clarify_roles))

    system_prompt = f"""你是 AI Creation Architect。
目前模式：{mode_display_name}
目前藍圖：{current_blueprint}
回答規則：用繁體中文，語氣像助理，直接回答不要廢話。"""

    def generate():
        full_reply = ""
        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"歷史對話：{conversation_history}\n\n使用者最新訊息：{user_message}"}
                ]
            ) as stream:
                for text in stream.text_stream:
                    full_reply += text
                    yield f"data: {json_mod.dumps({'text': text})}\n\n"

        except Exception as e:
            yield f"data: {json_mod.dumps({'error': str(e)})}\n\n"
            return

        # 完成後送出 blueprint 資訊
        from engines.ai_engine import extract_blueprint
        new_blueprint = extract_blueprint(full_reply)
        updated_blueprint = new_blueprint if new_blueprint else current_blueprint

        if blueprint_type in ["image", "workflow", "startup"]:
            update_blueprint(blueprint_type, updated_blueprint)

        global conversation_history
        conversation_history += f"\nAI顧問：{full_reply}"

        yield f"data: {json_mod.dumps({'done': True, 'blueprint': updated_blueprint, 'blueprint_type': blueprint_type})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/upload_images", methods=["POST"])
def upload_images():
    global uploaded_images
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "沒有收到圖片"})
    for file in files:
        if file.filename == "": continue
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)
        image_url = f"/static/uploads/{filename}"
        if image_url not in uploaded_images:
            uploaded_images.append(image_url)
    return jsonify({"message": "圖片上傳成功", "images": uploaded_images})


@app.route("/analyze_image", methods=["POST"])
def analyze_image_api():
    global conversation_history, image_blueprint
    data = request.get_json()
    image_url = data.get("image_url", "")
    if not image_url:
        return jsonify({"error": "沒有收到圖片路徑"})
    image_path = image_url.lstrip("/")
    result = analyze_image(image_path)
    image_blueprint = result
    conversation_history += f"\nVision分析：{result}"
    return jsonify({"analysis": result, "blueprint": image_blueprint, "blueprint_type": "image"})


@app.route("/analyze_style", methods=["POST"])
def analyze_style_api():
    data = request.get_json()
    image_url = data.get("image_url", "")
    project_name = data.get("project_name", current_project).strip()
    if not image_url: return jsonify({"error": "沒有收到圖片路徑"})
    if not project_name: return jsonify({"error": "請先設定專案名稱"})

    image_path = image_url.lstrip("/")
    result = analyze_style(image_path)
    if "error" in result: return jsonify({"error": result["error"]})

    save_style(project_name, image_url, result.get("raw", ""), result)
    return jsonify({"message": "風格已儲存", "style": result})


@app.route("/get_styles", methods=["POST"])
def get_styles_api():
    data = request.get_json()
    project_name = data.get("project_name", "").strip()
    if not project_name: return jsonify({"error": "請提供專案名稱"})
    styles = get_styles(project_name)
    return jsonify({"styles": styles})


@app.route("/delete_style", methods=["POST"])
def delete_style_api():
    data = request.get_json()
    style_id = data.get("id")
    if not style_id: return jsonify({"error": "請提供風格 ID"})
    delete_style(style_id)
    return jsonify({"message": "已刪除"})


@app.route("/generate_with_style", methods=["POST"])
def generate_with_style_api():
    global image_blueprint, conversation_history
    data = request.get_json()
    project_name = data.get("project_name", "").strip()
    if not project_name: return jsonify({"error": "請提供專案名稱"})

    styles = get_styles(project_name)
    if not styles: return jsonify({"error": "此專案尚無風格資料，請先上傳並分析圖片"})

    style_summary = build_style_prompt(styles)

    from engines.providers.provider_factory import get_ai_provider
    ask_model = get_ai_provider()

    prompt = f"""
你是 AI Creation Architect。
請根據以下風格資料與創作藍圖，生成 FLUX 英文提示詞。

【風格資料庫】
{style_summary}

【創作藍圖】
{image_blueprint if image_blueprint else "無，請完全依照風格生成"}

規則：只輸出英文提示詞，不要中文，不要 Negative Prompt，150字以內，必須融合風格關鍵字。
"""

    en_prompt = ask_model(prompt)
    image_url = generate_image(en_prompt)
    if image_url.startswith("ERROR:"):
        return jsonify({"error": image_url.replace("ERROR:", "").strip()})

    save_generated_image(project_name, en_prompt, image_url)
    conversation_history += f"\nAI依風格生成圖片：{en_prompt}"
    return jsonify({"image_url": image_url, "prompt_used": en_prompt, "style_count": len(styles)})


@app.route("/get_generated_images", methods=["POST"])
def get_generated_images_api():
    data = request.get_json()
    project_name = data.get("project_name", "").strip()
    if not project_name: return jsonify({"error": "請提供專案名稱"})
    images = get_generated_images(project_name)
    return jsonify({"images": images})


@app.route("/generate_prompt", methods=["POST"])
def generate_prompt_api():
    global image_blueprint, conversation_history
    if not image_blueprint:
        return jsonify({"error": "目前沒有生成藍圖，請先輸入需求或分析圖片。"})

    from engines.providers.provider_factory import get_ai_provider
    ask_model = get_ai_provider()

    prompt = f"""
你是 AI Creation Architect，把圖片創作藍圖轉成 AI 圖像生成提示詞。

目前生成藍圖：
{image_blueprint}

格式：
1. 英文正向提示詞
2. Negative Prompt
3. 繁體中文說明重點
"""
    result = ask_model(prompt)
    conversation_history += f"\nAI生成完整提示詞：{result}"
    return jsonify({"prompt": result})


@app.route("/generate_image", methods=["POST"])
def generate_image_api():
    global image_blueprint, conversation_history
    if not image_blueprint:
        return jsonify({"error": "目前沒有生成藍圖，請先輸入需求或分析圖片。"})

    from engines.providers.provider_factory import get_ai_provider
    ask_model = get_ai_provider()

    prompt = f"把以下藍圖轉成 FLUX 英文提示詞，只輸出提示詞，150字以內：\n{image_blueprint}"
    en_prompt = ask_model(prompt)
    image_url = generate_image(en_prompt)
    if image_url.startswith("ERROR:"):
        return jsonify({"error": image_url.replace("ERROR:", "").strip()})

    conversation_history += f"\nAI生成圖片：{en_prompt}"
    return jsonify({"image_url": image_url, "prompt_used": en_prompt})



@app.route("/generate_multiple", methods=["POST"])
def generate_multiple_api():
    global image_blueprint, conversation_history
    if not image_blueprint:
        return jsonify({"error": "目前沒有生成藍圖，請先輸入需求或分析圖片。"})

    from engines.providers.provider_factory import get_ai_provider
    import concurrent.futures

    ask_model = get_ai_provider()

    prompt = f"""把以下藍圖轉成 FLUX 英文提示詞，只輸出提示詞，150字以內：

{image_blueprint}"""

    en_prompt = ask_model(prompt)

    # 並行生成 4 張
    def gen_one(_):
        return generate_image(en_prompt)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(gen_one, range(4)))

    image_urls = [r for r in results if r and not r.startswith("ERROR:")]

    if not image_urls:
        return jsonify({"error": "所有圖片生成失敗，請稍後再試"})

    return jsonify({"image_urls": image_urls, "prompt_used": en_prompt})

@app.route("/projects", methods=["GET"])
def get_projects():
    return jsonify({"projects": list_projects()})


@app.route("/save_project", methods=["POST"])
def save_project_api():
    global conversation_history, image_blueprint, workflow_blueprint, startup_blueprint, uploaded_images, current_project
    data = request.get_json()
    project_name = data.get("project_name", "").strip()
    if not project_name: return jsonify({"error": "請輸入專案名稱"})

    current_project = project_name
    valid_images = [u for u in uploaded_images if os.path.exists(u.lstrip("/"))]
    uploaded_images = valid_images
    save_project(project_name, conversation_history, image_blueprint, workflow_blueprint, startup_blueprint, uploaded_images)
    return jsonify({"message": "專案已儲存", "project_name": project_name})


@app.route("/load_project", methods=["POST"])
def load_project_api():
    global conversation_history, image_blueprint, workflow_blueprint, startup_blueprint, uploaded_images, current_project
    data = request.get_json()
    project_name = data.get("project_name", "")
    project = load_project(project_name)
    if not project: return jsonify({"error": "找不到專案"})

    current_project = project_name
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
    if not project_name: return jsonify({"error": "請提供專案名稱"})
    success = delete_project(project_name)
    if not success: return jsonify({"error": "找不到專案"})
    return jsonify({"message": "專案已刪除", "project_name": project_name})


@app.route("/reset", methods=["POST"])
def reset_chat():
    global conversation_history, image_blueprint, workflow_blueprint, startup_blueprint, uploaded_images
    conversation_history = ""
    image_blueprint = ""
    workflow_blueprint = ""
    startup_blueprint = ""
    uploaded_images = []
    return jsonify({"message": "對話已重置"})



# ── 歷史生成圖片 ─────────────────────────────────────
@app.route("/history", methods=["POST"])
def history_api():
    data = request.get_json()
    project_name = data.get("project_name", "").strip()
    if not project_name:
        return jsonify({"error": "請提供專案名稱"})
    images = get_generated_images(project_name)
    return jsonify({"images": images})


# ── 提示詞優化迭代 ───────────────────────────────────
@app.route("/refine_image", methods=["POST"])
def refine_image_api():
    global image_blueprint, conversation_history
    data = request.get_json()
    instruction = data.get("instruction", "").strip()
    last_prompt = data.get("last_prompt", "").strip()

    if not instruction:
        return jsonify({"error": "請輸入修改指示"})
    if not last_prompt:
        return jsonify({"error": "沒有上一張圖的提示詞"})

    from engines.providers.provider_factory import get_ai_provider
    ask_model = get_ai_provider()

    prompt = f"""
你是圖片提示詞優化師。

上一張圖的英文提示詞：
{last_prompt}

使用者想修改的地方：
{instruction}

請根據修改指示調整提示詞，只輸出新的英文提示詞，不要中文，150字以內。
"""
    new_prompt = ask_model(prompt)
    image_url = generate_image(new_prompt)

    if image_url.startswith("ERROR:"):
        return jsonify({"error": image_url.replace("ERROR:", "").strip()})

    project_name = current_project
    if project_name:
        save_generated_image(project_name, new_prompt, image_url)

    conversation_history += f"\n優化提示詞：{instruction} → {new_prompt}"

    return jsonify({"image_url": image_url, "prompt_used": new_prompt})


# ── n8n JSON 下載 ────────────────────────────────────
@app.route("/export_n8n", methods=["POST"])
def export_n8n_api():
    global workflow_blueprint
    if not workflow_blueprint:
        return jsonify({"error": "目前沒有流程藍圖，請先輸入自動化需求"})

    from engines.providers.provider_factory import get_ai_provider
    ask_model = get_ai_provider()

    prompt = f"""
你是 n8n 自動化工程師。

請根據以下流程藍圖，生成一份完整可用的 n8n workflow JSON。

流程藍圖：
{workflow_blueprint}

規則：
1. 只輸出 JSON，不要任何說明
2. 使用真實的 n8n node types
3. 包含 nodes 和 connections
4. 觸發節點用 webhook 或 schedule
"""
    result = ask_model(prompt)

    import re
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = result.strip()

    return jsonify({"n8n_json": json_str})


# ── 風格混合 ─────────────────────────────────────────
@app.route("/blend_styles", methods=["POST"])
def blend_styles_api():
    global image_blueprint, conversation_history
    data = request.get_json()
    project_name = data.get("project_name", "").strip()
    style_ids = data.get("style_ids", [])

    if not project_name:
        return jsonify({"error": "請提供專案名稱"})
    if len(style_ids) < 2:
        return jsonify({"error": "請至少選擇 2 個風格"})

    all_styles = get_styles(project_name)
    selected = [s for s in all_styles if s["id"] in style_ids]

    if len(selected) < 2:
        return jsonify({"error": "找不到選擇的風格"})

    from engines.style_engine import build_style_prompt
    from engines.providers.provider_factory import get_ai_provider
    ask_model = get_ai_provider()

    style_summary = build_style_prompt(selected)

    prompt = f"""
你是風格融合專家。

請把以下 {len(selected)} 種風格融合成一種新風格，生成 FLUX 英文提示詞。

風格資料：
{style_summary}

規則：
1. 只輸出英文提示詞
2. 融合所有風格的特色
3. 150字以內
4. 不要 Negative Prompt
"""
    en_prompt = ask_model(prompt)
    image_url = generate_image(en_prompt)

    if image_url.startswith("ERROR:"):
        return jsonify({"error": image_url.replace("ERROR:", "").strip()})

    save_generated_image(project_name, en_prompt, image_url)
    return jsonify({"image_url": image_url, "prompt_used": en_prompt})


# ── 生成圖片分享連結 ──────────────────────────────────
@app.route("/share/<path:image_id>", methods=["GET"])
def share_image(image_id):
    from flask import redirect
    conn = __import__("db").get_conn()
    cur = conn.cursor()
    cur.execute("SELECT image_url FROM generated_images WHERE id = %s", (image_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return "找不到圖片", 404
    return redirect(row["image_url"])


# ── 兩張圖片合成（主體+背景）────────────────────────────
@app.route("/composite_images", methods=["POST"])
def composite_images_api():
    global conversation_history
    data = request.get_json()
    subject_url = data.get("subject_url", "")
    background_url = data.get("background_url", "")

    if not subject_url or not background_url:
        return jsonify({"error": "請提供主體圖和背景圖"})

    import base64, anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def load_image(url):
        path = url.lstrip("/")
        ext = os.path.splitext(path)[1].lower()
        media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        media_type = media_map.get(ext, "image/jpeg")
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        return data, media_type

    try:
        subject_data, subject_media = load_image(subject_url)
        bg_data, bg_media = load_image(background_url)
    except Exception as e:
        return jsonify({"error": f"讀取圖片失敗：{str(e)}"})

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "這是主體圖（第一張）和背景圖（第二張）。"},
                {"type": "image", "source": {"type": "base64", "media_type": subject_media, "data": subject_data}},
                {"type": "image", "source": {"type": "base64", "media_type": bg_media, "data": bg_data}},
                {"type": "text", "text": """請分析這兩張圖，生成一段 FLUX 英文提示詞，把第一張圖的主體放進第二張圖的背景場景中。
只輸出英文提示詞，150字以內，不要說明。"""}
            ]
        }]
    )

    en_prompt = message.content[0].text.strip()
    image_url = generate_image(en_prompt)

    if image_url.startswith("ERROR:"):
        return jsonify({"error": image_url.replace("ERROR:", "").strip()})

    if current_project:
        save_generated_image(current_project, en_prompt, image_url)

    conversation_history += f"\n合成圖片：{en_prompt}"

    return jsonify({"image_url": image_url, "prompt_used": en_prompt})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
