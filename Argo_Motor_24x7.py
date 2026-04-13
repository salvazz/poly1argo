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
from google import genai
import logging

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

def consultar_gemini_brain(mercado, precio):
    """Consulta a Gemini 1.5 Pro usando el nuevo SDK google-genai."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return None
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Leer contexto del proyecto
        doc_path = os.path.join(BASE_DIR, "docs", "ARGO_V3_CONSOLIDATED.md")
        contexto = ""
        if os.path.exists(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                contexto = f.read()[:30000]
                
        prompt = f"""
        ACTÚA COMO UN ESTRATEGA DE TRADING (NotebookLM AI).
        CONTEXTO: {contexto}
        MERCADO: {mercado} | PRECIO: {precio}
        Devuelve JSON: {{"veredicto": "FUERTE"|"DEBIL"|"EVITAR", "confianza": 0.0-1.0, "razon": "..."}}
        """
        response = client.models.generate_content(
            model='gemini-1.5-pro',
            contents=prompt
        )
        text = response.text
        clean_json = text[text.find("{"):text.rfind("}")+1]
        return json.loads(clean_json)
    except Exception as e:
        print(f"Error Gemini Brain: {e}")
        return None

def registrar_log_audit(accion, mercado, score, razon):
    """Guarda un registro de cada análisis para el dashboard."""
    log_file = os.path.join(BASE_DIR, "data", "argo_audit.json")
    nuevo_log = {
        "fecha": datetime.now(SPAIN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "accion": accion,
        "mercado": mercado,
        "score": round(score, 3) if score else 0,
        "razon": razon[:100] + "..."
    }
    try:
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                logs = json.load(f)
        else:
            logs = []
        logs.insert(0, nuevo_log)
        with open(log_file, "w") as f:
            json.dump(logs[:50], f, indent=4) # Guardamos los últimos 50
    except: pass

def ejecutar_mision_compra():
    api_key = os.environ.get("GROQ_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not api_key: return
    
    mercados = obtener_datos_polymarket()
    if not mercados: return
    texto_mercados = "\n".join([f"- {m['titulo']} | Precio: {m['precio']:.2f} | Volatilidad (24h): {m['volatilidad']*100:+.2f}%" for m in mercados])
    search_tool = TavilySearchTool(k=3) if tavily_key else None
    
    backends = [
        {"model": "groq/llama-3.3-70b-versatile", "tools": True},
        {"model": "groq/llama-3.1-8b-instant", "tools": False},   # Respaldo rápido y alta cuota
        {"model": "gemini/gemini-1.5-flash", "tools": False},     # Respaldo nube externo
        {"model": "ollama/llama3.1", "tools": False}
    ]
    exito_kickoff = False
    resultado_kickoff = None
    
    for backend_cfg in backends:
        b_modelo = backend_cfg["model"]
        use_tools = backend_cfg["tools"]
        try:
            print(f"Intentando análisis con: {b_modelo} (Tools: {use_tools})...")
            # Limpiar variables de entorno
            os.environ.pop("OPENAI_API_BASE", None)
            os.environ.pop("OPENAI_API_KEY", None)
            
            if "gemini" in b_modelo:
                val_key = os.environ.get("GEMINI_API_KEY")
                os.environ["GEMINI_API_KEY"] = val_key
                os.environ["GOOGLE_API_KEY"] = val_key
            
            if "ollama" in b_modelo:
                os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
                os.environ["OPENAI_API_KEY"] = "ollama"
            
            # Herramientas limitadas para fallbacks
            active_tools = [search_tool] if (use_tools and search_tool) else []
            
            # RE-CREAR AGENTES
            inv = Agent(
                role="Analista Cuantitativo de Polymarket", 
                goal="Detectar ineficiencias en el CLOB y arbitrajes.", 
                backstory="Experto en Gamma API y momentum.", 
                tools=active_tools, 
                llm=b_modelo
            )
            pes = Agent(
                role="Auditor de Riesgos", 
                goal="Identificar riesgos de oráculo y liquidez.", 
                backstory="Escéptico técnico de oráculos UMA.", 
                tools=active_tools, 
                llm=b_modelo
            )
            cri = Agent(
                role="Estratega Senior", 
                goal="Veredicto JSON final Kelly-based.", 
                backstory="Estratega de baja latencia.", 
                llm=b_modelo
            )

            # INTERFAZ DE TAREAS CUANTITATIVAS (Prompt Maestro)
            t1 = Task(
                description=f"""Analiza el CLOB de estos mercados:
                {texto_mercados}
                Busca señales de Momentum entre CEX (Binance/Coinbase) y Polymarket. 
                Identifica mercados con alta volatilidad y liquidez (Gamma API) donde haya un desfase de precio.""", 
                expected_output="Candidato técnico con justificación de liquidez y momentum.", 
                agent=inv
            )
            t2 = Task(
                description="""Realiza una auditoría matemática:
                1. ¿La suma de SÍ + NO en este mercado se desvía significativamente de $1.00? (Arbitraje).
                2. ¿Existe riesgo de resolución por oráculo UMA?
                3. Destroza el argumento alcista si el libro de órdenes es demasiado estrecho (spread alto).""", 
                expected_output="Informe de riesgos cuantitativos y viabilidad de arbitraje.", 
                agent=pes
            )
            t3 = Task(
                description="""Genera el veredicto técnico final en JSON. 
                Utiliza el Criterio de Kelly para sugerir el nivel de confianza.
                Considera si NegRisk:True permite una mayor eficiencia de capital.
                JSON FINAL:
                {
                  "accion": "COMPRAR" o "VETO",
                  "mercado": "...",
                  "precio_clob": 0.5,
                  "take_profit": 0.7,
                  "stop_loss": 0.4,
                  "razonamiento_tecnico": "...",
                  "evidencias": [...]
                }""", 
                expected_output="Bloque JSON técnico puro.", 
                agent=cri
            )

            # Definir la Crew con el modelo actual
            crew = Crew(agents=[inv, pes, cri], tasks=[t1, t2, t3], process=Process.sequential, verbose=False)
            resultado_kickoff = crew.kickoff()
            exito_kickoff = True
            break
        except Exception as e:
            error_msg = str(e)
            print(f"Error en {b_modelo}: {error_msg}")
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                enviar_telegram(f"🔄 *LIMITE:* {b_modelo} agotado. Saltando...")
            else:
                registrar_log_audit("ERROR", "Sistema", 0, f"Fallo en {b_modelo}: {error_msg}")
            continue

    if not exito_kickoff:
        enviar_telegram("🚨 *COLAPSO DE IA:* Todos los modelos han fallado. El motor entrará en espera.")
        return

    output = str(resultado_kickoff)
    
    try:
        clean_output = output[output.find("{"):output.rfind("}")+1]
        data = json.loads(clean_output)
        p_mercado = float(data.get('precio_clob', 0.5))
        
        # Calcular Probabilidad Bayesiana al estilo Polyseer
        # 4. Cerebro de Contexto (Gemini / NotebookLM)
        brain_decision = consultar_gemini_brain(data['mercado'], p_mercado)
        if brain_decision:
            evidencia_brain = {
                "type": "A", # Máxima prioridad
                "verifiability": brain_decision.get("confianza", 0.7),
                "consistency": 1.0 if brain_decision.get("veredicto") == "FUERTE" else 0.5,
                "corroborations": 1,
                "polarity": 1 if brain_decision.get("veredicto") != "EVITAR" else -1,
                "publishedAt": datetime.now().strftime("%Y-%m-%d")
            }
            evidencias.append(evidencia_brain)
            print(f"Cerebro Gemini: {brain_decision.get('veredicto')} (Confianza: {brain_decision.get('confianza')})")
        
        p_final = bayesian_engine.calculate_bayesian_probability(p_mercado, evidencias)
        analisis = bayesian_engine.get_bayesian_summary(p_mercado, p_final)
        
        # Recoger razonamiento (manejar ambas versiones del campo)
        razon_final = data.get('razonamiento_tecnico') or data.get('razonamiento', "Sin detalles")
        
        # Auditoría para Dashboard
        registrar_log_audit(data['accion'], data['mercado'], p_final, razon_final)
        data['razonamiento'] = razon_final
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
