import streamlit as st

st.set_page_config(
    page_title="Argo V3 | Autonomous Trading", page_icon="🚢", layout="wide"
)

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
from crewai import Agent, Task, Crew
from crewai.tools import tool
import bayesian_engine

# Configuración de zona horaria España
SPAIN_TZ = pytz.timezone("Europe/Madrid")


def obtener_hora_espana():
    return datetime.now(SPAIN_TZ).strftime("%Y-%m-%d %H:%M:%S")


# ==========================================
# CONFIGURACIONES Y PERSISTENCIA GLOBAL
# ==========================================
load_dotenv()
HISTORIAL_CSV = os.path.join(os.path.dirname(__file__), "data", "Argo_Historial.csv")
HEARTBEAT_FILE = os.path.join(os.path.dirname(__file__), "data", "motor_heartbeat.txt")


def verificar_motor():
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE, "r") as f:
                last_heartbeat = float(f.read().strip())
            if time.time() - last_heartbeat < 180:
                return "ONLINE 🟢"
        except:
            pass
    return "OFFLINE 🔴"


def cargar_historial():
    if os.path.exists(HISTORIAL_CSV):
        return pd.read_csv(HISTORIAL_CSV).to_dict("records")
    return []


def guardar_historial(registros):
    df = pd.DataFrame(registros)
    df.to_csv(HISTORIAL_CSV, index=False)


def enviar_telegram(mensaje):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(
                url,
                json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"},
            )
        except Exception:
            pass


def obtener_datos_polymarket():
    mercados = []
    try:
        url = (
            "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false"
        )
        resp = requests.get(url, timeout=10)
        for e in resp.json():
            vol = e.get("volume", 0)
            if vol > 10000:
                prices = e.get("outcomePrices", ["0", "0"])
                if isinstance(prices, str):
                    prices = json.loads(prices)
                mercados.append(
                    {
                        "titulo": e.get("title", "N/A"),
                        "volumen": vol,
                        "precio": float(prices[0]) if prices else 0,
                        "volatilidad": abs(e.get("oneDayPriceChange", 0)),
                    }
                )
    except Exception:
        pass

    if not mercados:
        return "Sin datos."
    lineas = [
        f"- {m['titulo']} | Precio: {m['precio']:.2f} | Vol: ${m['volumen']:,.0f}"
        for m in mercados[:10]
    ]
    return "TOP MERCADOS:\n" + "\n".join(lineas)


def misiones_argo(api_key, saldo_actual, backend="Groq"):
    if backend == "Groq":
        os.environ["GROQ_API_KEY"] = api_key
        modelo_ia = "groq/llama-3.3-70b-versatile"
    else:
        from langchain_community.llms import Ollama

        modelo_ia = Ollama(model="llama3.1", base_url="http://localhost:11434")

    datos_mercado = obtener_datos_polymarket()

    investigador = Agent(
        role="Analista",
        goal="Elegir mercado.",
        backstory="Analista.",
        llm=modelo_ia,
        verbose=True,
    )
    gestor = Agent(
        role="Riesgos",
        goal="Monto inversión.",
        backstory="Actuario.",
        llm=modelo_ia,
        verbose=True,
    )
    critico = Agent(
        role="Auditor",
        goal="Veredicto JSON.",
        backstory="Crítico.",
        llm=modelo_ia,
        verbose=True,
    )

    tarea1 = Task(
        description=f"Analiza:\n{datos_mercado}",
        expected_output="Nombre mercado.",
        agent=investigador,
    )
    tarea2 = Task(
        description="Propón monto (máx 5%).",
        expected_output="Monto sugerido.",
        agent=gestor,
    )
    tarea_final = Task(
        description="JSON FINAL: {accion, mercado, precio_clob, take_profit, stop_loss, monto, razonamiento, evidencias}",
        expected_output="JSON puro.",
        agent=critico,
    )

    # BUG 7: Crew construida y kickoff() ejecutado
    crew = Crew(
        agents=[investigador, gestor, critico],
        tasks=[tarea1, tarea2, tarea_final],
        verbose=False,
    )
    resultado = crew.kickoff()
    return str(resultado)


# BUG 7 B: UI de Streamlit a nivel raíz (indentación 0) corregido (se removió set_page_config duplicado)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Outfit:wght@400;800&display=swap');
    :root { --accent: #8b5cf6; --text: #f8fafc; }
    .main { background: #030712; font-family: 'Inter', sans-serif; color: var(--text); }
</style>
""",
    unsafe_allow_html=True,
)

if "historial" not in st.session_state:
    st.session_state["historial"] = cargar_historial()
if "saldo" not in st.session_state:
    # BUG 11: Protección contra ValueError en cálculo de saldo
    try:
        invertido = sum(
            [
                float(x.get("Inversión", 0) or 0)
                for x in st.session_state["historial"]
                if x.get("Acción") == "COMPRAR"
            ]
        )
    except (ValueError, TypeError):
        invertido = 0.0
    st.session_state["saldo"] = max(0, 50.0 - invertido)

st.title("ARGO V3 PLATINUM")
st.markdown(
    "<p style='text-align: center; color: #94a3b8;'>Red Neuronal de Trading Autónomo en Polymarket</p>",
    unsafe_allow_html=True,
)

stat_col1, stat_col2, stat_col3 = st.columns(3)
stat_col1.metric("Cartera Simulada", f"${st.session_state['saldo']:.2f}")
stat_col2.metric(
    "Operaciones",
    len([x for x in st.session_state["historial"] if x.get("Acción") == "COMPRAR"]),
)
stat_col3.metric("Estatus del Motor", verificar_motor())

col_main, col_side = st.columns([3, 1])

with col_side:
    st.markdown("### ⚙️ Centro de Mando")
    try:
        with open(os.path.join(os.path.dirname(__file__), ".env"), "r") as f:
            for line in f:
                if "GROQ_API_KEY=" in line:
                    # BUG 9: split("=", 1) para permitir '=' en la clave
                    val = (
                        line.split("=", 1)[1].strip().replace('"', "").replace("'", "")
                    )
                    if len(val) > 10:
                        os.environ["GROQ_API_KEY"] = val
    except:
        pass

    api_key_env = os.environ.get("GROQ_API_KEY", "")
    api_key_input = api_key_env or st.text_input(
        "Ingresar Groq API Key (Manual)", type="password"
    )
    backend_mode = st.radio("🤖 Backend", ["Groq", "Ollama"])

    if st.button("🚀 Ejecutar Análisis Manual", use_container_width=True):
        with st.spinner("Ejecutando agentes..."):
            res_bruto = misiones_argo(
                api_key_input, st.session_state["saldo"], backend=backend_mode
            )
            try:
                match = re.search(r"\{.*\}", res_bruto.replace("\n", ""), re.IGNORECASE)
                if match:
                    d = json.loads(match.group(0))
                    status = d.get("accion", "RECHAZAR").upper()
                    monto = float(d.get("monto", 0.0))

                    registro = {
                        "Fecha": obtener_hora_espana(),
                        "Mercado": d.get("mercado", "N/A"),
                        "Acción": status,
                        "Precio": float(d.get("precio_clob", 0.5)),
                        "TP": d.get("take_profit", 0.0),
                        "SL": d.get("stop_loss", 0.0),
                        "Inversión": monto,
                        "Razonamiento": d.get("razonamiento", "..."),
                    }
                    st.session_state["historial"].insert(0, registro)
                    guardar_historial(st.session_state["historial"])
                    if status == "COMPRAR":
                        st.session_state["saldo"] -= monto
                    st.success(f"Detección: {status}")
                st.rerun()
            except:
                st.error("Error al procesar JSON")

with col_main:
    tabs = st.tabs(["📊 Monitor", "💼 Cartera", "🧠 Inteligencia", "📜 Historial"])
    with tabs[0]:
        st.markdown("### 📈 Auditoría de Pensamiento")
        audit_file = os.path.join(os.path.dirname(__file__), "data", "argo_audit.json")
        if os.path.exists(audit_file):
            try:
                df_audit = pd.read_json(audit_file)
                # BUG 10: applymap corregido a map para Pandas 2.1+
                st.dataframe(
                    df_audit.style.map(
                        lambda x: "color: #10b981"
                        if x == "COMPRAR"
                        else ("color: #ef4444" if x == "VETO" else ""),
                        subset=["accion"],
                    ),
                    use_container_width=True,
                )
            except:
                st.info("Sin registros.")
        else:
            st.info("Esperando escaneo...")

    with tabs[3]:
        st.markdown("### 📜 Historial")
        if st.session_state["historial"]:
            df_plot = pd.DataFrame(st.session_state["historial"])
            st.dataframe(df_plot, use_container_width=True)
            try:
                df_plot["Inversión"] = pd.to_numeric(
                    df_plot["Inversión"], errors="coerce"
                )
                df_plot["Balance"] = 50.0 - df_plot["Inversión"].cumsum()
                fig = px.line(df_plot, x="Fecha", y="Balance", title="Balance")
                st.plotly_chart(fig, use_container_width=True)
            except:
                pass

st.write("---")
st.caption("Argo V3.5 Platinum - Hedge Fund Autónomo")
