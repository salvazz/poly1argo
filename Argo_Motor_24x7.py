import os
import time
import json
import pandas as pd
import requests
import pytz
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_CSV = os.path.join(BASE_DIR, "data", "Argo_Historial.csv")
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Zona horaria España
SPAIN_TZ = pytz.timezone('Europe/Madrid')

def obtener_hora_espana():
    return datetime.now(SPAIN_TZ).strftime("%Y-%m-%d %H:%M:%S")

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
        # General
        r1 = requests.get("https://gamma-api.polymarket.com/events?limit=25&active=true&closed=false", timeout=10)
        for e in r1.json():
            vol = e.get("volume", 0)
            if vol > 50000:
                mercados.append({"titulo": e.get("title", "N/A"), "volumen": vol, "categoria": "General"})
        # Deportes
        r2 = requests.get("https://gamma-api.polymarket.com/events?limit=25&active=true&closed=false&tag=sports", timeout=10)
        for e in r2.json():
            vol = e.get("volume", 0)
            if vol > 2000:
                mercados.append({"titulo": e.get("title", "N/A"), "volumen": vol, "categoria": "Deportes"})
    except: pass
    
    if not mercados: return "No hay mercados claros ahora."
    mercados.sort(key=lambda x: x["volumen"], reverse=True)
    res = [f"- [{m['categoria']}] {m['titulo']} | Vol: ${m['volumen']:,.0f}" for m in mercados[:10]]
    return "\n".join(res)

def ejecutar_mision():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: return
    
    datos_mercado = obtener_datos_polymarket()
    modelo = "groq/llama-3.3-70b-versatile"
    
    investigador = Agent(
        role="Investigador Jefe",
        goal="Seleccionar el mercado mas seguro de la lista.",
        backstory="Eres experto en detectar tendencias seguras.",
        llm=modelo
    )
    
    critico = Agent(
        role="Crítico Judicial",
        goal="Decide COMPRAR o RECHAZAR en JSON puro.",
        backstory="Odias perder dinero simulado.",
        llm=modelo
    )

    t1 = Task(description=f"Analiza estos mercados:\n{datos_mercado}\nEscoge uno.", expected_output="Nombre mercado.", agent=investigador)
    t2 = Task(description="Genera el JSON final: {'accion': 'COMPRAR'/'RECHAZAR', 'mercado': '...', 'monto': 2.50, 'razonamiento': '...'}", expected_output="JSON puro", agent=critico)

    crew = Crew(agents=[investigador, critico], tasks=[t1, t2], verbose=False)
    output = str(crew.kickoff())
    
    try:
        # Limpieza básica para extraer JSON si el LLM pone texto alrededor
        clean_output = output[output.find("{"):output.rfind("}")+1]
        data = json.loads(clean_output)
        
        # Guardar en CSV
        data['fecha'] = obtener_hora_espana()
        df_new = pd.DataFrame([data])
        if os.path.exists(HISTORIAL_CSV):
            df_old = pd.read_csv(HISTORIAL_CSV)
            df_final = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_final = df_new
        
        os.makedirs(os.path.dirname(HISTORIAL_CSV), exist_ok=True)
        df_final.to_csv(HISTORIAL_CSV, index=False)
        
        # Telegram
        prefijo = "🚀 *COMPRA*" if data['accion'] == "COMPRAR" else "🛑 *VETO*"
        enviar_telegram(f"{prefijo}\n*Mercado:* {data['mercado']}\n*Razón:* {data['razonamiento']}")
        print(f"Misión completada: {data['accion']}")
        
    except Exception as e:
        print(f"Error procesando salida: {e}")

if __name__ == "__main__":
    print("🛰️ ARGO MOTOR 24/7 INICIADO...")
    enviar_telegram("🛰️ *SISTEMA ARGO ONLINE*\nIniciando patrulla autónoma cada 5 minutos.")
    while True:
        try:
            ejecutar_mision()
        except Exception as e:
            print(f"Error en el ciclo: {e}")
        time.sleep(300) # 5 minutos
