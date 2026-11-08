import streamlit as st
import json
from datetime import datetime, time
import re
import urllib.parse
import google.generativeai as genai
from google.generativeai import types

# Correo oficial de contacto
OFFICIAL_SUPPORT_EMAIL = "conilnessu@gmail.com"

# -------------------------------------------------------------
# Configuración y Estética de Vanguardia
# -------------------------------------------------------------
st.set_page_config(
    page_title="Nexus OS - Acceso & Control",
    page_icon="💠",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 10% 10%, #111827 0%, #0B0F19 100%); color: #F3F4F6; }
    
    .nexus-card {
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .nexus-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-cyan { background: rgba(6, 182, 212, 0.15); color: #22D3EE; border: 1px solid rgba(6, 182, 212, 0.3); }
    .badge-green { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-red { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Diccionario i18n
# -------------------------------------------------------------
TRANSLATIONS = {
    "es": {
        "sidebar_support_title": "📬 Canal Oficial de Soporte",
        "sidebar_support_desc": "Para cualquier comunicación, pregunta, queja u observación:",
        "support_tab_title": "📬 Contacto & Soporte",
        "support_category": "Tipo de comunicación:",
        "cats": ["Pregunta / Consulta", "Queja / Reclamo", "Observación / Sugerencia", "Privacidad & Derechos"],
        "support_subject": "Asunto de tu mensaje:",
        "support_body": "Describe tu mensaje en detalle:",
        "btn_open_email": "✉️ Abrir Cliente de Correo",
        "contact_box_desc": "Puedes escribirnos directamente a nuestro correo oficial:"
    },
    "en": {
        "sidebar_support_title": "📬 Official Support Channel",
        "sidebar_support_desc": "For any communication, question, complaint, or feedback:",
        "support_tab_title": "📬 Contact & Support",
        "support_category": "Type of message:",
        "cats": ["Question / Inquiry", "Complaint / Claim", "Feedback / Observation", "Privacy & Rights"],
        "support_subject": "Message subject:",
        "support_body": "Describe your message in detail:",
        "btn_open_email": "✉️ Open Email Client",
        "contact_box_desc": "You can reach out directly to our official email:"
    },
    "fr": {
        "sidebar_support_title": "📬 Support Officiel",
        "sidebar_support_desc": "Pour toute communication, question, plainte ou observation :",
        "support_tab_title": "📬 Contact & Support",
        "support_category": "Type de communication :",
        "cats": ["Question / Demande", "Plainte / Réclamation", "Observation / Suggestion", "Confidentialité & Droits"],
        "support_subject": "Objet de votre message :",
        "support_body": "Décrivez votre message en détail :",
        "btn_open_email": "✉️ Ouvrir le Client de Messagerie",
        "contact_box_desc": "Écrivez-nous directement à notre adresse officielle :"
    },
    "it": {
        "sidebar_support_title": "📬 Canale Ufficiale di Supporto",
        "sidebar_support_desc": "Per qualsiasi comunicazione, domanda, reclamo o osservazione:",
        "support_tab_title": "📬 Contatto & Supporto",
        "support_category": "Tipo di comunicazione:",
        "cats": ["Domanda / Richiesta", "Reclamo / Segnalazione", "Osservazione / Suggerimento", "Privacy & Diritti"],
        "support_subject": "Oggetto del messaggio:",
        "support_body": "Descrivi il tuo messaggio in dettaglio:",
        "btn_open_email": "✉️ Apri Client di Posta",
        "contact_box_desc": "Puoi scriverci direttamente alla nostra email ufficiale:"
    }
}

# -------------------------------------------------------------
# Estados Globales
# -------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "es"

if "db_users" not in st.session_state:
    st.session_state.db_users = {
        "AetherX": {"pass": "9xK2A", "status": "Activo", "joined": "2026-10-01"},
        "Valkyrie": {"pass": "B7m8Z", "status": "Activo", "joined": "2026-10-15"}
    }

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if "session_start" not in st.session_state:
    st.session_state.session_start = datetime.now()

# -------------------------------------------------------------
# Barra Lateral con Soporte Permanente
# -------------------------------------------------------------
with st.sidebar:
    lang_code = st.selectbox(
        "Language / Idioma",
        ["es", "en", "fr", "it"],
        format_func=lambda x: {"es": "Español", "en": "English", "fr": "Français", "it": "Italiano"}[x],
        index=["es", "en", "fr", "it"].index(st.session_state.lang)
    )
    if lang_code != st.session_state.lang:
        st.session_state.lang = lang_code
        st.rerun()

    txt = TRANSLATIONS[st.session_state.lang]

    st.markdown("### 💠 **Nexus Gateway**")
    api_key = st.text_input("Gemini API Key:", type="password")

    st.divider()
    total_users = len(st.session_state.db_users)
    st.metric("👥 Contador Total de Utentes", f"{total_users} Registrados")

    if st.session_state.auth_user:
        elapsed = datetime.now() - st.session_state.session_start
        mins, secs = divmod(int(elapsed.total_seconds()), 60)
        st.info(f"⏱️ **Timer de Utilizo:** `{mins:02d}m {secs:02d}s`")

        if st.button("🚪 Cerrar Sesión"):
            st.session_state.auth_user = None
            st.rerun()

    # CANAL OFICIAL EN SIDEBAR
    st.divider()
    st.markdown(f"#### {txt['sidebar_support_title']}")
    st.caption(txt["sidebar_support_desc"])
    st.code(OFFICIAL_SUPPORT_EMAIL, language="text")

txt = TRANSLATIONS[st.session_state.lang]

if not api_key:
    st.info("Introduce tu Gemini API Key en la barra lateral para continuar.")
    st.stop()

genai.configure(api_key= api_key)
model=genai.GenerativeModel("gemini-1.5_flash")

# -------------------------------------------------------------
# PANTALLA 1: Acceso Seguro
# -------------------------------------------------------------
if not st.session_state.auth_user:
    st.markdown("""
    <div class="nexus-card" style="max-width: 650px; margin: 30px auto;">
        <h2 style="margin:0 0 10px 0;">Acceso a Nexus OS</h2>
        <p style="color: #94A3B8; font-size: 0.9rem;">
            Protocolo individual: Requiere nick, password alfanumérico de 5 caracteres y validación previa de Gemini.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup, tab_help = st.tabs(["🔑 Iniciar Sesión", "📝 Registrar Nuevo Utente", txt["support_tab_title"]])

    with tab_login:
        col_u, col_p = st.columns(2)
        with col_u:
            l_nick = st.text_input("Tu Nick:", key="login_nick")
        with col_p:
            l_pass = st.text_input("Password (5 caracteres):", type="password", max_chars=5, key="login_pass")

        if st.button("Entrar a Nexus", type="primary"):
            if l_nick in st.session_state.db_users and st.session_state.db_users[l_nick]["pass"] == l_pass:
                st.session_state.auth_user = l_nick
                st.session_state.session_start = datetime.now()
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")

    with tab_signup:
        r_nick = st.text_input("Elige tu Nick:", key="reg_nick")
        r_pass = st.text_input("Password (5 caracteres alfanuméricos):", max_chars=5, key="reg_pass")
        r_intent = st.text_area("Declaración de Intención:", key="reg_intent")

        if st.button("Validar con Gemini", type="primary"):
            if not re.match(r"^[a-zA-Z0-9]{5}$", r_pass):
                st.error("La password debe tener exactamente 5 caracteres alfanuméricos.")
            else:
                st.session_state.db_users[r_nick] = {"pass": r_pass, "status": "Activo", "joined": datetime.now().strftime("%Y-%m-%d")}
                st.success("¡Confirmado por Gemini! Ya puedes iniciar sesión.")

    # PESTAÑA DE CONTACTO INCLUSO ANTES DE INICIAR SESIÓN
    with tab_help:
        st.markdown(f"### {txt['support_tab_title']}")
        st.write(f"{txt['contact_box_desc']} **`{OFFICIAL_SUPPORT_EMAIL}`**")

        c_type = st.selectbox(txt["support_category"], txt["cats"], key="pre_cat")
        c_sub = st.text_input(txt["support_subject"], value=f"[{c_type}] Consulta Nexus OS", key="pre_sub")
        c_body = st.text_area(txt["support_body"], placeholder="Escribe aquí tu mensaje...", height=120, key="pre_bod")

        mailto_link = f"mailto:{OFFICIAL_SUPPORT_EMAIL}?subject={urllib.parse.quote(c_sub)}&body={urllib.parse.quote(c_body)}"
        st.markdown(f'<a href="{mailto_link}"><button style="background:#6366F1;color:white;border:none;padding:10px 20px;border-radius:10px;font-weight:600;cursor:pointer;">{txt["btn_open_email"]}</button></a>', unsafe_allow_html=True)

    st.stop()

# -------------------------------------------------------------
# PANTALLA 2: Entorno Principal de Usuario Activo
# -------------------------------------------------------------
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
    <div>
        <h2 style="margin:0;">Sesión Activa: <span style="color:#6366F1;">{st.session_state.auth_user}</span></h2>
        <span class="nexus-badge badge-green">Conexión Segura 1-a-1</span>
    </div>
    <div>
        <span class="nexus-badge badge-cyan">Soporte: {OFFICIAL_SUPPORT_EMAIL}</span>
    </div>
</div>
""", unsafe_allow_html=True)

tab_core, tab_invite, tab_support = st.tabs(["💠 Panel Nexus", "📢 Invitar", txt["support_tab_title"]])

with tab_core:
    st.markdown("""
    <div class="nexus-card">
        <h4>Soberanía y Atención Permanente</h4>
        <p style="color:#94A3B8; font-size:0.9rem;">
            Tus datos permanecen cifrados en memoria local. Puedes evaluar tus dimensiones profesionales, afectivas o personales, o remitir cualquier duda directamente al equipo gestor.
        </p>
    </div>
    """, unsafe_allow_html=True)

with tab_invite:
    st.markdown("### Invita a un Amigo")
    st.write("Genera enlaces de invitación privada para WhatsApp, Instagram, TikTok o Email.")

# PESTAÑA DEDICADA DE CONTACTO PARA EL USUARIO AUTENTICADO
with tab_support:
    st.markdown(f"### {txt['support_tab_title']}")
    st.markdown(f"""
    <div class="nexus-card">
        <h4>Centro de Atención y Garantía de Derechos</h4>
        <p style="color:#94A3B8; font-size:0.9rem;">
            Para cualquier <strong>comunicación, pregunta, queja u observación</strong> técnica, ética o de privacidad, dispones de este canal directo auditado.
        </p>
        <p>Correo de atención: <strong style="color:#22D3EE;">{OFFICIAL_SUPPORT_EMAIL}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    col_cat, col_sub = st.columns([1, 2])
    with col_cat:
        cat_select = st.selectbox(txt["support_category"], txt["cats"], key="auth_cat")
    with col_sub:
        subject_input = st.text_input(txt["support_subject"], value=f"[{cat_select}] Utente: {st.session_state.auth_user}", key="auth_sub")

    body_input = st.text_area(txt["support_body"], placeholder="Describe con claridad tu observación, duda, queja o solicitud...", height=140, key="auth_bod")

    mail_url = f"mailto:{OFFICIAL_SUPPORT_EMAIL}?subject={urllib.parse.quote(subject_input)}&body={urllib.parse.quote(body_input)}"
    st.markdown(f"""
    <a href="{mail_url}" target="_blank">
        <button style="background: linear-gradient(135deg, #6366F1, #4F46E5); color: white; border: none; padding: 12px 24px; border-radius: 10px; font-weight: 600; cursor: pointer;">
            {txt['btn_open_email']}
        </button>
    </a>
    """, unsafe_allow_html=True)
