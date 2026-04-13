import streamlit as st
import os
import requests
import pandas as pd
import json
import re
import plotly.express as px
from datetime import datetime
from dotenv import load_dotenv
import pytz
import time

# Importaciones de CrewAI y Langchain (Groq)
from crewai import Agent, Task, Crew, Process
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_CSV = os.path.join(BASE_DIR, "data", "Argo_Historial.csv")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "data", "motor_heartbeat.txt")

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
        try:
            df = pd.read_csv(HISTORIAL_CSV)
            return df.to_dict('records')
        except:
            return []
    return []

def guardar_historial(registros):
    """Guarda el historial en el archivo CSV."""
    df = pd.DataFrame(registros)
    df.to_csv(HISTORIAL_CSV, index=False)

def enviar_telegram(mensaje):
    """Envía notificación a Telegram."""
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"}, timeout=5)
        except:
            pass

# ==========================================
# 1. LÓGICA DE DATOS Y AGENTES
# ==========================================
def obtener_datos_polymarket():
    """Obtiene datos reales enfocados en los 10 mercados más volátiles."""
    mercados = []
    try:
        url = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false"
        resp = requests.get(url, timeout=10)
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
                    "volatilidad": change
                })
        mercados.sort(key=lambda x: x["volatilidad"], reverse=True)
    except: pass
    
    if not mercados: return "No hay datos."
    lineas = [f"- {m['titulo']} | Precio: {m['precio']:.2f} | Vol: ${m['volumen']:.0f}" for m in mercados[:10]]
    return "\n".join(lineas)

def misiones_argo(api_key, saldo_actual, backend="Groq"):
    if backend == "Groq":
        os.environ["GROQ_API_KEY"] = api_key
        modelo_ia = "groq/llama-3.3-70b-versatile"
    else:
        from langchain_community.llms import Ollama
        modelo_ia = Ollama(model="llama3.1", base_url="http://localhost:11434")
    
    datos_mercado = obtener_datos_polymarket()
    
    investigador = Agent(
        role="Analista", goal="Buscar el mejor mercado.", llm=modelo_ia,
        backstory="Experto cuantitativo en Polymarket.", verbose=False
    )
    gestor = Agent(
        role="Riesgos", goal="Gestionar el capital.", llm=modelo_ia,
        backstory="Especialista en Kelly Criterion.", verbose=False
    )
    critico = Agent(
        role="Auditor", goal="Emitir veredicto JSON.", llm=modelo_ia,
        backstory="Obsesivo con los formatos y la seguridad.", verbose=False
    )

    t1 = Task(description=f"Analiza:\n{datos_mercado}", expected_output="Un mercado sugerido.", agent=investigador)
    t2 = Task(description="Monto máx 5%.", expected_output="Monto sugerido.", agent=gestor)
    t3 = Task(description="JSON FINAL: {accion, mercado, precio_clob, take_profit, stop_loss, monto, razonamiento, evidencias}", expected_output="JSON puro.", agent=critico)

    crew = Crew(agents=[investigador, gestor, critico], tasks=[t1, t2, t3], process=Process.sequential, verbose=False)
    return str(crew.kickoff())

# ==========================================
# 2. UI TÉCNICA (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Argo V3 Dashboard", layout="wide")

# Estilos Técnicos Profesionales
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    body, .main { font-family: 'Inter', sans-serif; background-color: #0e1117; }
    .stMetric { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; }
    h1, h2, h3 { color: #f0f6fc; }
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; color: #8b949e; }
    .stTabs [aria-selected="true"] { color: #58a6ff; border-bottom-color: #58a6ff; }
</style>
""", unsafe_allow_html=True)

if "historial" not in st.session_state:
    st.session_state["historial"] = cargar_historial()
if "saldo" not in st.session_state:
    try:
        invertido = sum([float(x.get("Inversión", 0) or 0) for x in st.session_state["historial"] if x.get("Acción") == "COMPRAR"])
    except: invertido = 0.0
    st.session_state["saldo"] = max(0, 50.0 - invertido)

# Header
st.title("🚢 ARGO V3.5 | Autonomous Hedge Fund")
st.markdown("---")

# Métricas Principales
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Balance Disponible", f"${st.session_state['saldo']:.2f}")
with col2:
    ventas = len([x for x in st.session_state["historial"] if x.get("Acción") == "COMPRAR"])
    st.metric("Operaciones Realizadas", ventas)
with col3:
    st.metric("Status Motor", verificar_motor())

# Contenido Principal
col_main, col_side = st.columns([3, 1])

with col_side:
    st.subheader("Configuración")
    
    # Detección segura de API Key
    try:
        env_path = os.path.join(BASE_DIR, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if "GROQ_API_KEY=" in line:
                        val = line.split("=", 1)[1].strip().replace('"', '').replace("'", "")
                        if len(val) > 10: os.environ["GROQ_API_KEY"] = val
    except: pass
    
    api_key_env = os.environ.get("GROQ_API_KEY", "")
    if api_key_env:
        st.success("API Key cargada vía .env")
        api_input = api_key_env
    else:
        api_input = st.text_input("Groq API Key (Manual)", type="password")
    
    backend_mode = st.selectbox("Motor de IA", ["Groq Cloud", "Ollama Local"])
    
    if st.button("🚀 Iniciar Análisis de Mercado", use_container_width=True):
        if not api_input and "Groq" in backend_mode:
            st.error("Se requiere API Key de Groq.")
        else:
            with st.spinner("Ejecutando agentes..."):
                try:
                    res_raw = misiones_argo(api_input, st.session_state["saldo"], backend="Groq" if "Groq" in backend_mode else "Ollama")
                    match = re.search(r'\{.*\}', res_raw.replace('\n', ''), re.IGNORECASE)
                    if match:
                        datos = json.loads(match.group(0))
                        # Lógica de registro
                        status = datos.get("accion", "VETO").upper()
                        monto = float(datos.get("monto", 0.0))
                        
                        registro = {
                            "Fecha": obtener_hora_espana(),
                            "Mercado": datos.get("mercado", "N/A"),
                            "Acción": status,
                            "Precio": float(datos.get("precio_clob", 0.5)),
                            "TP": float(datos.get("take_profit", 0.0)),
                            "SL": float(datos.get("stop_loss", 0.0)),
                            "Inversión": monto,
                            "Razonamiento": datos.get("razonamiento", "...")
                        }
                        st.session_state["historial"].insert(0, registro)
                        guardar_historial(st.session_state["historial"])
                        if status == "COMPRAR":
                            st.session_state["saldo"] -= monto
                        st.success(f"Análisis finalizado: {status}")
                        st.rerun()
                except Exception as e:
                    st.error(f"Fallo técnico: {e}")

with col_main:
    tabs = st.tabs(["📊 Auditoría", "💼 Cartera", "🧠 Bayesiano", "📜 Historial"])
    
    with tabs[0]:
        st.subheader("Auditoría de Decisiones")
        audit_file = os.path.join(BASE_DIR, "data", "argo_audit.json")
        if os.path.exists(audit_file):
            with open(audit_file, "r") as f:
                logs = json.load(f)
            df_audit = pd.DataFrame(logs)
            if not df_audit.empty:
                st.dataframe(df_audit.style.map(lambda x: "color: #10b981" if x == "COMPRAR" else ("color: #ef4444" if x == "VETO" else ""), subset=['accion']), use_container_width=True)
        else:
            st.info("No hay registros de auditoría disponibles.")

    with tabs[1]:
        st.subheader("Posiciones Activas")
        abiertas = [h for h in st.session_state["historial"] if h.get("estado") == "ABIERTA"]
        if abiertas:
            st.table(pd.DataFrame(abiertas)[["Mercado", "Precio", "TP", "SL", "Inversión"]])
        else:
            st.info("Sin posiciones abiertas.")

    with tabs[2]:
        st.subheader("Configuración Bayesiana")
        st.code("""
        TYPE_CAPS = {'A': 1.0, 'B': 0.6, 'C': 0.3, 'D': 0.2}
        WEIGHTS = {"v": 0.45, "r": 0.25, "c": 0.15, "t": 0.15}
        LOGIT_MAX = 0.9999
        """, language="python")

    with tabs[3]:
        st.subheader("Historial Completo")
        if st.session_state["historial"]:
            df_hist = pd.DataFrame(st.session_state["historial"])
            st.dataframe(df_hist, use_container_width=True)
            
            # Gráfico de Rendimiento
            try:
                df_inv = df_hist[df_hist['Acción'] == 'COMPRAR'].copy()
                if not df_inv.empty:
                    df_inv['Balance'] = 50.0 - df_inv['Inversión'].cumsum()
                    fig = px.line(df_inv, x='Fecha', y='Balance', title="Evolución de Liquidez")
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                    st.plotly_chart(fig, use_container_width=True)
            except: pass
        else:
            st.info("Sin historial.")

st.write("---")
st.caption("Argo V3.5 Platinum | Quantum Trading Engine")
