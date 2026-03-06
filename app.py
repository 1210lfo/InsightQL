"""
InsightQL - Demo Frontend Premium
Interfaz Streamlit con branding Blacksmith Research
"""

import streamlit as st
import streamlit.components.v1 as components
import asyncio
import re
from datetime import datetime

# Configuración de página - DEBE IR PRIMERO
st.set_page_config(
    page_title="InsightQL | Blacksmith Research",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Importar el agente y seguridad
from src.agent.graph import run_analytics_query, run_voice_query
from src.config import get_config
from src.security import (
    sanitize_error,
    validate_user_input,
    get_rate_limiter,
    audit_log,
    RateLimitError,
)

# Logo de Blacksmith Research
BLACKSMITH_LOGO = "https://blacksmithresearch.com/wp-content/uploads/2025/03/IsoColor.svg"

# =============================================================================
# ESTILOS CSS - Diseño Profesional Corregido
# =============================================================================

st.markdown("""
<style>
    /* Importar fuentes */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Variables de colores */
    :root {
        --primary: #0066cc;
        --primary-dark: #1a237e;
        --primary-light: #e8f4fd;
        --accent: #ff6b35;
        --accent-light: #fff3ef;
        --success: #10b981;
        --success-light: #d1fae5;
        --purple: #8b5cf6;
        --purple-light: #ede9fe;
        --gray-50: #f9fafb;
        --gray-100: #f3f4f6;
        --gray-200: #e5e7eb;
        --gray-500: #6b7280;
        --gray-700: #374151;
        --gray-900: #111827;
        --white: #ffffff;
    }
    
    /* Base */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%);
    }
    
    /* Ocultar elementos Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--white) 0%, var(--gray-50) 100%);
        border-right: 1px solid var(--gray-200);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding: 1.5rem 1rem;
    }
    
    .sidebar-logo {
        text-align: center;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, var(--primary-light) 0%, var(--white) 100%);
        border-radius: 16px;
        border: 1px solid var(--gray-200);
    }
    
    .sidebar-logo img {
        height: 48px;
        margin-bottom: 0.5rem;
    }
    
    .sidebar-logo h2 {
        color: var(--primary-dark);
        font-size: 1.25rem;
        font-weight: 700;
        margin: 0;
    }
    
    .sidebar-logo span {
        color: var(--gray-500);
        font-size: 0.75rem;
    }
    
    .sidebar-title {
        font-size: 0.7rem;
        font-weight: 700;
        color: var(--gray-500);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 1rem 0 0.75rem 0.5rem;
    }
    
    .catalog-stats {
        background: var(--white);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid var(--gray-200);
    }
    
    .stat-row {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--gray-100);
    }
    
    .stat-row:last-child { border-bottom: none; }
    
    .stat-label { color: var(--gray-500); font-size: 0.85rem; }
    .stat-value { color: var(--primary-dark); font-weight: 600; }
    
    /* Botones sidebar */
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        background: var(--white) !important;
        color: var(--gray-700) !important;
        border: 1px solid var(--gray-200) !important;
        border-radius: 10px !important;
        padding: 0.625rem 0.875rem !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        transition: all 0.2s ease !important;
        margin-bottom: 0.375rem !important;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        color: var(--white) !important;
        border-color: var(--primary) !important;
        transform: translateX(4px) !important;
    }
    
    /* ========== HEADER ========== */
    .main-header {
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 50%, #4f46e5 100%);
        padding: 2rem 2.5rem;
        border-radius: 20px;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1);
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 60%;
        height: 200%;
        background: radial-gradient(ellipse, rgba(255,255,255,0.1) 0%, transparent 70%);
    }
    
    .header-content {
        position: relative;
        z-index: 1;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .header-text h1 {
        color: var(--white);
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
    }
    
    .header-text p {
        color: rgba(255,255,255,0.85);
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
    }
    
    .header-logo {
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 0.75rem;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .header-logo img { height: 40px; }
    
    /* ========== MÉTRICAS ========== */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background: var(--white);
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid var(--gray-100);
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--primary) 0%, var(--primary-dark) 100%);
    }
    
    .metric-card.orange::before { background: linear-gradient(90deg, var(--accent) 0%, #e55a2b 100%); }
    .metric-card.green::before { background: linear-gradient(90deg, var(--success) 0%, #059669 100%); }
    .metric-card.purple::before { background: linear-gradient(90deg, var(--purple) 0%, #7c3aed 100%); }
    
    .metric-icon {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        margin-bottom: 0.75rem;
        background: var(--primary-light);
    }
    
    .metric-card.orange .metric-icon { background: var(--accent-light); }
    .metric-card.green .metric-icon { background: var(--success-light); }
    .metric-card.purple .metric-icon { background: var(--purple-light); }
    
    .metric-value {
        font-size: 1.75rem;
        font-weight: 800;
        color: var(--gray-900);
        line-height: 1;
    }
    
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--gray-500);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.375rem;
    }
    
    /* ========== WHATSAPP-STYLE CHAT ========== */
    .wa-chat-wrap {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 8px 30px rgb(0 0 0 / 0.12);
        border: 1px solid var(--gray-200);
        margin-bottom: 1.5rem;
    }

    /* Top bar */
    .wa-topbar {
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
        padding: 0.75rem 1.25rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .wa-topbar-avatar {
        width: 40px; height: 40px;
        border-radius: 50%;
        background: rgba(255,255,255,0.2);
        display: flex; align-items: center; justify-content: center;
        font-size: 1.2rem; color: white;
    }
    .wa-topbar-info h3 { margin: 0; font-size: 0.95rem; font-weight: 600; color: white; }
    .wa-topbar-info span { font-size: 0.7rem; color: rgba(255,255,255,0.7); }

    /* Messages area — WhatsApp wallpaper */
    .wa-messages {
        background-color: #efeae2;
        background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23d5ced6' fill-opacity='0.18'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        padding: 1rem 1.25rem;
        min-height: 420px;
        max-height: 520px;
        overflow-y: auto;
    }

    /* Bubbles — user (right, green) */
    .wa-row-user { display: flex; justify-content: flex-end; margin-bottom: 0.5rem; }
    .wa-bubble-user {
        background: #d9fdd3;
        color: #111b21;
        padding: 0.5rem 0.65rem 0.35rem;
        border-radius: 10px 10px 2px 10px;
        max-width: 75%;
        font-size: 0.9rem; line-height: 1.55;
        box-shadow: 0 1px 1px rgb(0 0 0 / 0.08);
        position: relative;
    }
    .wa-bubble-user::after {
        content: '';
        position: absolute; top: 0; right: -7px;
        border-width: 0 0 10px 8px;
        border-style: solid;
        border-color: transparent transparent transparent #d9fdd3;
    }

    /* Bubbles — assistant (left, white) */
    .wa-row-bot { display: flex; justify-content: flex-start; margin-bottom: 0.5rem; }
    .wa-bubble-bot {
        background: #ffffff;
        color: #111b21;
        padding: 0.5rem 0.65rem 0.35rem;
        border-radius: 10px 10px 10px 2px;
        max-width: 80%;
        font-size: 0.9rem; line-height: 1.6;
        box-shadow: 0 1px 1px rgb(0 0 0 / 0.08);
        position: relative;
    }
    .wa-bubble-bot::after {
        content: '';
        position: absolute; top: 0; left: -7px;
        border-width: 0 8px 10px 0;
        border-style: solid;
        border-color: transparent #ffffff transparent transparent;
    }
    .wa-bubble-bot strong { color: #111b21; font-weight: 600; }

    /* Timestamp */
    .wa-time {
        font-size: 0.65rem; color: #667781;
        text-align: right; margin-top: 0.2rem;
        display: flex; justify-content: flex-end; align-items: center; gap: 0.25rem;
    }
    .wa-time .wa-check { color: #53bdeb; }

    /* Voice badge */
    .wa-voice-badge {
        display: inline-flex; align-items: center; gap: 0.3rem;
        background: #e2f7cb; border-radius: 20px;
        padding: 0.15rem 0.5rem; font-size: 0.7rem; color: #2d6a1e;
        margin-bottom: 0.2rem; font-weight: 500;
    }

    /* Day divider */
    .wa-day-divider {
        text-align: center; margin: 0.75rem 0;
    }
    .wa-day-divider span {
        background: #e1dede; color: #54656f;
        padding: 0.25rem 0.75rem; border-radius: 8px;
        font-size: 0.7rem; font-weight: 500;
    }
    
    /* ========== WHATSAPP INPUT BAR ========== */
    .wa-input-bar {
        background: #f0f2f5;
        padding: 0.5rem 1rem;
        border-top: 1px solid var(--gray-200);
    }

    /* Style Streamlit chat_input to look like WhatsApp */
    [data-testid="stChatInput"] {
        border-radius: 24px !important;
        border: none !important;
        background: var(--white) !important;
        box-shadow: 0 1px 2px rgb(0 0 0 / 0.08) !important;
        padding: 0.15rem 0.25rem !important;
    }
    [data-testid="stChatInput"]:focus-within {
        box-shadow: 0 1px 4px rgb(0 0 0 / 0.12) !important;
    }

    /* Audio input compact style */
    [data-testid="stAudioInput"] {
        margin-bottom: 0 !important;
    }
    [data-testid="stAudioInput"] > label {
        font-size: 0.8rem !important;
        color: var(--gray-500) !important;
    }
    
    /* ========== CAPACIDADES ========== */
    .capabilities-title {
        text-align: center;
        margin: 2rem 0 1.5rem 0;
    }
    
    .capabilities-title h2 {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--gray-900);
        margin: 0;
    }
    
    .capabilities-title p {
        color: var(--gray-500);
        font-size: 0.9rem;
        margin: 0.5rem 0 0 0;
    }
    
    .capability-card {
        background: var(--white);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid var(--gray-100);
        transition: all 0.3s ease;
    }
    
    .capability-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    
    .capability-icon {
        width: 56px;
        height: 56px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin: 0 auto 1rem auto;
    }
    
    .capability-card.blue .capability-icon { background: var(--primary-light); }
    .capability-card.orange .capability-icon { background: var(--accent-light); }
    .capability-card.green .capability-icon { background: var(--success-light); }
    .capability-card.purple .capability-icon { background: var(--purple-light); }
    
    .capability-card h4 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--gray-900);
        margin: 0 0 0.5rem 0;
    }
    
    .capability-card p {
        font-size: 0.85rem;
        color: var(--gray-500);
        margin: 0;
        line-height: 1.5;
    }
    
    /* ========== FOOTER ========== */
    .footer {
        text-align: center;
        padding: 2rem 1rem;
        margin-top: 2rem;
        background: var(--white);
        border-radius: 16px;
        border: 1px solid var(--gray-200);
    }
    
    .footer strong {
        color: var(--gray-900);
    }
    
    .footer a {
        color: var(--primary);
        text-decoration: none;
        font-weight: 600;
    }
    
    .footer-tagline {
        color: var(--gray-500);
        font-size: 0.8rem;
        margin-top: 0.5rem;
    }
    
    /* Botón limpiar */
    .clear-btn .stButton > button {
        background: #fef2f2 !important;
        color: #dc2626 !important;
        border: 1px solid #fecaca !important;
    }
    
    .clear-btn .stButton > button:hover {
        background: #dc2626 !important;
        color: white !important;
        transform: translateX(0) !important;
    }
    
    /* Hide default streamlit chat styles */
    [data-testid="stChatMessage"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def run_query(query: str) -> dict:
    """Ejecuta una consulta al agente."""
    return asyncio.run(run_analytics_query(query))


def run_voice(audio_bytes: bytes, audio_format: str = "wav") -> dict:
    """Ejecuta una consulta por voz al agente."""
    return asyncio.run(run_voice_query(audio_bytes, audio_format))


def format_response(response: dict) -> str:
    """Formatea la respuesta del agente."""
    return response.get("answer", "No se pudo obtener una respuesta.")


def _execute_user_query(query: str) -> str:
    """Validate, rate-limit, audit, and execute a text query. Returns response string."""
    is_valid, validation_error = validate_user_input(query)
    if not is_valid:
        return f"⚠️ {validation_error}"

    limiter = get_rate_limiter()
    session_id = st.session_state.get("session_id", "anonymous")
    if not limiter.is_allowed(session_id):
        return "⏳ Demasiadas consultas. Espera unos segundos."

    audit_log("query", {"query": query[:100]}, session_id)
    result = run_query(query)
    return format_response(result)


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-logo">
        <img src="{BLACKSMITH_LOGO}" alt="Blacksmith">
        <h2>InsightQL</h2>
        <span>Analytics Agent</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-title">📊 Catálogo Conectado</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="catalog-stats">
        <div class="stat-row">
            <span class="stat-label">Marcas</span>
            <span class="stat-value">29</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Productos</span>
            <span class="stat-value">337,714</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Categorías</span>
            <span class="stat-value">4</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Disponibles</span>
            <span class="stat-value">179,781</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-title">💡 Preguntas de Ejemplo</div>', unsafe_allow_html=True)
    
    examples = [
        ("📊", "Resumen del catálogo"),
        ("👟", "Precio promedio calzado hombre"),
        ("🏷️", "Productos con mayor descuento"),
        ("📏", "Distribución de tallas"),
        ("👥", "Análisis por segmento"),
    ]
    
    for emoji, text in examples:
        if st.button(f"{emoji}  {text}", key=f"ex_{text}", use_container_width=True):
            st.session_state.pending_query = text
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    if st.button("🗑️  Limpiar conversación", key="clear", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; text-align: center;">
        <span style="color: #9ca3af; font-size: 0.7rem;">Powered by</span><br>
        <a href="https://blacksmithresearch.com" target="_blank" style="color: #ff6b35; font-weight: 600; text-decoration: none; font-size: 0.8rem;">
            Blacksmith Research
        </a>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# CONTENIDO PRINCIPAL
# =============================================================================

# Header
st.markdown(f"""
<div class="main-header">
    <div class="header-content">
        <div class="header-text">
            <h1>🔍 InsightQL</h1>
            <p>Agente Analítico Inteligente para tu Catálogo de Moda</p>
        </div>
        <div class="header-logo">
            <img src="{BLACKSMITH_LOGO}" alt="Blacksmith Research">
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Métricas
st.markdown("""
<div class="metrics-grid">
    <div class="metric-card">
        <div class="metric-icon">📦</div>
        <div class="metric-value">337,714</div>
        <div class="metric-label">Productos</div>
    </div>
    <div class="metric-card orange">
        <div class="metric-icon">🏷️</div>
        <div class="metric-value">29</div>
        <div class="metric-label">Marcas</div>
    </div>
    <div class="metric-card green">
        <div class="metric-icon">✓</div>
        <div class="metric-value">179,781</div>
        <div class="metric-label">Disponibles</div>
    </div>
    <div class="metric-card purple">
        <div class="metric-icon">💰</div>
        <div class="metric-value">$199,597</div>
        <div class="metric-label">Precio Prom.</div>
    </div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# CHAT — WhatsApp Style
# =============================================================================

# Initialize messages
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "¡Hola! 👋 Soy **InsightQL**, tu asistente analítico para el catálogo de moda.\n\n"
                   "Puedo ayudarte con:\n"
                   "• 📊 Resumen del catálogo\n"
                   "• 💰 Análisis de precios y descuentos\n"
                   "• 👥 Segmentación por público\n"
                   "• 📏 Disponibilidad y tallas\n"
                   "• 🎙️ Consultas por voz\n\n"
                   "¿Qué te gustaría saber hoy?",
        "time": datetime.now().strftime("%H:%M"),
    })


def _get_time(msg):
    return msg.get("time", "")


def _md_to_html(text: str) -> str:
    """Lightweight markdown to HTML for chat bubbles."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    lines = text.split('\n')
    out = []
    in_list = False
    for line in lines:
        s = line.strip()
        if s.startswith('• ') or s.startswith('- '):
            if not in_list:
                out.append('<ul style="margin:0.3rem 0;padding-left:1.2rem;">')
                in_list = True
            out.append(f'<li style="margin:0.15rem 0;">{s[2:]}</li>')
        else:
            if in_list:
                out.append('</ul>')
                in_list = False
            if s:
                out.append(f'{s}<br>')
    if in_list:
        out.append('</ul>')
    return ''.join(out)


# ── Build entire WhatsApp chat as ONE HTML block ──
# Using components.html() to avoid Markdown processing corruption
WA_CSS = '''
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif; background: transparent; }
.wa-chat-wrap { border-radius: 16px; overflow: hidden; box-shadow: 0 8px 30px rgb(0 0 0 / 0.12); border: 1px solid #e5e7eb; }
.wa-topbar { background: linear-gradient(135deg, #1a237e 0%, #0066cc 100%); padding: 0.75rem 1.25rem; display: flex; align-items: center; gap: 0.75rem; }
.wa-topbar-avatar { width: 40px; height: 40px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; color: white; }
.wa-topbar-info h3 { margin: 0; font-size: 0.95rem; font-weight: 600; color: white; }
.wa-topbar-info span { font-size: 0.7rem; color: rgba(255,255,255,0.7); }
.wa-messages { background-color: #efeae2; background-image: url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23d5ced6\' fill-opacity=\'0.18\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E"); padding: 1rem 1.25rem; overflow-y: auto; }
.wa-row-user { display: flex; justify-content: flex-end; margin-bottom: 0.5rem; }
.wa-bubble-user { background: #d9fdd3; color: #111b21; padding: 0.5rem 0.65rem 0.35rem; border-radius: 10px 10px 2px 10px; max-width: 75%; font-size: 0.9rem; line-height: 1.55; box-shadow: 0 1px 1px rgb(0 0 0 / 0.08); position: relative; }
.wa-bubble-user::after { content: ""; position: absolute; top: 0; right: -7px; border-width: 0 0 10px 8px; border-style: solid; border-color: transparent transparent transparent #d9fdd3; }
.wa-row-bot { display: flex; justify-content: flex-start; margin-bottom: 0.5rem; }
.wa-bubble-bot { background: #ffffff; color: #111b21; padding: 0.5rem 0.65rem 0.35rem; border-radius: 10px 10px 10px 2px; max-width: 80%; font-size: 0.9rem; line-height: 1.6; box-shadow: 0 1px 1px rgb(0 0 0 / 0.08); position: relative; }
.wa-bubble-bot::after { content: ""; position: absolute; top: 0; left: -7px; border-width: 0 8px 10px 0; border-style: solid; border-color: transparent #ffffff transparent transparent; }
.wa-bubble-bot strong { color: #111b21; font-weight: 600; }
.wa-time { font-size: 0.65rem; color: #667781; text-align: right; margin-top: 0.2rem; display: flex; justify-content: flex-end; align-items: center; gap: 0.25rem; }
.wa-time .wa-check { color: #53bdeb; }
.wa-voice-badge { display: inline-flex; align-items: center; gap: 0.3rem; background: #e2f7cb; border-radius: 20px; padding: 0.15rem 0.5rem; font-size: 0.7rem; color: #2d6a1e; margin-bottom: 0.2rem; font-weight: 500; }
.wa-day-divider { text-align: center; margin: 0.75rem 0; }
.wa-day-divider span { background: #e1dede; color: #54656f; padding: 0.25rem 0.75rem; border-radius: 8px; font-size: 0.7rem; font-weight: 500; }
</style>
'''

bubbles_html = ''
for msg in st.session_state.messages:
    t = _get_time(msg)
    is_voice = msg.get("voice", False)

    if msg["role"] == "user":
        content = msg["content"]
        content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        voice_tag = '<div class="wa-voice-badge">&#127897;&#65039; Voz</div>' if is_voice else ''
        bubbles_html += (
            '<div class="wa-row-user"><div class="wa-bubble-user">'
            f'{voice_tag}{content}'
            f'<div class="wa-time">{t} <span class="wa-check">&#10003;&#10003;</span></div>'
            '</div></div>'
        )
    else:
        content = _md_to_html(msg["content"])
        bubbles_html += (
            '<div class="wa-row-bot"><div class="wa-bubble-bot">'
            f'{content}'
            f'<div class="wa-time">{t}</div>'
            '</div></div>'
        )

full_chat = (
    WA_CSS
    + '<div class="wa-chat-wrap">'
    + '<div class="wa-topbar">'
    + '<div class="wa-topbar-avatar">&#129302;</div>'
    + '<div class="wa-topbar-info"><h3>InsightQL</h3>'
    + '<span>en l\u00ednea \u00b7 Cat\u00e1logo de Moda \u00b7 337,714 productos</span></div></div>'
    + '<div class="wa-messages">'
    + '<div class="wa-day-divider"><span>Hoy</span></div>'
    + bubbles_html
    + '</div></div>'
)

# Calculate height: base 180px + ~90px per message, capped
chat_height = min(180 + len(st.session_state.messages) * 90, 650)
components.html(full_chat, height=chat_height, scrolling=True)

# ── Voice input (compact, before text input) ──
voice_config = get_config().voice
voice_enabled = voice_config.enabled and voice_config.groq_api_key

if voice_enabled:
    audio_value = st.audio_input("🎙️ Mantén presionado para grabar", key="voice_input")

    if audio_value is not None:
        audio_bytes = audio_value.read()
        if audio_bytes and len(audio_bytes) > 100:
            audio_hash = hash(audio_bytes)
            if st.session_state.get("last_audio_hash") != audio_hash:
                st.session_state.last_audio_hash = audio_hash
                now_str = datetime.now().strftime("%H:%M")

                with st.spinner("🎙️ Transcribiendo..."):
                    try:
                        limiter = get_rate_limiter()
                        session_id = st.session_state.get("session_id", "anonymous")
                        if not limiter.is_allowed(session_id):
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": "⏳ Demasiadas consultas. Espera unos segundos.",
                                "time": now_str,
                            })
                        else:
                            result = run_voice(audio_bytes, "wav")
                            transcription = result.get("transcription")
                            if transcription:
                                txt = transcription["text"]
                                dur = transcription.get("duration_seconds", 0)
                                prov = transcription.get("provider", "groq")
                                st.session_state.messages.append({
                                    "role": "user",
                                    "content": txt,
                                    "voice": True,
                                    "time": now_str,
                                })
                                audit_log("voice_query", {"transcript": txt[:100], "duration": dur, "provider": prov}, session_id)
                                response = format_response(result)
                            else:
                                response = f"🎙️ {result.get('answer', result.get('voice_error', 'Error'))}"
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": response,
                                "time": now_str,
                            })
                    except Exception as e:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"❌ {sanitize_error(e)}",
                            "time": now_str,
                        })
                st.rerun()

# ── Text input ──
if user_input := st.chat_input("Escribe un mensaje..."):
    now_str = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": user_input, "time": now_str})

    with st.spinner("🔄 Analizando..."):
        try:
            response = _execute_user_query(user_input)
        except RateLimitError as e:
            response = f"⏳ {str(e)}"
        except Exception as e:
            response = f"❌ {sanitize_error(e)}"

    st.session_state.messages.append({"role": "assistant", "content": response, "time": now_str})
    st.rerun()

# ── Process sidebar example queries ──
if "pending_query" in st.session_state:
    pending = st.session_state.pending_query
    del st.session_state.pending_query
    now_str = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": pending, "time": now_str})

    with st.spinner("🔄 Analizando..."):
        try:
            response = _execute_user_query(pending)
        except RateLimitError as e:
            response = f"⏳ {str(e)}"
        except Exception as e:
            response = f"❌ {sanitize_error(e)}"

    st.session_state.messages.append({"role": "assistant", "content": response, "time": now_str})
    st.rerun()


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("""
<div class="footer">
    <strong>InsightQL</strong> • Desarrollado con ❤️ por
    <a href="https://blacksmithresearch.com" target="_blank">Blacksmith Research</a>
    <div class="footer-tagline">
        Transformamos los datos en insights y conocimiento de valor para el negocio
    </div>
</div>
""", unsafe_allow_html=True)
