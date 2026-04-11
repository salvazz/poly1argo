import os
import time
import json
import pandas as pd
import requests
import pytz
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai_tools import TavilySearchResults

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORIAL_CSV = os.path.join(BASE_DIR, "data", "Argo_Historial.csv")
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
        r1 = requests.get("https://gamma-api.polymarket.com/events?limit=25&active=true&closed=false", timeout=10)
        for e in r1.json():
            vol = e.get("volume", 0)
            if vol > 50000:
                prices = e.get("outcomePrices", ["0", "0"])
                if isinstance(prices, str): prices = json.loads(prices)
                mercados.append({
                    "titulo": e.get("title", "N/A"), 
                    "volumen": vol, 
                    "precio": float(prices[0]) if prices else 0
                })
    except: pass
    if not mercados: return []
    mercados.sort(key=lambda x: x["volumen"], reverse=True)
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
    texto_mercados = "\n".join([f"- {m['titulo']} | Precio: {m['precio']:.2f}" for m in mercados])
    
    search_tool = TavilySearchResults(k=3) if tavily_key else None
    modelo = "groq/llama-3.3-70b-versatile"
    
    # 1. El Investigador
    inv = Agent(role="Analista", goal="Busca noticias positivas.", backstory="Optimista tecnológico.", tools=[search_tool] if search_tool else [], llm=modelo)
    
    # 2. El PESIMISTA (Abogado del diablo)
    pes = Agent(role="Abogado del Diablo", goal="Encuentra razones para NO comprar.", backstory="Escéptico radical. Solo cree en los hechos negativos.", tools=[search_tool] if search_tool else [], llm=modelo)
    
    # 3. El Crítico (Veredicto)
    cri = Agent(role="Gestor de Riesgos", goal="Decidir basandose en ambos.", backstory="Equilibrado y técnico.", llm=modelo)

    t1 = Task(description=f"Analiza estos mercados y busca noticias positivas:\n{texto_mercados}", expected_output="Mercado candidato.", agent=inv)
    t2 = Task(description="Analiza el candidato del Investigador y busca TODA LA BASURA y noticias negativas sobre ello. Destroza su argumento.", expected_output="Informe de riesgos.", agent=pes)
    t3 = Task(description="JSON final: {'accion': 'COMPRAR', 'mercado': '...', 'precio_clob': 0.5, 'take_profit': 0.7, 'stop_loss': 0.4, 'monto': 2.5, 'razonamiento': '...'}", expected_output="JSON puro.", agent=cri)

    crew = Crew(agents=[inv, pes, cri], tasks=[t1, t2, t3], process=Process.sequential, verbose=False)
    output = str(crew.kickoff())
    
    try:
        clean_output = output[output.find("{"):output.rfind("}")+1]
        data = json.loads(clean_output)
        data['fecha'] = obtener_hora_espana().strftime("%Y-%m-%d %H:%M:%S")
        data['estado'] = 'ABIERTA'
        data['max_precio'] = data.get('precio_clob', 0.1)
        
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
    print("🛰️ ARGO MOTOR V5 (COMITÉ + TRAILING SL) INICIADO...")
    informe_enviado_hoy = False
    ultimo_escaneo_compra = 0
    
    while True:
        try:
            ahora = obtener_hora_espana()
            
            # 1. Informe Diario a las 21:00
            if ahora.hour == 21 and ahora.minute == 0 and not informe_enviado_hoy:
                enviar_informe_diario()
                informe_enviado_hoy = True
            if ahora.hour == 22: # Reset para el dia siguiente
                informe_enviado_hoy = False

            # 2. Monitoreo rapido (Trailing SL)
            monitorear_y_vender()
            
            # 3. Escaneo de compras cada 10 min
            if time.time() - ultimo_escaneo_compra > 600:
                ejecutar_mision_compra()
                ultimo_escaneo_compra = time.time()
                
        except Exception as e: print(f"Error: {e}")
        time.sleep(60)
