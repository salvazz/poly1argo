import os
import time
import datetime
import requests
from crewai import Agent, Task, Crew
from langchain_groq import ChatGroq

# --- CONFIGURACIÓN DE IDENTIDAD ---
GROQ_KEY = os.environ.get("GROQ_API_KEY")
TAVILY_KEY = os.environ.get("TAVILY_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# --- 1. CONFIGURACIÓN DEL CEREBRO (Sólido para la nube) ---
cerebro_groq = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    groq_api_key=GROQ_KEY
)

# --- 2. LA TRIPULACIÓN (Con el objeto LLM correcto) ---
investigador = Agent(
    role='Investigador', 
    goal='Detectar oportunidades en Polymarket', 
    backstory='Experto en mercados predictivos y tendencias.',
    llm=cerebro_groq,
    verbose=True
)

gestor = Agent(
    role='Gestor de Riesgos', 
    goal='Calcular riesgo para cuenta de $50', 
    backstory='Especialista en el criterio de Kelly y preservación de capital.',
    llm=cerebro_groq,
    verbose=True
)

critico = Agent(
    role='Crítico', 
    goal='Auditar y aprobar solo oportunidades claras', 
    backstory='Abogado del diablo, busca fallos en la lógica de inversión.',
    llm=cerebro_groq,
    verbose=True
)

# --- 3. FUNCIONES DE APOYO ---
def enviar_alerta(mensaje):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

def ejecutar_mision():
    mision = Task(
        description="Analiza mercados reales de Polymarket hoy y busca una ventaja del 15%.", 
        expected_output="Informe con veredicto [APROBADO] o [RECHAZADO]", 
        agent=investigador
    )
    flota = Crew(agents=[investigador, gestor, critico], tasks=[mision])
    reporte = flota.kickoff()
    
    if "[APROBADO]" in str(reporte):
        enviar_alerta(f"🚢 *ARGO CLOUD VIGILANCIA*\n\n{reporte}")

# --- 4. BUCLE ETERNO ---
if __name__ == "__main__":
    print("🚀 Argo iniciando guardia 24/7 en la nube...")
    while True:
        try:
            ejecutar_mision()
            print(f"✅ Guardia completada a las {datetime.datetime.now()}. Durmiendo 4 horas...")
        except Exception as e:
            print(f"❌ Error durante la misión: {e}")
        
        time.sleep(14400)
