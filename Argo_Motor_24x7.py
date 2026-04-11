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
        r1 = requests.get("https://gamma-api.polymarket.com/events?limit=25&active=true&closed=false", timeout=10)
        for e in r1.json():
            vol = e.get("volume", 0)
            if vol > 50000:
                prices = e.get("outcomePrices", ["0", "0"])
                if isinstance(prices, str): prices = json.loads(prices)
                mercados.append({"titulo": e.get("title", "N/A"), "volumen": vol, "precio": float(prices[0]), "categoria": "General"})
        r2 = requests.get("https://gamma-api.polymarket.com/events?limit=25&active=true&closed=false&tag=sports", timeout=10)
        for e in r2.json():
            vol = e.get("volume", 0)
            if vol > 2000:
                prices = e.get("outcomePrices", ["0", "0"])
                if isinstance(prices, str): prices = json.loads(prices)
                mercados.append({"titulo": e.get("title", "N/A"), "volumen": vol, "precio": float(prices[0]), "categoria": "Deportes"})
    except: pass
    if not mercados: return "No hay mercados."
    mercados.sort(key=lambda x: x["volumen"], reverse=True)
    res = [f"- [{m['categoria']}] {m['titulo']} | Precio: {m['precio']:.2f} | Vol: ${m['volumen']:,.0f}" for m in mercados[:10]]
    return "\n".join(res)

def ejecutar_mision():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: return
    datos_mercado = obtener_datos_polymarket()
    modelo = "groq/llama-3.3-70b-versatile"
    
    investigador = Agent(role="Investigador", goal="Elegir el mejor mercado.", backstory="Analista senior.", llm=modelo)
    critico = Agent(role="Crítico", goal="Decidir en JSON con TP/SL.", backstory="Gestor de fondos.", llm=modelo)

    t1 = Task(description=f"Analiza:\n{datos_mercado}", expected_output="Mercado top.", agent=investigador)
    t2 = Task(description="Genera JSON: {'accion': 'COMPRAR', 'mercado': '...', 'precio_clob': 0.5, 'take_profit': 0.6, 'stop_loss': 0.4, 'monto': 2.5, 'razonamiento': '...'}", expected_output="JSON puro", agent=critico)

    crew = Crew(agents=[investigador, critico], tasks=[t1, t2], verbose=False)
    output = str(crew.kickoff())
    
    try:
        clean_output = output[output.find("{"):output.rfind("}")+1]
        data = json.loads(clean_output)
        data['fecha'] = obtener_hora_espana()
        
        # Guardar (Append al CSV)
        df_new = pd.DataFrame([data])
        if os.path.exists(HISTORIAL_CSV):
            df_old = pd.read_csv(HISTORIAL_CSV)
            df_final = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_final = df_new
        df_final.to_csv(HISTORIAL_CSV, index=False)
        
        # Telegram rico en info
        if data['accion'] == "COMPRAR":
            msg = f"🚀 *ARGO COMPRA*\n*Mercado:* {data['mercado']}\n*Precio:* {data.get('precio_clob')}\n*TP:* {data.get('take_profit')} | *SL:* {data.get('stop_loss')}"
        else:
            msg = f"🛑 *ARGO VETO*\n*Mercado:* {data['mercado']}\n*Razón:* {data['razonamiento']}"
        enviar_telegram(msg)
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    print("🛰️ ARGO MOTOR 24/7 INICIADO...")
    enviar_telegram("🛰️ *SISTEMA ARGO ONLINE*\nIniciando patrulla autónoma cada 5 minutos.")
    while True:
        try:
            ejecutar_mision()
        except Exception as e:
            print(f"Error en el ciclo: {e}")
        time.sleep(300) # 5 minutos
