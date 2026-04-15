import os
import time
import json
import pandas as pd
import requests
import pytz
import random
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai_tools import TavilySearchTool
import bayesian_engine
from google import genai


# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_CSV = os.path.join(BASE_DIR, "data", "Argo_Historial.csv")
HEARTBEAT_FILE = os.path.join(BASE_DIR, "data", "motor_heartbeat.txt")
LEARNING_FILE = os.path.join(BASE_DIR, "data", "model_learning.json")
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Zona horaria España
SPAIN_TZ = pytz.timezone("Europe/Madrid")


def obtener_hora_espana():
    return datetime.now(SPAIN_TZ)


def cargar_aprendizaje():
    if os.path.exists(LEARNING_FILE):
        with open(LEARNING_FILE, "r") as f:
            return json.load(f)
    return {"models": {}, "patterns": {}}


def guardar_aprendizaje(data):
    with open(LEARNING_FILE, "w") as f:
        json.dump(data, f, indent=4)


def actualizar_aprendizaje(modelo, exito, razon_error=None):
    data = cargar_aprendizaje()
    if modelo not in data["models"]:
        data["models"][modelo] = {"intentos": 0, "exitos": 0, "errores": {}}
    data["models"][modelo]["intentos"] += 1
    if exito:
        data["models"][modelo]["exitos"] += 1
    else:
        error_key = razon_error or "desconocido"
        data["models"][modelo]["errores"][error_key] = (
            data["models"][modelo]["errores"].get(error_key, 0) + 1
        )
    guardar_aprendizaje(data)


def seleccionar_modelo_inteligente(backends):
    data = cargar_aprendizaje()
    scores = {}
    for b in backends:
        modelo = b["model"]
        if modelo in data["models"]:
            stats = data["models"][modelo]
            if stats["intentos"] > 0:
                score = stats["exitos"] / stats["intentos"]
                # Penalizar errores recientes
                penalizacion = sum(stats["errores"].values()) * 0.1
                scores[modelo] = max(0, score - penalizacion)
            else:
                scores[modelo] = 0.5  # Neutral para nuevos
        else:
            scores[modelo] = 0.5
    # Seleccionar el mejor, con aleatoriedad para explorar
    mejor = max(scores, key=scores.get)
    if random.random() < 0.1:  # 10% explorar
        mejor = random.choice(list(scores.keys()))
    return next(b for b in backends if b["model"] == mejor)


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
        except Exception as e:
            print(f"Error enviando telegram: {e}")


def obtener_datos_polymarket():
    mercados = []
    try:
        r1 = requests.get(
            "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false",
            timeout=10,
        )
        for e in r1.json():
            vol = e.get("volume", 0)
            if vol > 10000:
                prices = e.get("outcomePrices", ["0", "0"])
                if isinstance(prices, str):
                    prices = json.loads(prices)
                change = abs(e.get("oneDayPriceChange", 0))

                mercados.append(
                    {
                        "titulo": e.get("title", "N/A"),
                        "volumen": vol,
                        "precio": float(prices[0]) if prices else 0,
                        "volatilidad": change,
                    }
                )
    except Exception as e:
        print(f"Error en API: {e}")


def ejecutar_mision_compra():
    api_key = os.environ.get("GROQ_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return

    mercados = obtener_datos_polymarket()
    if not mercados:
        return
    texto_mercados = "\n".join(
        [
            f"- {m['titulo']} | Precio: {m['precio']:.2f} | Volatilidad (24h): {m['volatilidad'] * 100:+.2f}%"
            for m in mercados
        ]
    )
    search_tool = TavilySearchTool(k=3) if tavily_key else None

    # BUG 4: Priorizar modelos cloud (Gemini) sobre locales
    backends = [
        {"model": "gemini/gemini-2.5-flash", "tools": False},
        {"model": "gemini/gemini-2.5-pro", "tools": False},
        {"model": "ollama/llama3.1", "tools": False},
        {"model": "ollama/gemma2:9b", "tools": False},
    ]
    exito_kickoff = False
    resultado_kickoff = None
    modelo_usado = None

    # Seleccionar modelo basado en aprendizaje
    backend_cfg = seleccionar_modelo_inteligente(backends)
    modelo_usado = backend_cfg["model"]

    backends_to_try = [backend_cfg] + [
        b for b in backends if b != backend_cfg
    ]  # Intentar mejor primero

    for backend_cfg in backends_to_try:
        b_modelo = backend_cfg["model"]
        use_tools = backend_cfg["tools"]
        try:
            print(f"Intentando análisis con: {b_modelo} (Tools: {use_tools})...")
            os.environ.pop("OPENAI_API_BASE", None)
            os.environ.pop("OPENAI_API_KEY", None)

            if "gemini/" in b_modelo:
                val_key = os.environ.get("GEMINI_API_KEY")
                os.environ["GEMINI_API_KEY"] = val_key if val_key else ""
                os.environ["GOOGLE_API_KEY"] = val_key if val_key else ""

            active_tools = [search_tool] if (use_tools and search_tool) else []

            inv = Agent(
                role="Analista",
                goal="Elegir mercado.",
                backstory="Experto.",
                tools=active_tools,
                llm=b_modelo,
            )
            pes = Agent(
                role="Riesgos",
                goal="Auditar.",
                backstory="Auditor.",
                tools=active_tools,
                llm=b_modelo,
            )
            cri = Agent(
                role="Estratega",
                goal="Veredicto JSON.",
                backstory="Estratega.",
                llm=b_modelo,
            )

            t1 = Task(
                description=f"Analiza:\n{texto_mercados}",
                expected_output="Nombre mercado.",
                agent=inv,
            )
            t2 = Task(
                description="Audita riesgos.",
                expected_output="Informe riesos.",
                agent=pes,
            )
            t3 = Task(
                description="Genera JSON: {accion, mercado, precio_clob, take_profit, stop_loss, razonamiento_tecnico, evidencias}",
                expected_output="Bloque JSON.",
                agent=cri,
            )

            crew = Crew(
                agents=[inv, pes, cri],
                tasks=[t1, t2, t3],
                process=Process.sequential,
                verbose=False,
            )
            resultado_kickoff = crew.kickoff()
            exito_kickoff = True
            actualizar_aprendizaje(b_modelo, True)
            break
        except Exception as e:
            error_msg = str(e)
            print(f"Error en {b_modelo}: {error_msg}")
            registrar_log_audit(
                "ERROR", "Sistema", 0, f"Fallo en {b_modelo}: {error_msg}"
            )
            actualizar_aprendizaje(b_modelo, False, error_msg)
            continue

    if not exito_kickoff:
        enviar_telegram("🚨 *COLAPSO DE IA:* Todos los modelos han fallado.")
        if modelo_usado:
            actualizar_aprendizaje(modelo_usado, False, "todos_fallaron")
        return

    output = str(resultado_kickoff)
    try:
        clean_output = output[output.find("{") : output.rfind("}") + 1]
        data = json.loads(clean_output)
        p_mercado = float(data.get("precio_clob", 0.5))

        # BUG 1: Definición de evidencias para evitar NameError
        evidencias = data.get("evidencias", [])
        if not isinstance(evidencias, list):
            evidencias = []

        brain_decision = consultar_gemini_brain(data["mercado"], p_mercado)
        if brain_decision:
            evidencias.append(
                {"type": "A", "verifiability": brain_decision.get("confianza", 0.7)}
            )

        p_final = bayesian_engine.calculate_bayesian_probability(p_mercado, evidencias)
        analisis = bayesian_engine.get_bayesian_summary(p_mercado, p_final)

        razon_final = data.get("razonamiento_tecnico") or data.get(
            "razonamiento", "Sin detalles"
        )
        registrar_log_audit(data["accion"], data["mercado"], p_final, razon_final)

        if data["accion"] == "COMPRAR" and analisis["edge"] > 0.03:
            data["Fecha"] = obtener_hora_espana().strftime("%Y-%m-%d %H:%M:%S")
            data["estado"] = "ABIERTA"
            data["max_precio"] = p_mercado
            data["Mercado"] = data["mercado"]
            data["Precio"] = p_mercado
            data["TP"] = data["take_profit"]
            data["SL"] = data["stop_loss"]
            data["Acción"] = "COMPRAR"
            data["Inversión"] = 2.5

            if os.path.exists(HISTORIAL_CSV):
                df_check = pd.read_csv(HISTORIAL_CSV)
                df_final = pd.concat(
                    [df_check, pd.DataFrame([data])], ignore_index=True
                )
            else:
                df_final = pd.DataFrame([data])

            df_final.to_csv(HISTORIAL_CSV, index=False)
            enviar_telegram(f"⚖️ *COMPRA EJECUTADA*\n*Mercado:* {data['mercado']}")
            actualizar_aprendizaje(modelo_usado, True)  # Éxito en trade
    # BUG 2: Reemplazado el bare except por registro audit
    except Exception as e:
        print(f"[ARGO ERROR] Fallo procesando resultado JSON: {e}")
        registrar_log_audit("ERROR_PARSE", "Sistema", 0, str(e))
        if modelo_usado:
            actualizar_aprendizaje(modelo_usado, False, "parse_error")


if __name__ == "__main__":
    while True:
        try:
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(str(time.time()))
            ejecutar_mision_compra()
            monitorear_y_vender()
            time.sleep(1200)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)
