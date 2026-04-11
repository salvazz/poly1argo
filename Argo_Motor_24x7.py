import os
import time
import json
import pandas as pd
import requests
import pytz
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai_tools import TavilySearchResults

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
                mercados.append({
                    "titulo": e.get("title", "N/A"), 
                    "volumen": vol, 
                    "precio": float(prices[0]) if prices else 0,
                    "id": e.get("id")
                })
    except: pass
    if not mercados: return []
    mercados.sort(key=lambda x: x["volumen"], reverse=True)
    return mercados[:10]

def monitorear_y_vender():
    """Revisa posiciones abiertas y las cierra si tocan TP o SL."""
    if not os.path.exists(HISTORIAL_CSV): return
    
    df = pd.read_csv(HISTORIAL_CSV)
    if 'estado' not in df.columns: df['estado'] = 'ABIERTA'
    
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
            
            cerrar = False
            motivo = ""
            
            if p_actual >= tp:
                cerrar = True
                motivo = f"✅ TAKE PROFIT alcanzado ({p_actual})"
            elif p_actual <= sl:
                cerrar = True
                motivo = f"🛑 STOP LOSS ejecutado ({p_actual})"
            
            if cerrar:
                df.at[idx, 'estado'] = 'CERRADA'
                df.at[idx, 'precio_cierre'] = p_actual
                df.to_csv(HISTORIAL_CSV, index=False)
                enviar_telegram(f"📉 *OPERACIÓN CERRADA*\n*Mercado:* {mercado}\n*Resultado:* {motivo}")

def ejecutar_mision_compra():
    api_key = os.environ.get("GROQ_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not api_key: return
    
    mercados = obtener_datos_polymarket()
    if not mercados: return
    
    texto_mercados = "\n".join([f"- {m['titulo']} | Precio: {m['precio']:.2f} | Vol: ${m['volumen']:,.0f}" for m in mercados])
    
    # Herramienta de búsqueda
    search_tool = TavilySearchResults(k=3) if tavily_key else None
    modelo = "groq/llama-3.3-70b-versatile"
    
    investigador = Agent(
        role="Analista de Inteligencia",
        goal="Investigar noticias reales y elegir el mercado mas probable.",
        backstory="Eres experto en OSINT y predices eventos geopoliticos y deportivos.",
        tools=[search_tool] if search_tool else [],
        llm=modelo
    )
    
    critico = Agent(
        role="Gestor de Riesgos",
        goal="Validar la compra y establecer TP/SL estrictos.",
        backstory="No toleras perdidas. Quieres ganar un 20% minimo.",
        llm=modelo
    )

    t1 = Task(
        description=f"1. Analiza estos mercados:\n{texto_mercados}\n2. BUSCA NOTICIAS sobre los 2 mas interesantes.\n3. Elige el mejor.",
        expected_output="Nombre del mercado y resumen de noticias que apoyan la decision.",
        agent=investigador
    )
    
    t2 = Task(
        description="Genera JSON: {'accion': 'COMPRAR', 'mercado': '...', 'precio_clob': 0.5, 'take_profit': 0.7, 'stop_loss': 0.4, 'monto': 2.5, 'razonamiento': '...', 'noticia': 'fuente noticia'}",
        expected_output="JSON puro con estrategia completa.",
        agent=critico
    )

    crew = Crew(agents=[investigador, critico], tasks=[t1, t2], verbose=False)
    output = str(crew.kickoff())
    
    try:
        clean_output = output[output.find("{"):output.rfind("}")+1]
        data = json.loads(clean_output)
        data['fecha'] = obtener_hora_espana()
        data['estado'] = 'ABIERTA'
        
        # Evitar duplicados si ya esta abierta
        if os.path.exists(HISTORIAL_CSV):
            df_check = pd.read_csv(HISTORIAL_CSV)
            if data['mercado'] in df_check[df_check['estado'] == 'ABIERTA']['Mercado'].values:
                return # Ya tenemos esta operacion abierta
            df_final = pd.concat([df_check, pd.DataFrame([data])], ignore_index=True)
        else:
            df_final = pd.DataFrame([data])
            
        df_final.to_csv(HISTORIAL_CSV, index=False)
        
        if data['accion'] == "COMPRAR":
            enviar_telegram(f"🚀 *NUEVA COMPRA INTELIGENTE*\n*Mercado:* {data['mercado']}\n*TP:* {data['take_profit']} | *SL:* {data['stop_loss']}\n*Fuente:* {data.get('noticia', 'Analisis IA')}")
    except: pass

if __name__ == "__main__":
    print("🛰️ ARGO MOTOR V4 (NOTICIAS + CIERRES) INICIADO...")
    while True:
        try:
            monitorear_y_vender()
            ejecutar_mision_compra()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(300) # 5 minutos
