import streamlit as st
import os
import requests
import pandas as pd
import json
import re
from datetime import datetime
from dotenv import load_dotenv

# Importaciones de CrewAI y Langchain (Groq)
from crewai import Agent, Task, Crew
from crewai.tools import tool

# ==========================================
# CONFIGURACIONES Y PERSISTENCIA GLOBAL
# ==========================================
load_dotenv()
st.set_page_config(page_title="Argo Local - Agentes en Vivo", layout="wide")
HISTORIAL_CSV = os.path.join(os.path.dirname(__file__), "data", "Argo_Historial.csv")

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
    """Obtiene datos reales de Polymarket ANTES de lanzar los agentes (generales + deportivos)."""
    mercados = []
    # Fuente 1: Mercados generales (política, crypto, geopolítica)
    try:
        url_general = "https://gamma-api.polymarket.com/events?limit=25&active=true&closed=false"
        resp = requests.get(url_general, timeout=10)
        for e in resp.json():
            vol = e.get("volume", 0)
            if vol > 50000:
                mercados.append({"titulo": e.get("title", "N/A"), "volumen": vol, "categoria": "General"})
    except Exception:
        pass
    # Fuente 2: Mercados deportivos (NBA, NFL, Fútbol, UFC, F1, etc.)
    try:
        url_sports = "https://gamma-api.polymarket.com/events?limit=25&active=true&closed=false&tag=sports"
        resp2 = requests.get(url_sports, timeout=10)
        for e in resp2.json():
            vol = e.get("volume", 0)
            if vol > 5000:  # Umbral más bajo para deportes
                mercados.append({"titulo": e.get("title", "N/A"), "volumen": vol, "categoria": "Deportes"})
    except Exception:
        pass
    if not mercados:
        return "No se encontraron mercados activos hoy."
    # Ordenamos por volumen y mostramos top 10
    mercados.sort(key=lambda x: x["volumen"], reverse=True)
    lineas = [f"- [{m['categoria']}] {m['titulo']} | Volumen: ${m['volumen']:,.0f}" for m in mercados[:10]]
    return "MERCADOS ACTIVOS EN POLYMARKET HOY (Generales + Deportes):\n" + "\n".join(lineas)

def misiones_argo(api_key, saldo_actual):
    os.environ["GROQ_API_KEY"] = api_key
    modelo_ia = "groq/llama-3.3-70b-versatile"
    
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
    
    # AGENTE 3: CRÍTICO JUDICIAL
    critico = Agent(
        role="Crítico de Inversiones",
        goal="Decide si COMPRAR o RECHAZAR y emite un veredicto en formato JSON estricto.",
        backstory="Eres la última línea de defensa. Odias el riesgo y jamás envías texto basura, solo respondes con bloques JSON perfectos.",
        llm=modelo_ia,
        verbose=True
    )

    # TAREAS (Los datos reales se inyectan en la primera tarea)
    tarea1 = Task(
        description=f"""Aquí tienes los datos REALES obtenidos de la API de Polymarket en tiempo real:

{datos_mercado}

Analiza estos mercados y escoge el que parezca más interesante, seguro y con mayor volumen de liquidez.""",
        expected_output="Nombre del mercado top seleccionado y justificación breve.",
        agent=investigador
    )
    
    tarea2 = Task(
        description="Analiza la elección del investigador, y determina cuánto invertir sabiendo que es una posición simulada de bajo riesgo.",
        expected_output="Un valor en dólares propuesto para la inversión y justificación del porcentaje.",
        agent=gestor
    )

    tarea_final = Task(
        description='''Toma todo lo anterior y emite la decisión final.
DEBES retornar ÚNICAMENTE el siguiente formato JSON puro. No pongas comillas invertidas ni bloques ```json. Solo el texto en diccionario:
{
  "accion": "COMPRAR" (o cambia a "RECHAZAR"),
  "mercado": "Título exacto del mercado propuesto",
  "monto": 2.50,
  "razonamiento": "Tu justificación técnica"
}
''',
        expected_output="Objeto JSON puro con tu decisión final.",
        agent=critico
    )

    # Ejecución de la tripulación
    flota = Crew(
        agents=[investigador, gestor, critico],
        tasks=[tarea1, tarea2, tarea_final],
        verbose=True
    )

    return flota.kickoff()

# ==========================================
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
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
        --accent: #6366f1;
        --success: #10b981;
        --warning: #f59e0b;
    }

    .main {
        background: radial-gradient(circle at top right, #111827, #000000);
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    /* Glassmorphism Cards */
    .stMetric {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(4px);
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
        color: #94a3b8;
    }

    .stTabs [aria-selected="true"] {
        color: white !important;
        border-bottom: 2px solid var(--accent) !important;
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
    st.session_state["saldo"] = max(0, 1000.0 - invertido)

# Header Premium
st.image("https://img.icons8.com/isometric/512/ship-front-view.png", width=80)
st.title("Argo V3")
st.markdown("<p style='font-size: 1.2em; color: #94a3b8; margin-bottom: 2em;'>Patrulla de Agentes Inteligentes sobre Polymarket</p>", unsafe_allow_html=True)

# Layout Principal: Stats en la parte superior para mobile
stat_col1, stat_col2, stat_col3 = st.columns(3)
with stat_col1:
    st.metric("Cartera Simulada", f"${st.session_state['saldo']:.2f}", help="Saldo inicial: $1,000.00")
with stat_col2:
    ventas = len([x for x in st.session_state["historial"] if x.get("Acción") == "COMPRAR"])
    st.metric("Operaciones", ventas, delta=f"+{ventas} hoy")
with stat_col3:
    st.metric("Estatus del Motor", "ONLINE 🟢", help="El motor 24/7 en segundo plano")

st.write("")

# Controles y Dashboard
col_main, col_side = st.columns([3, 1])

with col_side:
    st.markdown("### ⚙️ Centro de Mando")
    api_key_input = st.text_input("Groq API Key (Secure)", type="password", value=os.environ.get("GROQ_API_KEY", ""))
    
    st.write("")
    if st.button("🚀 Ejecutar Análisis Manual", use_container_width=True):
        if not api_key_input:
            st.error("Falta API Key")
        else:
            with st.spinner("🧠 Sincronizando agentes con la red..."):
                resultado_bruto = str(misiones_argo(api_key_input, st.session_state["saldo"]))
                st.session_state["ultimo_veredicto"] = resultado_bruto
                
                try:
                    match = re.search(r'\{.*\}', resultado_bruto.replace('\n', ''), re.IGNORECASE)
                    if match:
                        datos = json.loads(match.group(0))
                        accion = datos.get("accion", "RECHAZAR").upper()
                        monto = float(datos.get("monto", 0.0))
                        
                        registro = {
                            "Fecha": datetime.now().strftime("%H:%M:%S"),
                            "Mercado": datos.get("mercado", "N/A"),
                            "Acción": accion,
                            "Inversión": monto,
                            "Razonamiento": datos.get("razonamiento", "...")
                        }
                        st.session_state["historial"].insert(0, registro)
                        guardar_historial(st.session_state["historial"])
                        
                        if accion == "COMPRAR":
                            st.session_state["saldo"] -= monto
                            st.success(f"Detección: COMPRA")
                            enviar_telegram(f"🚀 *ARGO COMPRA*\n{datos.get('mercado')}")
                        else:
                            st.info("Detección: VETO")
                    st.rerun()
                except:
                    st.error("Error al procesar")

with col_main:
    t_history, t_brain = st.tabs(["📊 Historial de Patrullaje", "🧠 Procesamiento de Señal"])
    
    with t_history:
        if len(st.session_state["historial"]) > 0:
            df = pd.DataFrame(st.session_state["historial"])
            
            def styling_historial(row):
                color = 'color: #10b981; font-weight: bold;' if row['Acción'] == 'COMPRAR' else 'color: #fca5a5;'
                return [color] * len(row)

            st.dataframe(
                df.style.apply(styling_historial, axis=1),
                use_container_width=True,
                height=500
            )
        else:
            st.info("Sin anomalías detectadas. El sistema está en guardia.")

    with t_brain:
        if "ultimo_veredicto" in st.session_state:
            st.json(st.session_state["ultimo_veredicto"])
        else:
            st.write("Esperando señal del motor...")
