import streamlit as st
import json
from datetime import datetime, time
import re
import urllib.parse
from google import genai
client = genai.Client (api_key=st.secrets["GEMINI_API_KEY"])
import sqlite3
import os
import base64
import pandas as pd
from datetime import datetime
from google.genai import types


OFFICIAL_SUPPORT_EMAIL = "conilnessu@gmail.com"
DB_FILE = "nexus_core.db"
LOGO_PATH = "logo.jpg"

# -------------------------------------------------------------
# 1. BASE DE DATOS SQLITE (Persistencia, Seguridad & Migraciones)
# -------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabla de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nick TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'Activo',
            gemini_verdict TEXT,
            security_question TEXT,
            security_answer TEXT,
            joined_date TEXT,
            last_active TEXT
        )
    ''')
    
    # Migraciones para users
    cursor.execute("PRAGMA table_info(users)")
    u_cols = [col["name"] for col in cursor.fetchall()]
    if "security_question" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
    if "security_answer" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN security_answer TEXT")

    # Tabla de Perfiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            user_nick TEXT PRIMARY KEY,
            profesion TEXT,
            instruccion TEXT,
            estilo_vida_hobbies_intereses TEXT,
            pensamiento_politico_religioso TEXT,
            entorno_social TEXT,
            personal_motores TEXT,
            metas TEXT,
            frustraciones TEXT,
            logros TEXT,
            updated_at TEXT,
            FOREIGN KEY(user_nick) REFERENCES users(nick)
        )
    ''')
    
    cursor.execute("PRAGMA table_info(profiles)")
    p_cols = [col["name"] for col in cursor.fetchall()]
    if "estilo_vida_hobbies_intereses" not in p_cols:
        cursor.execute("ALTER TABLE profiles ADD COLUMN estilo_vida_hobbies_intereses TEXT")

    # Tabla de Control Diario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_insights (
            user_nick TEXT PRIMARY KEY,
            date_str TEXT NOT NULL,
            potencial_y_fortalezas TEXT NOT NULL,
            consejo_bienestar TEXT NOT NULL,
            suggested_contacts_json TEXT NOT NULL,
            generated_at TEXT NOT NULL
        )
    ''')

    # Tabla de Chat del Consejero
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_nick TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Crear Administrador nesu / 0000 con pregunta por defecto
    cursor.execute("SELECT id FROM users WHERE nick = 'nesu'")
    if not cursor.fetchone():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO users (nick, password, role, status, gemini_verdict, security_question, security_answer, joined_date, last_active)
            VALUES ('nesu', '0000', 'admin', 'Activo', 'Superadministrador Fundador', '¿Clave de origen Nexus?', 'nexus', ?, ?)
        ''', (now_str, now_str))
        cursor.execute('''
            INSERT INTO profiles (user_nick, profesion, instruccion, estilo_vida_hobbies_intereses, pensamiento_politico_religioso, entorno_social, personal_motores, metas, frustraciones, logros, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'nesu',
            'Arquitecto de Sistemas & Estratega Soberano',
            'Formación Superior en Ciencias de la Computación y Análisis de Sistemas Complejos',
            'Vida activa y reflexiva; cocina mediterránea casera, senderismo de montaña, lectura histórica y desconexión digital',
            'Humanismo pragmático, libertad individual con responsabilidad moral y respeto espiritual',
            'Círculos de innovación técnica, debate reflexivo y cultura mediterránea',
            'Aviación civil ligera, motocicletas clásicas de ruta y entrenamiento de fuerza',
            'Escalar la plataforma Nexus preservando la privacidad absoluta de los miembros',
            'Fricción con burocracias lentas que limitan el avance técnico',
            'Consolidación de arquitecturas descentralizadas de alto rendimiento',
            now_str
        ))
    
    # Perfiles demo de prueba
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'user'")
    if cursor.fetchone()['count'] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO users (nick, password, role, status, gemini_verdict, security_question, security_answer, joined_date, last_active)
            VALUES 
            ('AetherX', '9xK2A', 'user', 'Activo', 'Aprobado - Perfil Cloud & Backend', '¿Ciudad donde creciste?', 'valencia', ?, ?),
            ('Valkyrie', 'B7m8Z', 'user', 'Activo', 'Aprobado - Enfoque Aeronáutico & Diseño', '¿Nombre de tu primera mascota?', 'odin', ?, ?),
            ('Marcus_Dev', 'L4m9P', 'user', 'Activo', 'Aprobado - Estratega & Pensamiento Crítico', '¿Modelo de tu primer vehículo?', 'vespa', ?, ?)
        ''', (now_str, now_str, now_str, now_str, now_str, now_str))
        
        cursor.execute('''
            INSERT INTO profiles (user_nick, profesion, instruccion, estilo_vida_hobbies_intereses, pensamiento_politico_religioso, entorno_social, personal_motores, metas, frustraciones, logros, updated_at)
            VALUES 
            ('AetherX', 'Ingeniera de Datos & Cloud Architect', 'Máster en Inteligencia Artificial y Big Data', 'Ciclismo de larga distancia, gastronomía japonesa, ajedrez y cafés de especialidad', 'Liberal clásica; cree en el mérito y la transparencia institucional', 'Entornos de investigación aplicada y trabajo remoto sin jerarquías rígidas', 'Ciclismo de fondo y pasión por motores eléctricos eficientes', 'Desarrollar modelos descentralizados de aprendizaje seguro', 'Burocracia corporativa excesiva', 'Infraestructuras de datos escaladas con éxito', ?),
            ('Valkyrie', 'Diseñadora Industrial & Piloto ULM', 'Licenciatura en Bellas Artes e Ingeniería de Producto', 'Vuelo deportivo en avioneta, restauración artesanal, acampada libre y fotografía analógica', 'Espiritualidad humanista y ecologismo pragmático no dogmático', 'Comunidades artísticas independientes y círculos de vuelo deportivo', 'Piloto de aviación ligera, restauración de motocicletas custom y senderismo', 'Abrir un taller de diseño aeronáutico experimental', 'Imposiciones comerciales que degradan la calidad del diseño', 'Vuelos de travesía en solitario y premios de diseño funcional', ?),
            ('Marcus_Dev', 'Filósofo de Tecnología & Consultor Estratégico', 'Doble Grado en Filosofía y Ciencias Económicas', 'Rutas botánicas en 4x4, lectura estoica, vinilos de jazz y debate de sobremesa', 'Pensamiento republicano clásico y ética estoica de vida', 'Ateneo cultural, debates sobre ética en tecnología y tertulias literarias', 'Entrenamiento de fuerza funcional y rutas de montaña en 4x4 clásico', 'Publicar un tratado sobre autonomía cognitiva en la era algorítmica', 'Superficialidad de las redes sociales masivas', 'Autor de ensayos leídos por miles en medios independientes', ?)
        ''', (now_str, now_str, now_str))
        
    conn.commit()
    conn.close()

# -------------------------------------------------------------
# Funciones Utilitarias de Base de Datos
# -------------------------------------------------------------
def get_stored_daily_insight(user_nick, today_date_str):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM daily_insights WHERE user_nick = ? AND date_str = ?", 
        (user_nick, today_date_str)
    ).fetchone()
    conn.close()
    if row:
        return {
            "potencial_y_fortalezas": row["potencial_y_fortalezas"],
            "consejo_bienestar": row["consejo_bienestar"],
            "contacts": json.loads(row["suggested_contacts_json"]) if row["suggested_contacts_json"] else [],
            "date_str": row["date_str"],
            "generated_at": row["generated_at"]
        }
    return None

def save_stored_daily_insight(user_nick, today_date_str, insight_dict, contacts_list):
    conn = get_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute('''
        INSERT INTO daily_insights (user_nick, date_str, potencial_y_fortalezas, consejo_bienestar, suggested_contacts_json, generated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_nick) DO UPDATE SET
            date_str = excluded.date_str,
            potencial_y_fortalezas = excluded.potencial_y_fortalezas,
            consejo_bienestar = excluded.consejo_bienestar,
            suggested_contacts_json = excluded.suggested_contacts_json,
            generated_at = excluded.generated_at
    ''', (
        user_nick,
        today_date_str,
        insight_dict.get("potencial_y_fortalezas", ""),
        insight_dict.get("consejo_bienestar", ""),
        json.dumps(contacts_list, ensure_ascii=False),
        now_str
    ))
    conn.commit()
    conn.close()

def clear_stored_daily_insight(user_nick):
    conn = get_db()
    conn.execute("DELETE FROM daily_insights WHERE user_nick = ?", (user_nick,))
    conn.commit()
    conn.close()

def get_user_profile(user_nick):
    conn = get_db()
    row = conn.execute("SELECT * FROM profiles WHERE user_nick = ?", (user_nick,)) .fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "profesion": "Profesional Independiente",
        "instruccion": "Formación Superior Especializada",
        "estilo_vida_hobbies_intereses": "Estilo de vida activo y reflexivo, deporte al aire libre y afición por la cultura",
        "pensamiento_politico_religioso": "Humanismo ético y respeto por la libertad de conciencia",
        "entorno_social": "Círculos selectos de debate y crecimiento",
        "personal_motores": "Entrenamiento regular y pasión por la movilidad",
        "metas": "Consolidación de proyectos y balance vital",
        "frustraciones": "Tiempos muertos y lentitud en procesos",
        "logros": "Trayectoria profesional sostenida"
    }

def update_user_profile(user_nick, p_dict):
    conn = get_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute('''
        INSERT INTO profiles (user_nick, profesion, instruccion, estilo_vida_hobbies_intereses, pensamiento_politico_religioso, entorno_social, personal_motores, metas, frustraciones, logros, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_nick) DO UPDATE SET
            profesion = excluded.profesion,
            instruccion = excluded.instruccion,
            estilo_vida_hobbies_intereses = excluded.estilo_vida_hobbies_intereses,
            pensamiento_politico_religioso = excluded.pensamiento_politico_religioso,
            entorno_social = excluded.entorno_social,
            personal_motores = excluded.personal_motores,
            metas = excluded.metas,
            frustraciones = excluded.frustraciones,
            logros = excluded.logros,
            updated_at = excluded.updated_at
    ''', (
        user_nick,
        p_dict.get("profesion"),
        p_dict.get("instruccion"),
        p_dict.get("estilo_vida_hobbies_intereses"),
        p_dict.get("pensamiento_politico_religioso"),
        p_dict.get("entorno_social"),
        p_dict.get("personal_motores"),
        p_dict.get("metas"),
        p_dict.get("frustraciones"),
        p_dict.get("logros"),
        now_str
    ))
    conn.commit()
    conn.close()

def get_other_profiles_from_db(current_user_nick):
    conn = get_db()
    rows = conn.execute('''
        SELECT u.nick, u.status, p.profesion, p.instruccion, p.estilo_vida_hobbies_intereses, p.pensamiento_politico_religioso, p.entorno_social, p.personal_motores, p.metas
        FROM users u
        LEFT JOIN profiles p ON u.nick = p.user_nick
        WHERE u.nick != ? AND u.status = 'Activo'
    ''', (current_user_nick,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_chat_message(user_nick, role, content):
    conn = get_db()
    conn.execute("INSERT INTO chat_messages (user_nick, role, content, timestamp) VALUES (?, ?, ?, ?)",
                 (user_nick, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit(); conn.close()

def load_chat_history(user_nick):
    conn = get_db()
    rows = conn.execute("SELECT role, content FROM chat_messages WHERE user_nick = ? ORDER BY id ASC", (user_nick,)).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]

def clear_chat_history(user_nick):
    conn = get_db()
    conn.execute("DELETE FROM chat_messages WHERE user_nick = ?", (user_nick,))
    conn.commit(); conn.close()

init_db()

# -------------------------------------------------------------
# 2. Configuración Visual & Logo
# -------------------------------------------------------------
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

app_icon = LOGO_PATH if os.path.exists(LOGO_PATH) else "💠"
logo_b64 = get_base64_image(LOGO_PATH)

st.set_page_config(page_title="Nexus OS", page_icon=app_icon, layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 10% 10%, #111827 0%, #0B0F19 100%); color: #F3F4F6; }
    
    .nexus-logo-round {
        width: 76px; height: 76px; border-radius: 50%; object-fit: cover;
        border: 2px solid rgba(99, 102, 241, 0.6);
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.4);
        display: block; margin: 0 auto 12px auto;
    }
    .nexus-logo-header {
        width: 46px; height: 46px; border-radius: 50%; object-fit: cover;
        border: 1.5px solid rgba(6, 182, 212, 0.6);
        box-shadow: 0 0 12px rgba(6, 182, 212, 0.35);
        vertical-align: middle; margin-right: 12px;
    }
    .nexus-card {
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 18px;
        padding: 22px; margin-bottom: 16px;
    }
    .empower-card {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(16, 185, 129, 0.05) 100%);
        border: 1px solid rgba(99, 102, 241, 0.35);
        border-left: 4px solid #6366F1;
        border-radius: 16px;
        padding: 20px 24px;
        height: 100%;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
    }
    .network-card {
        background: linear-gradient(135deg, rgba(6, 182, 212, 0.08) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(6, 182, 212, 0.3);
        border-left: 4px solid #06B6D4;
        border-radius: 16px;
        padding: 20px 24px;
        height: 100%;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
    }
    .scout-card {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.09) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-left: 4px solid #F59E0B;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 18px;
    }
    .contact-item {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .nexus-badge {
        display: inline-block; padding: 3px 10px; border-radius: 9999px;
        font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
    }
    .badge-cyan { background: rgba(6, 182, 212, 0.15); color: #22D3EE; border: 1px solid rgba(6, 182, 212, 0.3); }
    .badge-purple { background: rgba(99, 102, 241, 0.15); color: #A5B4FC; border: 1px solid rgba(99, 102, 241, 0.3); }
    .badge-green { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-gold { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .gradient-title {
        background: linear-gradient(135deg, #FFFFFF 30%, #94A3B8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 3. Estados de Sesión
# -------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "es"
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "auth_role" not in st.session_state:
    st.session_state.auth_role = None
if "session_start" not in st.session_state:
    st.session_state.session_start = datetime.now()
if "daily_evaluation" not in st.session_state:
    st.session_state.daily_evaluation = None
if "suggested_contacts_cache" not in st.session_state:
    st.session_state.suggested_contacts_cache = None
if "evaluation_date" not in st.session_state:
    st.session_state.evaluation_date = None
if "unmasked_contacts" not in st.session_state:
    st.session_state.unmasked_contacts = set()
if "web_opportunities_cache" not in st.session_state:
    st.session_state.web_opportunities_cache = None
if "quick_prompt_query" not in st.session_state:
    st.session_state.quick_prompt_query = None

# Lista estándar de preguntas de seguridad
SECURITY_QUESTIONS = [
    "¿Cuál fue el nombre de tu primera mascota?",
    "¿En qué ciudad nació tu abuelo materno?",
    "¿Cuál es el modelo o marca de tu primer vehículo?",
    "¿Cómo se llamaba tu primera escuela primaria?",
    "¿Cuál es tu destino favorito de viaje de la infancia?"
]

# -------------------------------------------------------------
# 4. Generadores Cognitivos & Búsqueda Web
# -------------------------------------------------------------
def generate_empowered_daily_insight(gemini_client, user_nick, user_p, lang_code):
    lang_name = {"es": "Spanish", "en": "English", "fr": "French", "it": "Italian"}.get(lang_code, "Spanish")
    prompt = f"""
    Eres el Consejero Soberano y Mentor Personal de {user_nick}.

    PERSONALIDAD OBLIGATORIA:
    - Cálida, humana, reflexiva, equilibrada y perspicaz. Responde con sabiduría y apoyo constructivo.

    CONTEXTO COMPLETO DEL USUARIO:
    - INSTRUCCIÓN Y EDUCACIÓN: {user_p.get('instruccion')}
    - PROFESIÓN: {user_p.get('profesion')}
    - ESTILO DE VIDA, PASATIEMPOS E INTERESES: {user_p.get('estilo_vida_hobbies_intereses')}
    - PENSAMIENTO POLÍTICO-RELIGIOSO: {user_p.get('pensamiento_politico_religioso')}
    - ENTORNO SOCIAL: {user_p.get('entorno_social')}
    - MOTORES Y FÍSICO: {user_p.get('personal_motores')}
    - METAS: {user_p.get('metas')}
    - FRUSTRACIONES: {user_p.get('frustraciones')}
    - LOGROS: {user_p.get('logros')}

    INSTRUCCIONES:
    1. 'potencial_y_fortalezas': Un párrafo perspicaz (2-3 frases) destacando DE LO QUE ES CAPAZ este usuario, reconociendo el valor de su formación (instrucción), sus pasatiempos, su claridad ética y sus victorias.
    2. 'consejo_bienestar': Un consejo reflexivo y sabio (2 frases) sobre equilibrio diario, paz interior y cómo gestionar su energía física y mental hoy.

    Devuelve EXCLUSIVAMENTE un JSON con:
    {{
        "potencial_y_fortalezas": "...",
        "consejo_bienestar": "..."
    }}
    Idioma: {lang_name}.
    """
    res = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(res.text)

def find_db_affinities(gemini_client, current_user_nick, current_user_p, other_profiles, lang_code):
    if not other_profiles:
        return []
    
    lang_name = {"es": "Spanish", "en": "English", "fr": "French", "it": "Italian"}.get(lang_code, "Spanish")
    prompt = f"""
    Eres el Consejero de Afinidades de Nexus OS.
    Analiza con juicio perspicaz y cálido la compatibilidad entre el usuario y los candidatos registrados en SQLite:

    USUARIO ACTIVO ({current_user_nick}):
    - Profesión e Instrucción: {current_user_p.get('profesion')} | {current_user_p.get('instruccion')}
    - Estilo de Vida, Pasatiempos e Intereses: {current_user_p.get('estilo_vida_hobbies_intereses')}
    - Pensamiento y Valores: {current_user_p.get('pensamiento_politico_religioso')}
    - Entorno Social: {current_user_p.get('entorno_social')}
    - Pasiones: {current_user_p.get('personal_motores')}
    - Metas: {current_user_p.get('metas')}

    CANDIDATOS EN BASE DE DATOS:
    {json.dumps(other_profiles, ensure_ascii=False)}

    Criterios:
    1. Sintonía profesional y complementariedad formativa.
    2. Armonía en estilo de vida, pasatiempos, intereses y valores éticos/sociales.
    3. Score Total (0 a 100).

    Devuelve un JSON con 'sugerencias' (máximo 3):
    {{
        "sugerencias": [
            {{
                "nick_real": "...",
                "codigo_ciego": "Perfil Ciego #NX-...",
                "score": 94,
                "dimension": "💼 Profesional & 🏄 Estilo de Vida",
                "motivo": "Explicación concisa y perspicaz redactada en {lang_name}"
            }}
        ]
    }}
    """
    res = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    data = json.loads(res.text)
    return data.get("sugerencias", [])

def search_web_opportunities(gemini_client, user_nick, user_p, lang_code, category="Ambos"):
    lang_name = {"es": "Spanish", "en": "English", "fr": "French", "it": "Italian"}.get(lang_code, "Spanish")
    prompt = f"""
    Eres el Agente Scout y Asesor de Inversión y Empleo de Nexus OS para el usuario '{user_nick}'.
    Utiliza Google Search para rastrear oportunidades REALES, ACTIVAS y ACTUALIZADAS en la web acordes a:

    PERFIL COMPLETO:
    - Profesión e Instrucción: {user_p.get('profesion')} | {user_p.get('instruccion')}
    - Estilo de Vida, Pasatiempos e Intereses: {user_p.get('estilo_vida_hobbies_intereses')}
    - Pasiones y Motores: {user_p.get('personal_motores')}
    - Marco Ético: {user_p.get('pensamiento_politico_religioso')}
    - Metas de Vida: {user_p.get('metas')}
    - Foco Solicitado: {category}

    Presenta el reporte en formato Markdown con:
    - 💼 Oportunidades Laborales Curadas (Rol, Entorno y por qué encaja con su estilo de vida).
    - 📈 Oportunidades de Inversión y Proyectos Estratégicos (Sector, potencial y sinergia).
    - 🧭 Dictamen Estratégico de Gemini (Consejos de aproximación).

    Idioma obligatorio: {lang_name}.
    """
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        system_instruction="Eres un asesor de élite que investiga oportunidades web contrastadas respetando la soberanía del usuario."
    )
    res = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config
    )
    return res.text

# -------------------------------------------------------------
# 5. Barra Lateral
# -------------------------------------------------------------
with st.sidebar:
    if logo_b64:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 8px;">
            <img src="data:image/jpeg;base64,{logo_b64}" class="nexus-logo-round">
            <h3 style="margin: 0; font-size: 1.3rem;">Nexus OS</h3>
            <span class="nexus-badge badge-purple">Soberanía Digital</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("### 💠 **Nexus OS**")

    lang_code = st.selectbox(
        "🌐 Idioma / Language",
        ["es", "en", "fr", "it"],
        format_func=lambda x: {"es": "Español", "en": "English", "fr": "Français", "it": "Italiano"}[x],
        index=["es", "en", "fr", "it"].index(st.session_state.lang)
    )
    if lang_code != st.session_state.lang:
        st.session_state.lang = lang_code
        st.session_state.daily_evaluation = None
        st.session_state.suggested_contacts_cache = None
        st.session_state.web_opportunities_cache = None
        st.rerun()

    api_key = st.text_input("Gemini API Key:", type="password")

    conn = get_db()
    c_users = conn.execute("SELECT COUNT(*) as total FROM users WHERE role != 'admin'").fetchone()['total']
    conn.close()

    st.divider()
    st.metric("👥 Utentes Registrados", f"{c_users} en Base de Datos")

    if st.session_state.auth_user:
        elapsed = datetime.now() - st.session_state.session_start
        mins, secs = divmod(int(elapsed.total_seconds()), 60)
        st.info(f"⏱️ **Timer de Utilizo:** `{mins:02d}m {secs:02d}s`")
        
        if st.session_state.auth_role == "admin":
            st.markdown('<span class="nexus-badge badge-gold">Sesión Administrador Activa</span>', unsafe_allow_html=True)

        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.auth_user = None
            st.session_state.auth_role = None
            st.session_state.daily_evaluation = None
            st.session_state.suggested_contacts_cache = None
            st.session_state.web_opportunities_cache = None
            st.session_state.evaluation_date = None
            st.session_state.unmasked_contacts = set()
            st.rerun()

    st.divider()
    st.caption("📬 Soporte Oficial:")
    st.code(OFFICIAL_SUPPORT_EMAIL, language="text")

if not api_key:
    st.info("Introduce tu Gemini API Key en la barra lateral para continuar.")
    st.stop()

client = genai.Client(api_key=api_key)

# -------------------------------------------------------------
# 6. PANTALLA DE ACCESO (Hero + Login / Registro / Recuperación)
# -------------------------------------------------------------
if not st.session_state.auth_user:
    hero_b64 = get_base64_image("hero.jpg")
    bg_style = f"""
    <style>
        .hero-container {{
            background: linear-gradient(180deg, rgba(11, 15, 25, 0.35) 0%, rgba(11, 15, 25, 0.95) 85%),
                        url('data:image/jpeg;base64,{hero_b64 if hero_b64 else ""}');
            background-size: cover; background-position: center top;
            border-radius: 24px; padding: 70px 30px; margin-bottom: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1); text-align: center;
        }}
    </style>
    """
    st.markdown(bg_style, unsafe_allow_html=True)

    st.markdown("""
    <div class="hero-container">
        <span class="nexus-badge badge-cyan" style="margin-bottom: 12px;">Soberanía Digital & Privacidad</span>
        <h1 class="gradient-title" style="font-size: 2.8rem; margin: 10px 0 15px 0;">
            El mundo es amplio.<br>Tu identidad te pertenece.
        </h1>
        <p style="color: #CBD5E1; max-width: 640px; margin: 0 auto 24px auto; font-size: 1.05rem; line-height: 1.6;">
            Accede a tu mentor privado con validación de seguridad y recuperación protegida de credenciales.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup, tab_reset = st.tabs(["🔑 Iniciar Sesión", "📝 Registrar Nuevo Utente", "🔄 Restablecer Contraseña"])

    # 1. LOGIN
    with tab_login:
        col_u, col_p = st.columns(2)
        with col_u:
            l_nick = st.text_input("Nick de Utente:", key="l_nick")
        with col_p:
            l_pass = st.text_input("Password:", type="password", key="l_pass")

        if st.button("Ingresar a Nexus", type="primary", use_container_width=True):
            conn = get_db()
            user_row = conn.execute("SELECT * FROM users WHERE nick = ?", (l_nick,)).fetchone()
            conn.close()

            if user_row:
                if user_row["status"] == "Bloqueado":
                    st.error("⛔ Utente bloqueado por la Administración.")
                elif user_row["password"] == l_pass:
                    st.session_state.auth_user = user_row["nick"]
                    st.session_state.auth_role = user_row["role"]
                    st.session_state.session_start = datetime.now()
                    st.session_state.daily_evaluation = None
                    st.session_state.suggested_contacts_cache = None
                    st.session_state.web_opportunities_cache = None
                    st.session_state.evaluation_date = None
                    st.success(f"Bienvenido {user_row['nick']}.")
                    st.rerun()
                else:
                    st.error("Password incorrecta.")
            else:
                st.error("El nick no existe en la base de datos.")

    # 2. REGISTRO CON PREGUNTA Y RESPUESTA DE SEGURIDAD
    with tab_signup:
        r_nick = st.text_input("Elige tu Nick:", key="reg_nick")
        r_pass = st.text_input("Password (5 caracteres alfanuméricos):", max_chars=5, key="reg_pass")
        
        col_sq, col_sa = st.columns(2)
        with col_sq:
            r_sec_q = st.selectbox("Pregunta de Seguridad:", SECURITY_QUESTIONS, key="reg_sec_q")
        with col_sa:
            r_sec_a = st.text_input("Respuesta Confidencial:", key="reg_sec_a", help="La necesitarás si olvidas tu contraseña.")

        r_intent = st.text_area("Declaración de Propósito (Auditada por Gemini):", key="reg_intent")

        if st.button("Solicitar Confirma de Gemini", type="primary", use_container_width=True):
            if r_nick.lower() == "nesu":
                st.error("⚠️ El nick 'nesu' está reservado para la administración.")
            elif not re.match(r"^[a-zA-Z0-9]{5}$", r_pass):
                st.error("⚠️ La password debe tener exactamente 5 caracteres alfanuméricos.")
            elif not r_sec_a.strip():
                st.error("⚠️ Debes proporcionar una respuesta para la pregunta de seguridad.")
            elif not r_intent.strip():
                st.error("⚠️ Debes incluir tu declaración de propósito.")
            else:
                conn = get_db()
                exists = conn.execute("SELECT id FROM users WHERE nick = ?", (r_nick,)).fetchone()
                if exists:
                    st.error("⚠️ Este Nick ya está en uso.")
                    conn.close()
                else:
                    with st.spinner("Gemini auditando solicitud con tono perspicaz..."):
                        vetting = f"Evalúa la intención: '{r_intent}'. Responde JSON con 'aprobado': true/false."
                        res = client.models.generate_content(model="gemini-2.5-flash", contents=vetting, config=types.GenerateContentConfig(response_mime_type="application/json"))
                        v = json.loads(res.text)
                        if v.get("aprobado", True):
                            now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            conn.execute('''
                                INSERT INTO users (nick, password, role, status, gemini_verdict, security_question, security_answer, joined_date, last_active)
                                VALUES (?, ?, 'user', 'Activo', 'Aprobado', ?, ?, ?, ?)
                            ''', (r_nick, r_pass, r_sec_q, r_sec_a.strip().lower(), now_s, now_s))
                            
                            conn.execute('''
                                INSERT INTO profiles (user_nick, profesion, instruccion, estilo_vida_hobbies_intereses, pensamiento_politico_religioso, entorno_social, personal_motores, metas, frustraciones, logros, updated_at)
                                VALUES (?, 'Nuevo Profesional', 'Formación Técnica / Universitaria', 'Vida activa y deportiva, interés por la cultura', 'Humanismo y Libertad', 'Entorno en desarrollo', 'Actividad física regular', 'Crecimiento integral', 'Falta de tiempo', 'Inicio en Nexus', ?)
                            ''', (r_nick, now_s))
                            conn.commit(); conn.close()
                            st.success("✅ ¡Aprobado por Gemini y registrado con credenciales de seguridad! Ya puedes iniciar sesión.")
                        else:
                            conn.close()
                            st.error("❌ Solicitud no admitida por las directrices de Nexus.")

    # 3. RESTABLECER CONTRASEÑA VALIDANDO PREGUNTA DE SEGURIDAD
    with tab_reset:
        st.markdown("#### Recuperación Soberana de Acceso")
        st.caption("Verifica tu identidad respondiendo a tu pregunta de seguridad registrada para redefinir tu password.")
        
        reset_nick = st.text_input("Ingresa tu Nick para localizar tu cuenta:", key="reset_nick_input")
        
        if reset_nick:
            conn = get_db()
            user_data = conn.execute("SELECT security_question, security_answer FROM users WHERE nick = ?", (reset_nick,)).fetchone()
            conn.close()
            
            if user_data:
                pregunta = user_data["security_question"]
                respuesta_real = user_data["security_answer"]
                
                if not pregunta or not respuesta_real:
                    st.warning("Esta cuenta no tiene configurada una pregunta de seguridad. Contacta a soporte.")
                else:
                    st.info(f"**Pregunta de Seguridad Registrada:** {pregunta}")
                    user_answer_attempt = st.text_input("Tu Respuesta Secreta:", key="reset_answer_attempt")
                    new_password_attempt = st.text_input("Nueva Password (5 caracteres alfanuméricos):", max_chars=5, type="password", key="reset_new_pass")

                    if st.button("Validar Identidad y Actualizar Contraseña", type="primary", use_container_width=True):
                        if not user_answer_attempt.strip():
                            st.error("Debes ingresar la respuesta a la pregunta de seguridad.")
                        elif user_answer_attempt.strip().lower() != respuesta_real.strip().lower():
                            st.error("❌ Respuesta de seguridad incorrecta. Validación de identidad fallida.")
                        elif not re.match(r"^[a-zA-Z0-9]{5}$", new_password_attempt):
                            st.error("⚠️ La nueva password debe tener exactamente 5 caracteres alfanuméricos.")
                        else:
                            conn = get_db()
                            conn.execute("UPDATE users SET password = ? WHERE nick = ?", (new_password_attempt, reset_nick))
                            conn.commit()
                            conn.close()
                            st.success("✅ ¡Identidad verificada exitosamente! Tu contraseña ha sido actualizada. Ya puedes ir a 'Iniciar Sesión'.")
            else:
                st.error("No se encontró ningún usuario con ese Nick en la base de datos.")

    st.stop()

# -------------------------------------------------------------
# 7. ENTORNO ACTIVO: VERIFICACIÓN DE NUEVO DÍA & GENERACIÓN
# -------------------------------------------------------------
current_profile = get_user_profile(st.session_state.auth_user)
today_date_str = datetime.now().strftime("%Y-%m-%d")

# VERIFICACIÓN DE NUEVO DÍA EN SQLITE
cached_today = get_stored_daily_insight(st.session_state.auth_user, today_date_str)

if cached_today is not None and st.session_state.daily_evaluation is None:
    # Mismo día: Cargar instantáneamente de SQLite
    st.session_state.daily_evaluation = {
        "potencial_y_fortalezas": cached_today["potencial_y_fortalezas"],
        "consejo_bienestar": cached_today["consejo_bienestar"]
    }
    st.session_state.suggested_contacts_cache = cached_today["contacts"]
    st.session_state.evaluation_date = cached_today["date_str"]
elif st.session_state.daily_evaluation is None:
    # NUEVO DÍA DETECTADO: Llamada a Gemini
    with st.spinner(f"📅 Detectado nuevo día ({today_date_str}). Gemini sincronizando tu potencial, bienestar y contactos..."):
        st.session_state.daily_evaluation = generate_empowered_daily_insight(
            client, st.session_state.auth_user, current_profile, st.session_state.lang
        )
        other_candidates = get_other_profiles_from_db(st.session_state.auth_user)
        st.session_state.suggested_contacts_cache = find_db_affinities(
            client, st.session_state.auth_user, current_profile, other_candidates, st.session_state.lang
        )
        save_stored_daily_insight(
            st.session_state.auth_user,
            today_date_str,
            st.session_state.daily_evaluation,
            st.session_state.suggested_contacts_cache
        )
        st.session_state.evaluation_date = today_date_str

# Cabecera con Logo
logo_img_tag = f'<img src="data:image/jpeg;base64,{logo_b64}" class="nexus-logo-header">' if logo_b64 else '💠 '
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
    <div style="display: flex; align-items: center;">
        {logo_img_tag}
        <div>
            <h2 style="margin: 0;">Sesión Activa: <span style="color: #6366F1;">{st.session_state.auth_user}</span></h2>
            <span class="nexus-badge badge-green">Conexión Soberana Cifrada</span>
        </div>
    </div>
    <div>
        <span class="nexus-badge badge-cyan">Fecha Sincronizada: {st.session_state.evaluation_date}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SECCIÓN FIJA DUAL: POTENCIAL/BIENESTAR + CONTACTOS SQLITE
# -------------------------------------------------------------
col_insight, col_contactos = st.columns([1, 1])

# COLUMNA 1: Potencial Latente ("De lo que eres capaz") + Consejo de Bienestar
with col_insight:
    insight = st.session_state.daily_evaluation
    st.markdown(f"""
    <div class="empower-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span class="nexus-badge badge-purple">⚡ De lo que eres capaz (Fortalezas & Potencial)</span>
            <small style="color: #94A3B8;">Análisis Gemini del Día</small>
        </div>
        <p style="font-size: 1.02rem; line-height: 1.6; margin: 0 0 14px 0; color: #F1F5F9; font-weight: 500;">
            {insight.get('potencial_y_fortalezas')}
        </p>
        <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 10px; margin-top: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span class="nexus-badge badge-green">⚖️ Equilibrio & Bienestar Diario</span>
                <small style="color: #64748B;">{st.session_state.evaluation_date}</small>
            </div>
            <p style="font-size: 0.95rem; line-height: 1.5; margin: 0; color: #CBD5E1; font-style: italic;">
                "{insight.get('consejo_bienestar')}"
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🔄 Forzar Recalibración Manual con Gemini", use_container_width=True):
        clear_stored_daily_insight(st.session_state.auth_user)
        st.session_state.daily_evaluation = None
        st.session_state.suggested_contacts_cache = None
        st.rerun()

# COLUMNA 2: Sinergias Sugeridas en SQLite
with col_contactos:
    st.markdown(f"""
    <div class="network-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span class="nexus-badge badge-cyan">🤝 Sinergias Sugeridas en la Base de Datos</span>
            <small style="color: #94A3B8;">Afinidad 1-a-1 Ciega</small>
        </div>
        <p style="color: #94A3B8; font-size: 0.82rem; margin: 0 0 10px 0;">
            Cruce de instrucción, estilo de vida, pasatiempos y metas:
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    sugerencias = st.session_state.suggested_contacts_cache
    if not sugerencias:
        st.info("No hay suficientes perfiles en la base de datos para contrastar hoy.")
    else:
        for item in sugerencias:
            is_unmasked = item["nick_real"] in st.session_state.unmasked_contacts
            display_title = f"👤 {item['nick_real']}" if is_unmasked else item["codigo_ciego"]
            badge_class = "badge-green" if is_unmasked else "badge-purple"
            
            st.markdown(f"""
            <div class="contact-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>{display_title}</strong>
                    <span class="nexus-badge {badge_class}">{item['score']}% Sinergia</span>
                </div>
                <p style="color: #CBD5E1; font-size: 0.85rem; margin: 5px 0;">{item['motivo']}</p>
                <small style="color: #6366F1;">{item['dimension']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            if not is_unmasked:
                if st.button(f"👁️ Solicitar Desclasificación Mutua ({item['codigo_ciego']})", key=f"unmask_db_{item['nick_real']}", use_container_width=True):
                    st.session_state.unmasked_contacts.add(item["nick_real"])
                    st.rerun()

st.divider()

# -------------------------------------------------------------
# 8. Pestañas de Trabajo y Configuración
# -------------------------------------------------------------
tab_web_scout, tab_chat_ia, tab_profile_edit, tab_report, tab_admin = st.tabs([
    "🌐 Oportunidades Web (Empleo & Inversión)",
    "💬 El Chat del Consejero IA",
    "📝 Mi Perfil & Estilo de Vida",
    "📄 Reporte Ejecutivo 360°",
    "👑 Administración Central" if st.session_state.auth_role == "admin" else "ℹ️ Información"
])

# TAB 1: RASTREO WEB CON GOOGLE SEARCH GROUNDING
with tab_web_scout:
    st.markdown("### 🌐 Radar de Oportunidades Web en Vivo (Google Search)")
    st.caption("Gemini rastrea ofertas laborales e inversiones reales en internet, filtradas por tus competencias, pasatiempos y estilo de vida.")

    col_cat, col_btn = st.columns([2, 1])
    with col_cat:
        scout_type = st.radio("Enfoque de búsqueda:", ["💼 Ofertas de Empleo", "📈 Inversión y Proyectos", "Ambos"], horizontal=True)
    with col_btn:
        st.write("")
        run_search = st.button("🚀 Rastrear Oportunidades con Gemini", type="primary", use_container_width=True)

    if run_search:
        with st.spinner("Gemini rastreando la web en tiempo real con Google Search..."):
            st.session_state.web_opportunities_cache = search_web_opportunities(
                client, st.session_state.auth_user, current_profile, st.session_state.lang, scout_type
            )

    if st.session_state.web_opportunities_cache:
        st.markdown(f"""
        <div class="scout-card">
            <span class="nexus-badge badge-gold" style="margin-bottom: 8px;">Reporte Grounded por Google Search</span>
            {st.session_state.web_opportunities_cache}
        </div>
        """, unsafe_allow_html=True)

# TAB 2: CHAT DEL CONSEJERO IA
with tab_chat_ia:
    st.markdown("### 💬 El Chat del Consejero IA")
    st.caption("Tu mentor soberano: cálido, reflexivo, equilibrado y perspicaz. Considera todas tus facetas diarias.")

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        if st.button("🎯 Alineación de Metas", use_container_width=True):
            st.session_state.quick_prompt_query = "¿Cómo enfocar mis fortalezas hacia mis metas sin descuidar mi estilo de vida y pasatiempos?"
    with col_p2:
        if st.button("💼 Dilema Profesional", use_container_width=True):
            st.session_state.quick_prompt_query = "Ayúdame a evaluar una decisión laboral basada en mi formación técnica y mi necesidad de balance personal."
    with col_p3:
        if st.button("🧘 Superar Bloqueo", use_container_width=True):
            st.session_state.quick_prompt_query = "Tengo fricción con mi entorno o un bloqueo de energía. Dame perspectiva recordando mis logros."

    chat_history = load_chat_history(st.session_state.auth_user)
    for msg in chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Escribe tu duda, decisión o situación para conversar con tu Consejero...")
    query_to_process = st.session_state.quick_prompt_query if st.session_state.quick_prompt_query else user_input

    if query_to_process:
        st.session_state.quick_prompt_query = None
        save_chat_message(st.session_state.auth_user, "user", query_to_process)
        with st.chat_message("user"):
            st.markdown(query_to_process)

        with st.spinner("Tu Consejero reflexionando con calidez y sabiduría..."):
            lang_name = {"es": "Spanish", "en": "English", "fr": "French", "it": "Italian"}.get(st.session_state.lang, "Spanish")
            
            consejero_master_system_prompt = f"""
            Eres el Consejero Soberano y Mentor Personal de {st.session_state.auth_user}.

            PERSONALIDAD Y TONO:
            - Cálida, reflexiva, equilibrada y perspicaz. Responde siempre con sabiduría y apoyo constructivo.

            CONTEXTO VITAL CONFIDENCIAL DEL USUARIO:
            - INSTRUCCIÓN Y EDUCACIÓN: {current_profile.get('instruccion')}
            - PROFESIÓN: {current_profile.get('profesion')}
            - ESTILO DE VIDA, PASATIEMPOS E INTERESES: {current_profile.get('estilo_vida_hobbies_intereses')}
            - PENSAMIENTO POLÍTICO-RELIGIOSO: {current_profile.get('pensamiento_politico_religioso')}
            - ENTORNO SOCIAL: {current_profile.get('entorno_social')}
            - MOTORES, DEPORTE Y FÍSICO: {current_profile.get('personal_motores')}
            - METAS DE VIDA: {current_profile.get('metas')}
            - FRUSTRACIONES O BLOQUEOS: {current_profile.get('frustraciones')}
            - LOGROS Y VICTORIAS: {current_profile.get('logros')}

            REGLAS:
            1. Respuestas de mentor maduro, perspicaz y elegante.
            2. Conecta sus pasatiempos, su rigor técnico y sus principios éticos.
            3. Idioma: {lang_name}.
            """
            
            resp = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=query_to_process, 
                config=types.GenerateContentConfig(system_instruction=consejero_master_system_prompt)
            )
            save_chat_message(st.session_state.auth_user, "assistant", resp.text)
            st.rerun()

# TAB 3: EDICIÓN DE PERFIL & ESTILO DE VIDA EN SQLITE
with tab_profile_edit:
    st.markdown("### Configuración de Perfil & Estilo de Vida (`nexus_core.db`)")
    st.caption("Cualquier cambio recalibrará la base de datos y forzará una nueva evaluación de Gemini.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        e_prof = st.text_input("Profesión y Rol Actual:", value=current_profile.get("profesion", ""))
        e_inst = st.text_area("Instrucción y Formación Académica:", value=current_profile.get("instruccion", ""), height=80)
        e_estilo = st.text_area("Estilo de Vida, Pasatiempos e Intereses:", value=current_profile.get("estilo_vida_hobbies_intereses", ""), height=90)
        e_pol = st.text_area("Pensamiento Político-Religioso y Convicciones:", value=current_profile.get("pensamiento_politico_religioso", ""), height=80)
    with col_b:
        e_soc = st.text_area("Entorno Social y Tradición Cultural:", value=current_profile.get("entorno_social", ""), height=80)
        e_mot = st.text_area("Pasiones Mecánicas (Autos, Motos, Aviones) y Deporte:", value=current_profile.get("personal_motores", ""), height=80)
        e_met = st.text_input("Grandes Metas de Vida:", value=current_profile.get("metas", ""))
        e_fru = st.text_input("Frustraciones o Fricciones Actuales:", value=current_profile.get("frustraciones", ""))
        e_log = st.text_input("Logros y Razones de Orgullo:", value=current_profile.get("logros", ""))

    if st.button("💾 Guardar y Actualizar en Base de Datos", type="primary"):
        updated_dict = {
            "profesion": e_prof.strip(),
            "instruccion": e_inst.strip(),
            "estilo_vida_hobbies_intereses": e_estilo.strip(),
            "pensamiento_politico_religioso": e_pol.strip(),
            "entorno_social": e_soc.strip(),
            "personal_motores": e_mot.strip(),
            "metas": e_met.strip(),
            "frustraciones": e_fru.strip(),
            "logros": e_log.strip()
        }
        update_user_profile(st.session_state.auth_user, updated_dict)
        clear_stored_daily_insight(st.session_state.auth_user)
        st.session_state.daily_evaluation = None
        st.session_state.suggested_contacts_cache = None
        st.session_state.web_opportunities_cache = None
        st.success("✅ Perfil y estilo de vida actualizados. Se ha programado una nueva sincronización con Gemini.")
        st.rerun()

# TAB 4: REPORTE EJECUTIVO 360°
with tab_report:
    st.markdown("### 📄 Generador de Reporte Ejecutivo 360°")
    if st.button("⚡ Compilar Reporte Completo desde SQLite", type="primary"):
        with st.spinner("Compilando auditoría formal directamente con Gemini..."):
            rep_prompt = f"Genera un reporte 360° en Markdown analizando con profundidad, sabiduría y apoyo el perfil de {st.session_state.auth_user}: {json.dumps(current_profile, ensure_ascii=False)}."
            res = client.models.generate_content(model="gemini-2.5-flash", contents=rep_prompt)
            st.download_button("📥 Descargar Reporte (.md)", data=res.text, file_name=f"Reporte_{st.session_state.auth_user}.md", mime="text/markdown")
            st.markdown(f'<div class="nexus-card">{res.text}</div>', unsafe_allow_html=True)

# TAB 5: PANEL DE ADMINISTRADOR ('nesu' / '0000')
with tab_admin:
    if st.session_state.auth_role == "admin":
        st.markdown("### 👑 Supervisión de Base de Datos y Utentes")
        conn = get_db()
        df_all = pd.read_sql_query("SELECT u.id, u.nick, u.status, u.role, p.profesion, p.instruccion, p.updated_at FROM users u LEFT JOIN profiles p ON u.nick = p.user_nick", conn)
        conn.close()
        st.dataframe(df_all, use_container_width=True)
    else:
        st.markdown("### Información del Sistema")
        st.write("Tu sesión opera bajo el protocolo Zero-Knowledge Enclave de Nexus OS.")
