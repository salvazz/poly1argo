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
    """Obtiene datos reales de Polymarket ANTES de lanzar los agentes."""
    try:
        url = "https://gamma-api.polymarket.com/events?limit=25&active=true&closed=false"
        response = requests.get(url, timeout=10)
        data = response.json()
        mercados = []
        for e in data:
            if e.get("volume", 0) > 50000:
                mercados.append(f"- Mercado: {e.get('title', 'N/A')} | Volumen USD: {e.get('volume', 0)} | Categoría: {e.get('category', 'Otro')}")
        if not mercados:
            return "No se encontraron mercados de alto volumen hoy."
        return "MERCADOS ACTIVOS EN POLYMARKET HOY:\n" + "\n".join(mercados[:5])
    except Exception as e:
        return f"Error leyendo Polymarket: {str(e)}"

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
if "historial" not in st.session_state:
    st.session_state["historial"] = cargar_historial()
if "saldo" not in st.session_state:
    # Calculamos el saldo basándose en el historial (Empieza en 50, se resta lo invertido)
    invertido = sum([float(x.get("Inversión", 0)) for x in st.session_state["historial"] if x.get("Acción") == "COMPRAR"])
    st.session_state["saldo"] = max(0, 50.0 - invertido)

st.title("🚢 Argo V3 - Panel 100% Local (Con Agentes Reales)")
st.markdown("Dashboard interactivo en caliente. Los agentes **tienen acceso a Internet** y comprarán de forma simulada en Polymarket.")

col_left, col_right = st.columns([1, 4])

with col_left:
    st.subheader("🔑 Tu Billetera")
    st.metric(label="Saldo (Simulado)", value=f"${st.session_state['saldo']:.2f}")
    api_key_input = st.text_input("Groq API Key (Recomendado)", type="password", value=os.environ.get("GROQ_API_KEY", ""))
    
    st.write("---")
    if st.button("🚀 Iniciar Escaneo y Simular", use_container_width=True):
        if not api_key_input:
            st.error("Introduce tu Groq API Key.")
        else:
            with st.spinner("🤖 Desplegando agentes en la API Gamma de Polymarket. Por favor, espera ~45 segundos..."):
                resultado_bruto = str(misiones_argo(api_key_input, st.session_state["saldo"]))
                st.session_state["ultimo_veredicto"] = resultado_bruto
                
                # Intentamos extraer el JSON de forma segura usando expresiones regulares
                try:
                    match = re.search(r'\{.*\}', resultado_bruto.replace('\n', ''), re.IGNORECASE)
                    if match:
                        json_str = match.group(0)
                        datos = json.loads(json_str)
                    else:
                        datos = json.loads(resultado_bruto) # Si el agente lo dio limpio
                        
                    # Agregamos al historial local si es válido
                    accion = datos.get("accion", "RECHAZAR").upper()
                    monto = float(datos.get("monto", 0.0))
                    
                    registro = {
                        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Mercado": datos.get("mercado", "Mercado Desconocido"),
                        "Acción": accion,
                        "Inversión": monto,
                        "Razonamiento": datos.get("razonamiento", "Sin justificación aportada")
                    }
                    
                    st.session_state["historial"].insert(0, registro)
                    guardar_historial(st.session_state["historial"]) # Guardamos en Excel local
                    
                    if accion == "COMPRAR":
                        st.session_state["saldo"] -= monto
                        st.success(f"✅ ¡Compra simulada! El crítico gastó ${monto:.2f}.")
                        enviar_telegram(f"🚀 *ARGO REPORTA COMPRA*\n\n*Mercado:* {datos.get('mercado')}\n*Inversión:* ${monto:.2f}\n*Veredicto crítico:* {datos.get('razonamiento')}\n\n*Saldo Restante:* ${st.session_state['saldo']:.2f}")
                    else:
                        st.warning("⚠️ El crítico ha vetado la operación.")
                        enviar_telegram(f"🛑 *ARGO REPORTA VETO*\n\n*Mercado Analizado:* {datos.get('mercado')}\n*Razón:* {datos.get('razonamiento')}")

                except Exception as e:
                    st.error("⚠️ Fallo en la traducción del juicio del robot a JSON. Verifica el texto en bruto.")

with col_right:
    tab1, tab2 = st.tabs(["🗃️ Registro de Operaciones y Decisiones", "🧠 Cerebro en Bruto"])
    
    with tab1:
        if len(st.session_state["historial"]) > 0:
            df = pd.DataFrame(st.session_state["historial"])
            
            # Resaltar colores según acción (Comprar o Rechazar)
            def color_accion(val):
                color = '#c6f6d5' if val == 'COMPRAR' else '#fed7d7'
                return f'background-color: {color}; color: black;'
            
            st.dataframe(
                df.style.map(color_accion, subset=['Acción']), 
                use_container_width=True, 
                height=400
            )
            st.caption(f"Estos datos se están guardando localmente en: {HISTORIAL_CSV}")
        else:
            st.info("Sin operaciones registradas aún. ¡Lanza la patrulla!")
            
    with tab2:
        st.write("Si quieres validar qué está pensando el sistema o si falló al guardar, mira el resultado sin procesar aquí:")
        if "ultimo_veredicto" in st.session_state:
            st.code(st.session_state["ultimo_veredicto"], language="json")
        else:
            st.write("Esperando a la primera ejecución...")
