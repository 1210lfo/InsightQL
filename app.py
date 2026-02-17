"""
InsightQL - Demo Frontend Premium
Interfaz Streamlit con branding Blacksmith Research
"""

import streamlit as st
import asyncio
import re

# Configuración de página - DEBE IR PRIMERO
st.set_page_config(
    page_title="InsightQL | Blacksmith Research",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Importar el agente y seguridad
from src.agent.graph import run_analytics_query
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
    
    /* ========== CHAT CONTAINER ========== */
    .chat-container {
        background: var(--white);
        border-radius: 20px;
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        border: 1px solid var(--gray-200);
        overflow: hidden;
        margin-bottom: 1.5rem;
    }
    
    .chat-header {
        background: linear-gradient(135deg, var(--gray-50) 0%, var(--white) 100%);
        padding: 1rem 1.5rem;
        border-bottom: 1px solid var(--gray-200);
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .chat-header-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 1rem;
    }
    
    .chat-header h3 {
        margin: 0;
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--gray-900);
    }
    
    .chat-header span {
        font-size: 0.75rem;
        color: var(--gray-500);
    }
    
    .chat-messages {
        padding: 1.5rem;
        min-height: 320px;
        max-height: 420px;
        overflow-y: auto;
        background: var(--gray-50);
    }
    
    .message {
        margin-bottom: 1rem;
    }
    
    .message-user {
        display: flex;
        justify-content: flex-end;
    }
    
    .message-user .bubble {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: var(--white);
        padding: 0.875rem 1.25rem;
        border-radius: 18px 18px 4px 18px;
        max-width: 70%;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        font-size: 0.9rem;
        line-height: 1.5;
    }
    
    .message-assistant {
        display: flex;
        gap: 0.75rem;
        align-items: flex-start;
    }
    
    .message-avatar {
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, var(--accent) 0%, #e55a2b 100%);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 0.875rem;
        flex-shrink: 0;
    }
    
    .message-assistant .bubble {
        background: var(--white);
        color: var(--gray-700);
        padding: 1rem 1.25rem;
        border-radius: 18px 18px 18px 4px;
        max-width: 80%;
        border: 1px solid var(--gray-200);
        font-size: 0.9rem;
        line-height: 1.6;
    }
    
    .message-assistant .bubble strong {
        color: var(--gray-900);
        font-weight: 600;
    }
    
    /* ========== INPUT AREA ========== */
    .input-wrapper {
        background: var(--white);
        border-radius: 16px;
        padding: 1rem 1.25rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid var(--gray-200);
    }
    
    .stTextInput > div > div > input {
        border-radius: 12px !important;
        border: 2px solid var(--gray-200) !important;
        padding: 0.875rem 1.25rem !important;
        font-size: 0.95rem !important;
        background: var(--gray-50) !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--primary) !important;
        background: var(--white) !important;
        box-shadow: 0 0 0 4px rgba(0, 102, 204, 0.1) !important;
    }
    
    /* Botón enviar */
    div[data-testid="stHorizontalBlock"] > div:last-child .stButton > button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        color: var(--white) !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.875rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important;
    }
    
    div[data-testid="stHorizontalBlock"] > div:last-child .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1) !important;
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
    
    /* ========== CHAT MESSAGES NATIVO STREAMLIT ========== */
    /* Todos los mensajes de chat */
    [data-testid="stChatMessage"] {
        border-radius: 16px !important;
        padding: 1rem 1.25rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Mensajes del asistente - fondo azul */
    div[data-testid="stChatMessage"][data-testid*="assistant"],
    div[class*="stChatMessage"]:nth-child(odd) {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%) !important;
        border: 1px solid #93c5fd !important;
    }
    
    /* Alternativa: usar el avatar para identificar */
    .stChatMessage:has(span[data-testid="chatAvatarIcon-assistant"]) {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%) !important;
        border: 1px solid #93c5fd !important;
    }
    
    /* Forzar fondo azul para mensajes del asistente con selector más amplio */
    .stApp [data-testid="stChatMessageContent"]:not(:has(~ [data-testid="chatAvatarIcon-user"])) {
        background: transparent !important;
    }
    
    /* Chat input */
    [data-testid="stChatInput"] {
        border-radius: 16px !important;
        border: 2px solid var(--gray-200) !important;
        background: var(--white) !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important;
    }
    
    [data-testid="stChatInput"]:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 4px rgba(0, 102, 204, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def run_query(query: str) -> dict:
    """Ejecuta una consulta al agente."""
    return asyncio.run(run_analytics_query(query))


def format_response(response: dict) -> str:
    """Formatea la respuesta del agente."""
    return response.get("answer", "No se pudo obtener una respuesta.")


def markdown_to_html(text: str) -> str:
    """Convierte markdown a HTML."""
    # Negritas
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Cursivas
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    # Bullets
    lines = text.split('\n')
    result = []
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('• ') or stripped.startswith('- '):
            if not in_list:
                result.append('<ul style="margin: 0.5rem 0; padding-left: 1.5rem; list-style: disc;">')
                in_list = True
            content = stripped[2:]
            result.append(f'<li style="margin: 0.25rem 0;">{content}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            if stripped:
                result.append(f'{stripped}<br>')
    
    if in_list:
        result.append('</ul>')
    
    return ''.join(result)


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
# CHAT
# =============================================================================

# Inicializar mensajes
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "¡Hola! 👋 Soy **InsightQL**, tu asistente analítico para el catálogo de moda.\n\nPuedo ayudarte con preguntas como:\n• 📊 **Resumen del catálogo** - Vista general de productos\n• 💰 **Análisis de precios** - Promedios, rangos, descuentos\n• 👥 **Segmentación** - Distribución por público objetivo\n• 📏 **Disponibilidad** - Tallas y stock\n\n¿Qué te gustaría saber hoy?"
    })

# Chat header
st.markdown("""
<div class="chat-container">
    <div class="chat-header">
        <div class="chat-header-icon">💬</div>
        <div>
            <h3>Conversación</h3>
            <span>Pregunta en lenguaje natural</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Mostrar mensajes con estilo personalizado
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
            <div style="background: linear-gradient(135deg, #4b5563 0%, #374151 100%); 
                        color: white; 
                        padding: 1rem 1.25rem; 
                        border-radius: 18px 18px 4px 18px; 
                        max-width: 80%;
                        font-size: 0.95rem;
                        line-height: 1.6;
                        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
                👤 {msg["content"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Convertir markdown a HTML para el asistente
        content = msg["content"].replace("**", "<strong>").replace("**", "</strong>")
        content = content.replace("\n", "<br>")
        content = content.replace("• ", "• ")
        st.markdown(f"""
        <div style="display: flex; gap: 0.75rem; margin-bottom: 1rem;">
            <div style="width: 36px; 
                        height: 36px; 
                        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); 
                        border-radius: 10px; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        color: white; 
                        font-size: 1rem;
                        flex-shrink: 0;">🤖</div>
            <div style="background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); 
                        border: 1px solid #93c5fd;
                        color: #1e3a5f; 
                        padding: 1rem 1.25rem; 
                        border-radius: 18px 18px 18px 4px; 
                        max-width: 85%;
                        font-size: 0.95rem;
                        line-height: 1.7;
                        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
                {content}
            </div>
        </div>
        """, unsafe_allow_html=True)

# Procesar pregunta pendiente
if "pending_query" in st.session_state:
    pending = st.session_state.pending_query
    del st.session_state.pending_query
    
    st.session_state.messages.append({"role": "user", "content": pending})
    
    with st.spinner("🔄 Analizando..."):
        try:
            # Validate input
            is_valid, validation_error = validate_user_input(pending)
            if not is_valid:
                response = f"⚠️ {validation_error}"
            else:
                # Check rate limit
                limiter = get_rate_limiter()
                session_id = st.session_state.get("session_id", "anonymous")
                if not limiter.is_allowed(session_id):
                    response = "⏳ Demasiadas consultas. Por favor espera unos segundos."
                else:
                    audit_log("query", {"query": pending[:100]}, session_id)
                    result = run_query(pending)
                    response = format_response(result)
        except RateLimitError as e:
            response = f"⏳ {str(e)}"
        except Exception as e:
            response = f"❌ {sanitize_error(e)}"
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# Input area con st.chat_input nativo
if user_input := st.chat_input("💬 Escribe tu pregunta... Ej: ¿Cuál es el precio promedio de calzado para mujer?"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.spinner("🔄 Analizando..."):
        try:
            # Validate input
            is_valid, validation_error = validate_user_input(user_input)
            if not is_valid:
                response = f"⚠️ {validation_error}"
            else:
                # Check rate limit
                limiter = get_rate_limiter()
                session_id = st.session_state.get("session_id", "anonymous")
                if not limiter.is_allowed(session_id):
                    response = "⏳ Demasiadas consultas. Por favor espera unos segundos."
                else:
                    audit_log("query", {"query": user_input[:100]}, session_id)
                    result = run_query(user_input)
                    response = format_response(result)
        except RateLimitError as e:
            response = f"⏳ {str(e)}"
        except Exception as e:
            response = f"❌ {sanitize_error(e)}"
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()


# =============================================================================
# CAPACIDADES
# =============================================================================

st.markdown("""
<div class="capabilities-title">
    <h2>🚀 Capacidades del Agente</h2>
    <p>Potenciado por IA para análisis avanzado de datos</p>
</div>
""", unsafe_allow_html=True)

cap1, cap2, cap3 = st.columns(3)

with cap1:
    st.markdown("""
    <div class="capability-card blue">
        <div class="capability-icon">📊</div>
        <h4>Análisis en Tiempo Real</h4>
        <p>Consultas sobre el 100% de los datos con respuestas precisas.</p>
    </div>
    """, unsafe_allow_html=True)

with cap2:
    st.markdown("""
    <div class="capability-card orange">
        <div class="capability-icon">🗣️</div>
        <h4>Lenguaje Natural</h4>
        <p>Pregunta como hablarías con un experto. Sin SQL necesario.</p>
    </div>
    """, unsafe_allow_html=True)

with cap3:
    st.markdown("""
    <div class="capability-card green">
        <div class="capability-icon">✅</div>
        <h4>Datos Verificados</h4>
        <p>Respuestas validadas con datos reales del catálogo.</p>
    </div>
    """, unsafe_allow_html=True)


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
