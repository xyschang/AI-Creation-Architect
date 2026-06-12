def create_blueprint(content, blueprint_type="image"):
    return {
        "type": blueprint_type,

        "subject_blueprint": "",

        "style_blueprint": "",

        "scene_blueprint": "",

        "fixed_rules": "",

        "raw_content": content
    }