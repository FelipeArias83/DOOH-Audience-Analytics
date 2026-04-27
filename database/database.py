import pandas as pd
import sqlite3
from datetime import datetime
import os

DB_FOLDER = "data"
DB_PATH = os.path.join(DB_FOLDER, "audience_analytics.db")

def init_db():
    """Crea la carpeta y la tabla si no existen."""
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS view_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            commercial_id TEXT,
            seconds_watched REAL,
            emotion_detected TEXT,
            age_estimated INTEGER,
            gender_detected TEXT,
            is_child INTEGER
        )
    ''')
    _ensure_optional_columns(cursor)
    conn.commit()
    conn.close()

def _ensure_optional_columns(cursor):
    cursor.execute("PRAGMA table_info(view_sessions)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if "age_estimated" not in existing_columns:
        cursor.execute("ALTER TABLE view_sessions ADD COLUMN age_estimated INTEGER")
    if "gender_detected" not in existing_columns:
        cursor.execute("ALTER TABLE view_sessions ADD COLUMN gender_detected TEXT")
    if "is_child" not in existing_columns:
        cursor.execute("ALTER TABLE view_sessions ADD COLUMN is_child INTEGER")

def log_view_session(duration, emotion, commercial_id, age=None, gender=None, is_child=None):
    """Registra una sesión de visualización de forma segura."""
    init_db() # Asegura que la tabla existe
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO view_sessions (
                timestamp,
                commercial_id,
                seconds_watched,
                emotion_detected,
                age_estimated,
                gender_detected,
                is_child
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            commercial_id,
            round(duration, 2),
            emotion,
            age,
            gender,
            int(is_child) if is_child is not None else None,
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error al guardar en base de datos: {e}")

def get_analytics_summary():
    """Obtiene los datos directamente en un DataFrame de Pandas."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    # Leemos la tabla completa para Streamlit
    df = pd.read_sql_query("SELECT * FROM view_sessions", conn)
    conn.close()
    return df