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

Imagina que el servidor es una casa mágica en la nube. Los agentes son robots que viven ahí.

### Instrucciones de Uso:

1. Ve a la casa (abre https://cloud.oracle.com y entra a tu tenancy).

2. Busca la puerta (la instancia corriendo en 158.179.208.247).

3. Para ejecutar análisis y compra:
   - Desde el dashboard: Ejecuta `streamlit run Argo_Dashboard_Autonomo.py` y haz clic en "💰 Ejecutar Compra Automática".
   - Desde móvil o PC, abre en navegador: `http://158.179.208.247:5000` y haz clic en "Ejecutar Análisis y Compra".
   - O en terminal: `curl -X POST http://158.179.208.247:5000/trade`

4. Para monitorear y vender:
   - Desde el dashboard: Haz clic en "📉 Ejecutar Monitoreo y Venta".
   - Abre `http://158.179.208.247:5000` y haz clic en "Ejecutar Monitoreo y Venta".
   - O terminal: `curl -X POST http://158.179.208.247:5000/monitor`

Los robots despiertan, analizan Polymarket con IA, deciden compras/ventas si hay ventaja, actualizan el historial CSV, y envían notificaciones por Telegram.

### Para que funcione automáticamente:
1. Accede a la instancia (usa Cloud Shell o consola OCI para ejecutar comandos).
2. Instala cron si no está: `sudo apt install cron`
3. Edita el crontab: `crontab -e`
4. Agrega estas líneas para ejecutar cada 20 minutos análisis y cada 10 minutos monitoreo:
   ```
   */20 * * * * curl -X POST http://localhost:5000/trade
   */10 * * * * curl -X POST http://localhost:5000/monitor
   ```
5. Guarda y sal (Ctrl+X, Y, Enter).

Ahora, los agentes ejecutarán automáticamente sin intervención. Revisa logs para confirmar.

### Notas:
- La app Flask corre en la instancia en puerto 5000.
- Si usas API Gateway, configura un deployment con backend HTTP a http://158.179.208.247:5000/trade
- Revisa logs en la instancia: `tail -f nohup.out`
- Asegura que el puerto 5000 esté abierto en la Security List de la VCN.

---
*Este proyecto tiene fines educativos y de investigación cuantitativa.*