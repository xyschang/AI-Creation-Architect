import json
import os

PROJECT_FOLDER = "projects"

os.makedirs(PROJECT_FOLDER, exist_ok=True)


def save_project(
    project_name,
    conversation_history,
    image_blueprint="",
    workflow_blueprint="",
    startup_blueprint="",
    uploaded_images=None
):

    if uploaded_images is None:
        uploaded_images = []

    data = {
        "project_name": project_name,
        "conversation_history": conversation_history,
        "image_blueprint": image_blueprint,
        "workflow_blueprint": workflow_blueprint,
        "startup_blueprint": startup_blueprint,
        "uploaded_images": uploaded_images
    }

    filepath = os.path.join(
        PROJECT_FOLDER,
        f"{project_name}.json"
    )

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


def load_project(project_name):

    filepath = os.path.join(
        PROJECT_FOLDER,
        f"{project_name}.json"
    )

    if not os.path.exists(filepath):
        return None

    try:
        with open(
            filepath,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except json.JSONDecodeError:
        return {
            "project_name": project_name,
            "conversation_history": "",
            "character_profile": "這個專案檔案格式錯誤，請重新儲存或刪除此專案。"
        }


def list_projects():

    projects = []

    for file in os.listdir(PROJECT_FOLDER):

        if file.endswith(".json"):

            projects.append(
                file.replace(".json", "")
            )

    return projects

def delete_project(project_name):

    filepath = os.path.join(
        PROJECT_FOLDER,
        f"{project_name}.json"
    )

    if not os.path.exists(filepath):
        return False

    os.remove(filepath)
    return True