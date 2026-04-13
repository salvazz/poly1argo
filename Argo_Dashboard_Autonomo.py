import streamlit as st
import os
import requests
import pandas as pd
import json
import re
from datetime import datetime
from dotenv import load_dotenv
import pytz
import time

# Importaciones de CrewAI y Langchain (Groq)
from crewai import Agent, Task, Crew
from crewai.tools import tool
import bayesian_engine

# Configuración de zona horaria España
SPAIN_TZ = pytz.timezone('Europe/Madrid')

def obtener_hora_espana():
    return datetime.now(SPAIN_TZ).strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# CONFIGURACIONES Y PERSISTENCIA GLOBAL
# ==========================================
load_dotenv()
HISTORIAL_CSV = os.path.join(os.path.dirname(__file__), "data", "Argo_Historial.csv")
HEARTBEAT_FILE = os.path.join(os.path.dirname(__file__), "data", "motor_heartbeat.txt")

def verificar_motor():
    """Verifica si el motor está activo leyendo el heartbeat."""
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE, "r") as f:
                last_heartbeat = float(f.read().strip())
            if time.time() - last_heartbeat < 180: # 3 minutos de margen
                return "ONLINE 🟢"
        except:
            pass
    return "OFFLINE 🔴"

def cargar_historial():
    """Carga el historial de compras/ventas del archivo CSV local."""
    if os.path.exists(HISTORIAL_CSV):
        return pd.read_csv(HISTORIAL_CSV).to_dict('records')
    return []

def guardar_historial(registros):
    """Guarda el historial en el escritorio para que persista al cerrar."""
    df = pd.DataFrame(registros)
    df.to_csv(HISTORIAL_CSV, index=False)

def enviar_telegram(mensaje):
    """Envía notificación a Telegram usando credenciales seguras."""
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id and "tu_token" not in token:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"})
        except Exception:
            pass

# ==========================================
# 1. HERRAMIENTA PERSONALIZADA (LOS OJOS)
# ==========================================
@tool("LectorPolymarketGamma")
def lector_polymarket(query: str = "general") -> str:
    """Útil para conectarse a Polymarket, leer mercados activos reales y devolver un listado en formato texto. Pasa 'general' como query."""
    try:
        # Usamos la Gamma API real de Polymarket
        url = "https://gamma-api.polymarket.com/events?limit=25&active=true&closed=false"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        mercados = []
        for e in data:
            if e.get("volume", 0) > 50000:  # Filtramos mercados importantes
                mercados.append(f"""
                Mercado: {e.get('title', 'N/A')}
                Volumen USD: {e.get('volume', 0)}
                Categoría: {e.get('category', 'Político/Otro')}
                """)
        if not mercados:
            return "No se encontraron mercados de alto volumen hoy."
        
        # Le enviamos los top 5 al agente para no marearlo
        return "MERCADOS ACTIVOS EN POLYMARKET HOY:\n" + "".join(mercados[:5])
    
    except Exception as e:
        return f"Error leyendo Polymarket: {str(e)}"

# ==========================================
# 2. LÓGICA CORE DE LOS AGENTES
# ==========================================
def obtener_datos_polymarket():
    """Obtiene datos reales enfocados en los 10 mercados más volátiles."""
    mercados = []
    try:
        url_general = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false"
        resp = requests.get(url_general, timeout=10)
        for e in resp.json():
            vol = e.get("volume", 0)
            if vol > 10000:
                prices = e.get("outcomePrices", ["0", "0"])
                if isinstance(prices, str): prices = json.loads(prices)
                precio_si = float(prices[0]) if prices else 0
                
                change = abs(e.get("oneDayPriceChange", 0))
                
                mercados.append({
                    "titulo": e.get("title", "N/A"), 
                    "volumen": vol, 
                    "precio": precio_si,
                    "volatilidad": change,
                    "categoria": "General"
                })
    except Exception: pass
    
    if not mercados:
        return "No se encontraron mercados activos hoy."
    
    # Ordenamos por VOLATILIDAD
    mercados.sort(key=lambda x: x["volatilidad"], reverse=True)
    
    lineas = [f"- [{m['categoria']}] {m['titulo']} | Precio: {m['precio']:.2f} | Volatilidad: {m['volatilidad']*100:+.2f}% | Vol: ${m['volumen']:,.0f}" for m in mercados[:10]]
    return "TOP 10 MERCADOS POR VOLATILIDAD (24H):\n" + "\n".join(lineas)

def misiones_argo(api_key, saldo_actual, backend="Groq"):
    if backend == "Groq":
        os.environ["GROQ_API_KEY"] = api_key
        modelo_ia = "groq/llama-3.3-70b-versatile"
    else:
        # Configuración para Ollama Local
        # Importación tardía para no penalizar si no se usa
        from langchain_community.llms import Ollama
        modelo_ia = Ollama(model="llama3.1", base_url="http://localhost:11434")
    
    # Pre-cargamos datos reales de Polymarket
    datos_mercado = obtener_datos_polymarket()
    
    # AGENTE 1: INVESTIGADOR (Sin herramienta, recibe datos directamente)
    investigador = Agent(
        role="Investigador Jefe",
        goal="Analizar los mercados activos de Polymarket y seleccionar la mejor oportunidad de inversión.",
        backstory="Eres un sabueso de datos. Analizas la lista de mercados y seleccionas la oportunidad que tenga más liquidez y seguridad.",
        llm=modelo_ia,
        verbose=True
    )
    
    # AGENTE 2: GESTOR DE RIESGOS
    gestor = Agent(
        role="Gestor de Riesgos Matemático",
        goal=f"Con base en el mercado elegido, tu capital actual de ${saldo_actual} USD, propón un monto de inversión. Máximo estricto: 5% del bank.",
        backstory="Eres un actuario ultra-conservador. Proteges el capital a toda costa.",
        llm=modelo_ia,
        verbose=True
    )
    
    critico = Agent(
        role="Crítico de Inversiones",
        goal="Decide si COMPRAR o RECHAZAR y emite un veredicto en formato JSON estricto.",
        backstory="Eres la última línea de defensa. Odias el riesgo y jamás envías texto basura, solo respondes con bloques JSON perfectos.",
        llm=modelo_ia,
        verbose=True
    )

    tarea1 = Task(
        description=f"""Aquí tienes los datos REALES obtenidos de la API de Polymarket en tiempo real:
{datos_mercado}
Analiza estos mercados y escoge el que parezca más interesante y volátil.""",
        expected_output="Nombre del mercado top seleccionado y justificación breve.",
        agent=investigador
    )
    
    tarea2 = Task(
        description="Analiza la elección y propón monto de inversión (máx 5%).",
        expected_output="Monto sugerido y justificación.",
        agent=gestor
    )

    tarea_final = Task(
        description='''JSON FINAL estricto:
{
  "accion": "COMPRAR" o "RECHAZAR",
  "mercado": "Título exacto",
  "precio_clob": 0.75,
  "take_profit": 0.90,
  "stop_loss": 0.60,
  "monto": 2.50,
  "razonamiento": "Justificación",
  "evidencias": [
    {"type": "A|B|C|D", "verifiability": 0.8, "consistency": 0.9, "corroborations": 2, "polarity": 1, "publishedAt": "2025-04-10"}
  ]
}''',
        expected_output="Objeto JSON puro con evidencias.",
        agent=critico
    )

# 3. INTERFAZ FRONTAL (DASHBOARD)
# ==========================================
# ==========================================
# 3. INTERFAZ FRONTAL (DASHBOARD PREMIUM)
# ==========================================
st.set_page_config(page_title="Argo V3 | Autonomous Trading", page_icon="🚢", layout="wide")

# Curated HSL Palette & Premium Typography
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@300;400;600;800&display=swap');
    
    :root {
        --glass-bg: rgba(17, 24, 39, 0.7);
        --glass-border: rgba(255, 255, 255, 0.05);
        --accent: #8b5cf6; /* Modern Violet */
        --success: #10b981;
        --warning: #f59e0b;
        --text: #f8fafc;
    }

    .main {
        background: #030712;
        background-image: 
            radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
        font-family: 'Inter', sans-serif;
        color: var(--text);
    }
    
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Glassmorphism Cards */
    div[data-testid="stMetric"] {
        background: var(--glass-bg) !important;
        border: 1px solid var(--glass-border) !important;
        padding: 25px !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 40px 0 rgba(0, 0, 0, 0.5) !important;
        backdrop-filter: blur(12px) !important;
        transition: transform 0.3s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: var(--accent) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent !important;
        border: none !important;
        font-weight: 600;
        color: #64748b;
    }

    .stTabs [aria-selected="true"] {
        color: white !important;
        border-bottom: 2px solid var(--accent) !important;
    }

    /* Sidebar and other elements */
    section[data-testid="stSidebar"] {
        background-color: #030712 !important;
        border-right: 1px solid var(--glass-border);
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Target specific mobile tweaks */
    @media (max-width: 768px) {
        .stColumns {
            flex-direction: column !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

if "historial" not in st.session_state:
    st.session_state["historial"] = cargar_historial()
if "saldo" not in st.session_state:
    invertido = sum([float(x.get("Inversión", 0)) for x in st.session_state["historial"] if x.get("Acción") == "COMPRAR"])
    st.session_state["saldo"] = max(0, 50.0 - invertido)

# Header Premium con Canvas Animation
st.markdown("""
<div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; background: #020617;">
    <canvas id="canvas-bg"></canvas>
</div>
<script>
    const canvas = document.getElementById('canvas-bg');
    const ctx = canvas.getContext('2d');
    let particles = [];

    function init() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        particles = [];
        for (let i = 0; i < 80; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                size: Math.random() * 2 + 1,
                speedX: Math.random() * 0.5 - 0.25,
                speedY: Math.random() * 0.5 - 0.25,
                opacity: Math.random() * 0.5 + 0.2
            });
        }
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        ctx.strokeStyle = 'rgba(139, 92, 246, 0.1)';
        ctx.lineWidth = 0.5;

        for (let i = 0; i < particles.length; i++) {
            let p = particles[i];
            p.x += p.speedX;
            p.y += p.speedY;

            if (p.x < 0 || p.x > canvas.width) p.speedX *= -1;
            if (p.y < 0 || p.y > canvas.height) p.speedY *= -1;

            ctx.fillStyle = `rgba(139, 92, 246, ${p.opacity})`;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();

            for (let j = i + 1; j < particles.length; j++) {
                let p2 = particles[j];
                let dist = Math.sqrt((p.x - p2.x)**2 + (p.y - p2.y)**2);
                if (dist < 150) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.stroke();
                }
            }
        }
        requestAnimationFrame(animate);
    }

    window.addEventListener('resize', init);
    init();
    animate();
</script>
<style>
    /* Transparencia para que se vea el canvas */
    .stApp {
        background: transparent !important;
    }
    div[data-testid="stToolbar"] { visibility: hidden; }
    
    .main-title {
        font-family: 'Outfit', sans-serif;
        font-size: 4rem;
        background: linear-gradient(to right, #fff, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">ARGO V3 PLATINUM</h1>', unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 1.2em; color: #94a3b8; margin-bottom: 3em;'>Red Neuronal de Trading Autónomo en Polymarket</p>", unsafe_allow_html=True)

# Layout Principal: Stats en la parte superior para mobile
stat_col1, stat_col2, stat_col3 = st.columns(3)
with stat_col1:
    st.metric("Cartera Simulada", f"${st.session_state['saldo']:.2f}", help="Saldo inicial: $50.00")
with stat_col2:
    ventas = len([x for x in st.session_state["historial"] if x.get("Acción") == "COMPRAR"])
    st.metric("Operaciones", ventas, delta=f"+{ventas} hoy")
with stat_col3:
    status_motor = verificar_motor()
    st.metric("Estatus del Motor", status_motor, help="Verificando heartbeat del Motor 24/7")

st.write("")

# Controles y Dashboard
col_main, col_side = st.columns([3, 1])

with col_side:
    st.markdown("### ⚙️ Centro de Mando")
    
    # Intento de detección manual robusta
    try:
        with open(os.path.join(os.path.dirname(__file__), ".env"), "r") as f:
            for line in f:
                if "GROQ_API_KEY=" in line:
                    val = line.split("=")[1].strip().replace('"', '').replace("'", "")
                    if len(val) > 10: os.environ["GROQ_API_KEY"] = val
    except: pass
    
    api_key_env = os.environ.get("GROQ_API_KEY", "")
    
    if api_key_env and len(api_key_env) > 10:
        st.success("🔒 ACCESO ENCRIPTADO Y OCULTO")
        api_key_input = api_key_env
    else:
        api_key_input = st.text_input("Ingresar Groq API Key (Manual)", type="password")
    
    st.write("")
    backend_mode = st.radio("🤖 Backend de IA", ["Groq (Nube)", "Ollama (Local)"], help="Usa Ollama si alcanzas el límite de Groq.")
    backend_val = "Ollama" if "Ollama" in backend_mode else "Groq"
    
    st.write("")
    if st.button("🚀 Ejecutar Análisis Manual", use_container_width=True):
        if backend_val == "Groq" and not api_key_input:
            st.error("Falta API Key de Groq")
        else:
            with st.spinner(f"🧠 Sincronizando con backend {backend_val}..."):
                resultado_bruto = str(misiones_argo(api_key_input, st.session_state["saldo"], backend=backend_val))
                st.session_state["ultimo_veredicto"] = resultado_bruto
                
                try:
                    match = re.search(r'\{.*\}', resultado_bruto.replace('\n', ''), re.IGNORECASE)
                    if match:
                        datos = json.loads(match.group(0))
                        accion = datos.get("accion", "RECHAZAR").upper()
                        monto = float(datos.get("monto", 0.0))
                        
                        # Cálculo Bayesiano Manual
                        p_mercado = float(datos.get('precio_clob', 0.5))
                        evidencias = datos.get('evidencias', [])
                        p_final = bayesian_engine.calculate_bayesian_probability(p_mercado, evidencias)
                        analisis = bayesian_engine.get_bayesian_summary(p_mercado, p_final)
                        
                        registro = {
                            "Fecha": obtener_hora_espana(),
                            "Mercado": datos.get("mercado", "N/A"),
                            "Acción": accion,
                            "Score": analisis['score'],
                            "Edge": analisis['edge'],
                            "Precio": p_mercado,
                            "TP": datos.get("take_profit", 0.0),
                            "SL": datos.get("stop_loss", 0.0),
                            "Inversión": monto,
                            "Razonamiento": datos.get("razonamiento", "...")
                        }
                        st.session_state["historial"].insert(0, registro)
                        guardar_historial(st.session_state["historial"])
                        
                        if accion == "COMPRAR":
                            st.session_state["saldo"] -= monto
                            st.success(f"Detección: COMPRA")
                            enviar_telegram(f"🚀 *ARGO COMPRA*\n*Mercado:* {datos.get('mercado')}\n*Precio:* {datos.get('precio_clob')}\n*TP:* {datos.get('take_profit')} | *SL:* {datos.get('stop_loss')}")
                        else:
                            st.info("Detección: VETO")
                    st.rerun()
                except:
                    st.error("Error al procesar")

import plotly.express as px

# ... (funciones previas se mantienen)

with col_main:
    tabs = st.tabs(["📊 Monitor", "💼 Cartera", "🧠 Inteligencia", "📜 Historial"])
    
    with tabs[0]:
        st.markdown("### 📈 Auditoría de Pensamiento")
        audit_file = os.path.join(os.path.dirname(__file__), "data", "argo_audit.json")
        if os.path.exists(audit_file):
            try:
                with open(audit_file, "r") as f:
                    audit_logs = json.load(f)
                df_audit = pd.DataFrame(audit_logs)
                st.dataframe(df_audit.style.applymap(lambda x: 'color: #10b981' if x == 'COMPRAR' else ('color: #ef4444' if x == 'VETO' else ''), subset=['accion']), use_container_width=True)
            except:
                st.info("Aún no hay registros de auditoría.")
        else:
            st.info("Esperando el primer escaneo del motor...")
            
    with tabs[1]:
        st.markdown("### 💼 Posiciones Abiertas")
        historial = st.session_state["historial"]
        abiertas = [h for h in historial if h.get("estado", "CERRADA") == "ABIERTA"]
        if abiertas:
            st.table(pd.DataFrame(abiertas)[["Mercado", "Precio", "TP", "SL", "Inversión"]])
        else:
            st.info("No hay posiciones abiertas en este momento.")

    with tabs[2]:
        st.markdown("### 🧠 Desglose de Evidencias Bayesianas")
        st.write("Configuración del Motor:")
        st.code("""
        TYPE_CAPS = {'A': 1.0, 'B': 0.6, 'C': 0.3, 'D': 0.2} # Calibración Premium
        LLM_PRIMARY = 'Groq Llama 3.3 70B'
        LLM_FALLBACK = 'Gemini 1.5 Flash'
        """, language="python")

    with tabs[3]:
        st.markdown("### 📜 Historial de Operaciones")
        if len(st.session_state["historial"]) > 0:
            df_plot = pd.DataFrame(st.session_state["historial"])
            st.dataframe(df_plot, use_container_width=True)
            
            df_plot['Inversión'] = pd.to_numeric(df_plot['Inversión'], errors='coerce')
            df_plot['Balance'] = 50.0 - df_plot['Inversión'].cumsum()
            
            fig = px.line(df_plot, x='Fecha', y='Balance', title='Evolución del Saldo (Simulado)',
                         line_shape='spline', markers=True)
            fig.update_traces(line_color='#6366f1')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("El historial está vacío.")

    st.write("---")
    st.caption("Argo V3.5 Platinum - Hedge Fund Autónomo")
