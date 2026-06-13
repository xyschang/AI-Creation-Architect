import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    """建立所有需要的資料表"""
    conn = get_conn()
    cur = conn.cursor()

    # 專案風格資料表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS project_styles (
            id SERIAL PRIMARY KEY,
            project_name TEXT NOT NULL,
            image_url TEXT NOT NULL,
            style_analysis TEXT,
            color_tone TEXT,
            visual_style TEXT,
            lighting TEXT,
            composition TEXT,
            atmosphere TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 生成圖片紀錄資料表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS generated_images (
            id SERIAL PRIMARY KEY,
            project_name TEXT NOT NULL,
            prompt_used TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ 資料庫初始化完成")


def save_style(project_name, image_url, analysis_text, parsed):
    """儲存風格分析結果"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO project_styles
            (project_name, image_url, style_analysis, color_tone, visual_style, lighting, composition, atmosphere)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        project_name,
        image_url,
        analysis_text,
        parsed.get("color_tone", ""),
        parsed.get("visual_style", ""),
        parsed.get("lighting", ""),
        parsed.get("composition", ""),
        parsed.get("atmosphere", "")
    ))
    conn.commit()
    cur.close()
    conn.close()


def get_styles(project_name):
    """取得某專案所有風格資料"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM project_styles
        WHERE project_name = %s
        ORDER BY created_at DESC
    """, (project_name,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def delete_style(style_id):
    """刪除單筆風格"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM project_styles WHERE id = %s", (style_id,))
    conn.commit()
    cur.close()
    conn.close()


def save_generated_image(project_name, prompt_used, image_url):
    """儲存生成圖片紀錄"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO generated_images (project_name, prompt_used, image_url)
        VALUES (%s, %s, %s)
    """, (project_name, prompt_used, image_url))
    conn.commit()
    cur.close()
    conn.close()


def get_generated_images(project_name):
    """取得某專案所有生成圖片"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM generated_images
        WHERE project_name = %s
        ORDER BY created_at DESC
    """, (project_name,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]
