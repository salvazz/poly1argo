# 🚢 Argo V3.5 - Hedge Fund Autónomo

Sistema de trading predictivo de alto rendimiento para **Polymarket** utilizando agentes de IA y Bayesiano.

## 📈 Características Principales

*   **Motor Bayesiano de Alta Fidelidad**: Cálculo de probabilidad basado en evidencias (inspirado en Polyseer).
*   **Comité de Agentes (CrewAI)**: Tres especialistas (Analista, Auditor de Riesgos y Estratega) colaboran en cada operación.
*   **Dashboard Platinum**: Interfaz premium en Streamlit para monitoreo 24/7.
*   **Vigilante Robusto (Watchdog)**: Sistema de salud y control vía Telegram con hilos dedicados.
*   **Trailing Stop Loss Dinámico**: Gestión automatizada de salidas para asegurar beneficios.

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
    Crea un archivo `.env` en la raíz con:
    ```env
    GROQ_API_KEY=tu_clave
    GEMINI_API_KEY=tu_clave
    TAVILY_API_KEY=tu_clave
    TELEGRAM_TOKEN=tu_token
    CHAT_ID=tu_id
    ```

## 🛠️ Uso del Ecosistema

*   **Motor Principal**: `python Argo_Motor_24x7.py` (Mantiene el sistema activo e invierte).
*   **Dashboard**: `streamlit run Argo_Dashboard_Autonomo.py` (Interfaz visual).
*   **Watchdog**: `python Argo_Watchdog.py` (Monitoreo de salud y comandos Telegram).
*   **Simulación**: `python simulate_trading.py` (Evalúa estrategias sin riesgo).
*   **Tests**: `python run_test_bayesian.py` (Lanza un análisis de prueba).

## 🛡️ Seguridad

*   El archivo `oracle.key` ha sido revocado y eliminado del rastreo.
*   El sistema utiliza firmas HMAC y EIP-712 para interactuar con Polymarket.
*   Todas las operaciones se auditan en `data/argo_audit.json`.

---
*Este proyecto tiene fines educativos y de investigación cuantitativa.*