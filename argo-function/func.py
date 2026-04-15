import io
import os
import json
import datetime
from crewai import Agent, Task, Crew
from langchain_groq import ChatGroq
from fdk import response


def handler(ctx, data: io.BytesIO = None):
    # Configuración de identidad desde variables de entorno
    GROQ_KEY = os.environ.get("GROQ_API_KEY")
    TAVILY_KEY = os.environ.get("TAVILY_API_KEY")
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("CHAT_ID")

    if not GROQ_KEY:
        return response.Response(
            ctx,
            response_data=json.dumps({"error": "GROQ_API_KEY not set"}),
            headers={"Content-Type": "application/json"},
        )

    # Configuración del cerebro
    cerebro_groq = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_KEY)

    investigador = Agent(
        role="Analista de Mercados",
        goal="Buscar oportunidades de inversión con ventaja estadística",
        backstory="Experto en análisis técnico y fundamental de mercados predictivos.",
        llm=cerebro_groq,
        verbose=True,
    )

    gestor = Agent(
        role="Gestor de Riesgos",
        goal="Calcular riesgo para cuenta de $50",
        backstory="Especialista en el criterio de Kelly y preservación de capital.",
        llm=cerebro_groq,
        verbose=True,
    )

    critico = Agent(
        role="Crítico",
        goal="Auditar y aprobar solo oportunidades claras",
        backstory="Abogado del diablo, busca fallos en la lógica de inversión.",
        llm=cerebro_groq,
        verbose=True,
    )

    # Función de apoyo (modificada para no enviar Telegram, solo retornar)
    def ejecutar_mision():
        mision = Task(
            description="Analiza mercados reales de Polymarket hoy y busca una ventaja del 15%.",
            expected_output="Informe con veredicto [APROBADO] o [RECHAZADO]",
            agent=investigador,
        )
        flota = Crew(agents=[investigador, gestor, critico], tasks=[mision])
        reporte = flota.kickoff()
        return str(reporte)

    try:
        reporte = ejecutar_mision()
        response_data = {
            "status": "success",
            "timestamp": str(datetime.datetime.now()),
            "report": reporte,
        }
        return response.Response(
            ctx,
            response_data=json.dumps(response_data),
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        response_data = {
            "status": "error",
            "error": str(e),
            "timestamp": str(datetime.datetime.now()),
        }
        return response.Response(
            ctx,
            response_data=json.dumps(response_data),
            headers={"Content-Type": "application/json"},
        )
