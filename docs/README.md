# 🚢 Argo V3.5 - Hedge Fund Autónomo

Sistema de trading predictivo de alto rendimiento para **Polymarket** utilizando agentes de IA y Bayesiano.

## 📈 Características Principales

*   **Motor Bayesiano de Alta Fidelidad**: Cálculo de probabilidad basado en evidencias (inspirado en Polyseer).
*   **Comité de Agentes (CrewAI)**: Tres especialistas supervisados por un Cerebro Gemini.
*   **Dashboard Platinum**: Interfaz premium en Streamlit para monitoreo 24/7.
*   **Vigilante Robusto (Watchdog)**: Sistema de salud y control vía Telegram con hilos dedicados.
*   **Control de Riesgos**: Implementación de Trailing Stop Loss y Criterio de Kelly.

## 🚀 Instalación y Setup

1.  **Clona el repositorio**:
    ```bash
    git clone https://github.com/salvazz/poly1argo.git
    cd poly1argo
    ```

2.  **Configura el entorno**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Linux/Mac
    .\venv\Scripts\activate   # En Windows
    pip install -r requirements.txt
    ```

3.  **Variables de Entorno (.env)**:
    Crea un archivo `.env` en la raíz con tus claves de Groq, Gemini, Tavily y Telegram.

## 🛠️ Archivos Reales del Proyecto

*   **Argo_Motor_24x7.py**: El motor principal que ejecuta el bucle de trading infinito.
*   **Argo_Dashboard_Autonomo.py**: Dashboard interactivo para visualizar el estado y las evidencias.
*   **Argo_Watchdog.py**: Vigilante que reinicia el sistema si falla y responde comandos por Telegram.
*   **bayesian_engine.py**: El núcleo matemático del sistema.
*   **simulate_trading.py**: Simulador de Monte Carlo para probar el edge de la IA.

## 🛡️ Seguridad

*   `oracle.key` está en el `.gitignore` y no debe ser compartido.
*   Las claves API se gestionan exclusivamente vía `.env`.

## 🌐 Despliegue en Oracle Cloud (Servidor)

El proyecto está subido a Oracle Cloud. Para ejecutar los agentes desde el servidor:

Imagina que el servidor es una casa mágica. Los agentes son robots que viven ahí.

1. Ve a la casa (abre https://cloud.oracle.com).

2. Busca la puerta secreta (API Gateway > Deployments > copia la URL como https://casa-magica.com).

3. Toca el timbre para comprar: En Cloud Shell, escribe:
   ```
   curl -X POST https://casa-magica.com/argo/trade
   ```

4. Toca el timbre para vender: Cambia "trade" por "monitor".

Los robots despiertan, miran mercados, compran o venden, y avisan por Telegram.

Si no funciona, revisa logs: `ssh ubuntu@158.179.208.247 tail -f nohup.out`.

---
*Este proyecto tiene fines educativos y de investigación cuantitativa.*