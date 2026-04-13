# ARGO V3 - ARCHIVO MAESTRO DE CONOCIMIENTO
Este documento consolida todo el sistema de trading autónomo Argo V3. 
Contiene el motor de ejecución, el dashboard premium, el motor bayesiano y el vigilante de Telegram.
Ideal para alimentar NotebookLM y obtener un análisis profundo del sistema.

---

## ARCHIVO: Argo_Motor_24x7.py
```python
import os
import time
import json
import pandas as pd
import requests
import pytz
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai_tools import TavilySearchTool
import bayesian_engine

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_CSV = os.path.join(BASE_DIR, "data", "Argo_Historial.csv")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "data", "motor_heartbeat.txt")
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Zona horaria España
SPAIN_TZ = pytz.timezone('Europe/Madrid')

def obtener_hora_espana():
    return datetime.now(SPAIN_TZ)

def enviar_telegram(mensaje):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"})
        except: pass

def obtener_datos_polymarket():
    mercados = []
    try:
        # Aumentamos el límite para buscar más candidatos y filtrar por volatilidad
        r1 = requests.get("https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false", timeout=10)
        for e in r1.json():
            vol = e.get("volume", 0)
            # Filtro básico de liquidez para evitar mercados "muertos"
            if vol > 10000:
                prices = e.get("outcomePrices", ["0", "0"])
                if isinstance(prices, str): prices = json.loads(prices)
                
                # Volatilidad basada en el cambio de precio de 24h
                # Si no existe el campo, asumimos 0
                change = abs(e.get("oneDayPriceChange", 0))
                
                mercados.append({
                    "titulo": e.get("title", "N/A"), 
                    "volumen": vol, 
                    "precio": float(prices[0]) if prices else 0,
                    "volatilidad": change
                })
    except Exception as e: 
        print(f"Error en API: {e}")
        pass
    
    if not mercados: return []
    
    # Ordenamos por VOLATILIDAD (cambio absoluto de precio en 24h)
    mercados.sort(key=lambda x: x["volatilidad"], reverse=True)
    return mercados[:10]

def monitorear_y_vender():
    """Vigilancia con TRAILING STOP LOSS."""
    if not os.path.exists(HISTORIAL_CSV): return
    df = pd.read_csv(HISTORIAL_CSV)
    if 'estado' not in df.columns: df['estado'] = 'ABIERTA'
    if 'max_precio' not in df.columns: df['max_precio'] = df['Precio']
    
    abiertas = df[df['estado'] == 'ABIERTA']
    if abiertas.empty: return

    mercados_actuales = obtener_datos_polymarket()
    precios_map = {m['titulo']: m['precio'] for m in mercados_actuales}

    for idx, row in abiertas.iterrows():
        mercado = row['Mercado']
        if mercado in precios_map:
            p_actual = precios_map[mercado]
            tp = row['TP']
            sl = row['SL']
            max_p = row['max_precio']
            
            # Lógica Trailing SL: si el precio sube, subimos el SL (manteniendo distancia del 15% del maximo)
            if p_actual > max_p:
                df.at[idx, 'max_precio'] = p_actual
                # El nuevo SL no puede bajar, solo subir
                nuevo_sl = max(sl, p_actual * 0.85)
                df.at[idx, 'SL'] = nuevo_sl
                print(f"Subiendo Trailing SL para {mercado} a {nuevo_sl:.2f}")

            # Verificacion de cierre
            if p_actual >= tp:
                df.at[idx, 'estado'] = 'CERRADA'
                df.at[idx, 'precio_cierre'] = p_actual
                enviar_telegram(f"💰 *TP ALCANZADO (+profit)*\n{mercado}\nCierre: {p_actual}")
            elif p_actual <= df.at[idx, 'SL']:
                df.at[idx, 'estado'] = 'CERRADA'
                df.at[idx, 'precio_cierre'] = p_actual
                enviar_telegram(f"🛡️ *TRAILING SL DISPARADO*\n{mercado}\nCierre: {p_actual}")
            
    df.to_csv(HISTORIAL_CSV, index=False)

def enviar_informe_diario():
    if not os.path.exists(HISTORIAL_CSV): return
    df = pd.read_csv(HISTORIAL_CSV)
    # Filtrar por hoy
    hoy_str = obtener_hora_espana().strftime("%Y-%m-%d")
    df_hoy = df[df['fecha'].str.contains(hoy_str)]
    
    total = len(df_hoy)
    compras = len(df_hoy[df_hoy['Acción'] == 'COMPRAR'])
    cerradas = len(df_hoy[df_hoy['estado'] == 'CERRADA'])
    
    msg = f"📊 *INFORME DIARIO ARGO*\n\n"
    msg += f"📅 Fecha: {hoy_str}\n"
    msg += f"🤖 Operaciones hoy: {total}\n"
    msg += f"📥 Compras: {compras}\n"
    msg += f"📤 Cierres ejecutados: {cerradas}\n\n"
    msg += "¡Mañana más patrulla! 🚢"
    enviar_telegram(msg)

def ejecutar_mision_compra():
    api_key = os.environ.get("GROQ_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not api_key: return
    
    mercados = obtener_datos_polymarket()
    if not mercados: return
    texto_mercados = "\n".join([f"- {m['titulo']} | Precio: {m['precio']:.2f} | Volatilidad (24h): {m['volatilidad']*100:+.2f}%" for m in mercados])
    
    search_tool = TavilySearchTool(k=3) if tavily_key else None
    modelo = "groq/llama-3.3-70b-versatile"
    
    # 1. El Investigador
    inv = Agent(role="Analista", goal="Busca noticias positivas sobre los mercados.", backstory="Optimista tecnológico. IMPORTANTE: Usa solo la herramienta de búsqueda disponible si la tienes, no inventes otras.", tools=[search_tool] if search_tool else [], llm=modelo)
    
    # 2. El PESIMISTA (Abogado del diablo)
    pes = Agent(role="Abogado del Diablo", goal="Encuentra razones para NO comprar.", backstory="Escéptico radical. Solo cree en los hechos negativos.", tools=[search_tool] if search_tool else [], llm=modelo)
    
    # 3. El Crítico (Veredicto)
    cri = Agent(role="Gestor de Riesgos", goal="Decidir basandose en ambos.", backstory="Equilibrado y técnico.", llm=modelo)

    t1 = Task(description=f"Analiza estos mercados y busca noticias positivas:\n{texto_mercados}", expected_output="Mercado candidato y por qué.", agent=inv)
    t2 = Task(description="Analiza el candidato y busca TODA LA BASURA y noticias negativas. Destroza su argumento.", expected_output="Informe de riesgos.", agent=pes)
    t3 = Task(description="""JSON FINAL con este formato exacto:
    {
      "accion": "COMPRAR" o "VETO",
      "mercado": "...",
      "precio_clob": 0.5,
      "take_profit": 0.7,
      "stop_loss": 0.4,
      "razonamiento": "...",
      "evidencias": [
        {"type": "A|B|C|D", "verifiability": 0.8, "consistency": 0.9, "corroborations": 2, "polarity": 1, "publishedAt": "2025-04-10"}
      ]
    }""", expected_output="JSON puro.", agent=cri)

    crew = Crew(agents=[inv, pes, cri], tasks=[t1, t2, t3], process=Process.sequential, verbose=False)
    output = str(crew.kickoff())
    
    try:
        clean_output = output[output.find("{"):output.rfind("}")+1]
        data = json.loads(clean_output)
        
        # Calcular Probabilidad Bayesiana al estilo Polyseer
        p_mercado = data.get('precio_clob', 0.5)
        evidencias = data.get('evidencias', [])
        p_final = bayesian_engine.calculate_bayesian_probability(p_mercado, evidencias)
        analisis = bayesian_engine.get_bayesian_summary(p_mercado, p_final)
        
        data['bayesian_score'] = analisis['score']
        data['edge'] = analisis['edge']
        data['sentiment'] = analisis['sentiment']
        data['fecha'] = obtener_hora_espana().strftime("%Y-%m-%d %H:%M:%S")
        data['estado'] = 'ABIERTA'
        data['max_precio'] = p_mercado

        print(f"Resultado Bayesiano: {p_final:.3f} (Edge: {analisis['edge']})")

        if data['accion'] == 'VETO' or analisis['edge'] < 0.03:
            razon = "VETO" if data['accion'] == 'VETO' else f"POCO EDGE ({analisis['edge']})"
            print(f"Rechazado: {razon} para {data['mercado']}")
            enviar_telegram(f"⚖️ *ANALISIS COMPLETADO*\nMercado: {data['mercado']}\nScore Bayesiano: {p_final:.2f}\nSentimiento: {analisis['sentiment']}\nAccion: {razon}")
            return
        
        if os.path.exists(HISTORIAL_CSV):
            df_check = pd.read_csv(HISTORIAL_CSV)
            if data['mercado'] in df_check[df_check['estado'] == 'ABIERTA']['Mercado'].values: return
            df_final = pd.concat([df_check, pd.DataFrame([data])], ignore_index=True)
        else:
            df_final = pd.DataFrame([data])
            
        df_final.to_csv(HISTORIAL_CSV, index=False)
        if data['accion'] == "COMPRAR":
            enviar_telegram(f"⚖️ *COMITÉ HA DECIDIDO: COMPRA*\n*Mercado:* {data['mercado']}\n*Veredicto:* {data['razonamiento'][:100]}...")
    except: pass

if __name__ == "__main__":
    print("ARGO MOTOR V5 (COMITE + TRAILING SL) INICIADO...")
    informe_enviado_hoy = False
    ultimo_escaneo_compra = 0
    
    while True:
        try:
            ahora = obtener_hora_espana()
            
            # 0. Actualizar Heartbeat (Al inicio para marcar presencia)
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(str(time.time()))
            
            # 1. Informe Diario a las 21:00
            if ahora.hour == 21 and ahora.minute == 0 and not informe_enviado_hoy:
                enviar_informe_diario()
                informe_enviado_hoy = True
            if ahora.hour == 22: # Reset para el dia siguiente
                informe_enviado_hoy = False

            # 2. Monitoreo rapido (Trailing SL)
            monitorear_y_vender()
            
            # 3. Escaneo de compras cada 20 min (Ajustado para durar más la cuota de tokens)
            if time.time() - ultimo_escaneo_compra > 1200:
                ejecutar_mision_compra()
                ultimo_escaneo_compra = time.time()
                
        except Exception as e: print(f"Error: {e}")
        time.sleep(60)

```

---

## ARCHIVO: Argo_Dashboard_Autonomo.py
```python
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
    st.markdown("### 📈 Rendimiento de la Flota")
    if len(st.session_state["historial"]) > 0:
        # Generar Curva de Capital (Simulada)
        df_plot = pd.DataFrame(st.session_state["historial"])
        df_plot['Inversión'] = pd.to_numeric(df_plot['Inversión'], errors='coerce')
        # Simulamos una curva simple: Restamos inversion si compra, sumamos aprox si cerramos (o mantenemos)
        df_plot['Balance'] = 50.0 - df_plot['Inversión'].cumsum()
        
        fig = px.line(df_plot, x='Fecha', y='Balance', title='Evolución del Saldo (Simulado)',
                     line_shape='spline', markers=True)
        fig.update_traces(line_color='#6366f1')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
        st.plotly_chart(fig, use_container_width=True)

    t_history, t_brain = st.tabs(["📊 Historial de Patrullaje", "🧠 Procesamiento de Señal"])
    
    with t_history:
        if len(st.session_state["historial"]) > 0:
            df = pd.DataFrame(st.session_state["historial"])
            
            # Filtro de estado si existe
            if 'estado' in df.columns:
                st.write("Filtrar por estado:")
                st.dataframe(df, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.info("Sin anomalías detectadas. El sistema está en guardia.")


    with t_brain:
        if "ultimo_veredicto" in st.session_state:
            st.json(st.session_state["ultimo_veredicto"])
        else:
            st.write("Esperando señal del motor...")

```

---

## ARCHIVO: bayesian_engine.py
```python
import math
import datetime

# ------------------------------------------------------------------------------
# CONFIGURACIÓN DE PESOS (Inspirado en Polyseer)
# ------------------------------------------------------------------------------
TYPE_CAPS = {"A": 1.0, "B": 0.6, "C": 0.3, "D": 0.2}
WEIGHTS = {"v": 0.45, "r": 0.25, "u": 0.15, "t": 0.15}

def clamp(x, lo, hi):
    return min(hi, max(lo, x))

def logit(p):
    if p >= 1: p = 0.9999
    if p <= 0: p = 0.0001
    return math.log(p / (1 - p))

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

def recency_score(published_at_str):
    """Calcula un score de recencia basado en días de antigüedad."""
    if not published_at_str:
        return 0.5
    try:
        # Formato esperado: YYYY-MM-DD
        dt = datetime.datetime.strptime(published_at_str[:10], "%Y-%m-%d")
        now = datetime.datetime.now()
        days = max(0, (now - dt).days)
        half_life = 120
        score = 1 / (1 + days / half_life)
        return clamp(score, 0, 1)
    except:
        return 0.5

def r_from_corroborations(k, k0=1.0):
    return 1 - math.exp(-k0 * max(0, k))

def calculate_log_lr(evidence_item):
    """
    Calcula el Log Likelihood Ratio de una pieza de evidencia.
    evidence_item: {
        'type': 'A'|'B'|'C'|'D',
        'verifiability': 0-1,
        'consistency': 0-1,
        'corroborations': int,
        'polarity': 1 (FOR) or -1 (AGAINST),
        'publishedAt': 'YYYY-MM-DD'
    }
    """
    e_type = evidence_item.get('type', 'C')
    cap = TYPE_CAPS.get(e_type, 0.3)
    
    ver = clamp(evidence_item.get('verifiability', 0.5), 0, 1)
    cons = clamp(evidence_item.get('consistency', 0.5), 0, 1)
    r = r_from_corroborations(evidence_item.get('corroborations', 0))
    t = recency_score(evidence_item.get('publishedAt'))
    
    polarity = evidence_item.get('polarity', 1)
    
    val = polarity * cap * (WEIGHTS['v']*ver + WEIGHTS['r']*r + WEIGHTS['u']*cons + WEIGHTS['t']*t)
    return clamp(val, -cap, cap)

def calculate_bayesian_probability(p_market, evidence_list):
    """
    Calcula la probabilidad final combinando el precio de mercado con la evidencia recolectada.
    """
    l = logit(p_market)
    
    for ev in evidence_list:
        l += calculate_log_lr(ev)
    
    p_final = sigmoid(l)
    return p_final

def get_bayesian_summary(p_market, p_final):
    diff = p_final - p_market
    sentiment = "NEUTRAL"
    if diff > 0.05: sentiment = "BULLISH (Argo ve oportunidad)"
    if diff < -0.05: sentiment = "BEARISH (Mercado sobrevalorado)"
    
    return {
        "score": round(p_final, 3),
        "edge": round(diff, 3),
        "sentiment": sentiment
    }

```

---

## ARCHIVO: Argo_Watchdog.py
```python
import os
import time
import requests
import subprocess
import signal
from datetime import datetime
from dotenv import load_dotenv

# Configuración
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "data", "motor_heartbeat.txt")

# Comandos de ejecución (ajustados a la ruta del servidor)
PYTHON_PATH = "./venv/bin/python3"
STREAMLIT_PATH = "./venv/bin/streamlit"

def enviar_telegram(mensaje):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"})

def check_process(name_pattern):
    try:
        output = subprocess.check_output(["pgrep", "-f", name_pattern])
        return len(output.strip().split()) > 0
    except:
        return False

def start_agents():
    enviar_telegram("🚀 *Iniciando Agentes Argo...*")
    # Iniciar Motor
    subprocess.Popen(f"nohup {PYTHON_PATH} Argo_Motor_24x7.py > motor.log 2>&1 &", shell=True, cwd=BASE_DIR)
    # Iniciar Dashboard
    subprocess.Popen(f"nohup {STREAMLIT_PATH} run Argo_Dashboard_Autonomo.py --server.port 8501 > dashboard.log 2>&1 &", shell=True, cwd=BASE_DIR)
    time.sleep(5)
    status = get_status_msg()
    enviar_telegram(status)

def get_status_msg():
    motor_ok = check_process("Argo_Motor_24x7.py")
    dashboard_ok = check_process("Argo_Dashboard_Autonomo.py")
    
    hb_status = "Desconocido"
    if os.path.exists(HEARTBEAT_FILE):
        with open(HEARTBEAT_FILE, "r") as f:
            last_hb = float(f.read().strip())
            diff = time.time() - last_hb
            if diff < 300:
                hb_status = f"Activo (hace {int(diff)}s)"
            else:
                hb_status = f"⚠ RETRASADO (hace {int(diff)}s)"
    
    msg = "📊 *ESTADO DE ARGO*\n\n"
    msg += f"🤖 Motor: {'✅ ONLINE' if motor_ok else '❌ OFFLINE'}\n"
    msg += f"🖥 Dashboard: {'✅ ONLINE' if dashboard_ok else '❌ OFFLINE'}\n"
    msg += f"💓 Heartbeat: {hb_status}"
    return msg

def poll_telegram():
    last_update_id = 0
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    
    while True:
        try:
            r = requests.get(url, params={"offset": last_update_id + 1, "timeout": 30})
            data = r.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    text = msg.get("text", "")
                    sender_id = str(msg.get("from", {}).get("id", ""))
                    
                    if sender_id != str(CHAT_ID): continue # Solo responder al dueño
                    
                    if text == "/start":
                        start_agents()
                    elif text == "/status":
                        enviar_telegram(get_status_msg())
                    elif text == "/ping":
                        enviar_telegram("Pong! 🏓 El Watchdog está vivo.")
        except Exception as e:
            print(f"Error polling: {e}")
        time.sleep(1)

def watchdog_loop():
    sent_alert = False
    print("Watchdog iniciado...")
    
    # Iniciar el hilo de polling de telegram en el proceso principal o separado
    # Para simplicidad en un solo script, usaremos un loop que hace ambas cosas
    
    last_check_status = time.time()
    last_update_id = 0
    
    while True:
        try:
            # 1. Verificar Salud cada 2 minutos
            if time.time() - last_check_status > 120:
                motor_ok = check_process("Argo_Motor_24x7.py")
                hb_ok = False
                if os.path.exists(HEARTBEAT_FILE):
                    with open(HEARTBEAT_FILE, "r") as f:
                        last_hb = float(f.read().strip())
                        if time.time() - last_hb < 600: hb_ok = True
                
                if (not motor_ok or not hb_ok) and not sent_alert:
                    enviar_telegram("🚨 *ALERTA: Argo está caído o bloqueado!*\nUsa /status para verificar o /start para reiniciar.")
                    sent_alert = True
                elif motor_ok and hb_ok:
                    sent_alert = False
                
                last_check_status = time.time()

            # 2. Poll Telegram (Fast)
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", 
                             params={"offset": last_update_id + 1, "timeout": 10}, timeout=15)
            data = r.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message", {})
                    text = msg.get("text", "").lower()
                    sender_id = str(msg.get("from", {}).get("id", ""))
                    
                    if sender_id != str(CHAT_ID): continue 
                    
                    if "/start" in text:
                        start_agents()
                    elif "/status" in text:
                        enviar_telegram(get_status_msg())
                    elif "/ping" in text:
                        enviar_telegram("Pong! 🏓")
        
        except Exception as e:
            print(f"Error principal loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    watchdog_loop()

```

---

## ARCHIVO: requirements.txt
```text
crewai
crewai-tools
requests
openpyxl
python-dotenv
websocket-client
cryptography
pytz
pandas
streamlit
litellm
plotly
tavily-python

```

---

## ARCHIVO: .env.example
```text
# Copia este archivo como .env y llena con tus claves reales
GROQ_API_KEY=tu_clave_groq_aqui
TAVILY_API_KEY=tu_clave_tavily_aqui
TELEGRAM_TOKEN=tu_token_telegram_aqui
CHAT_ID=tu_chat_id_telegram_aqui
```

---
