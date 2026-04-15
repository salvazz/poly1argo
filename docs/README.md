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

### Despliegue Profesional en OCI (Configuración Completa)

#### Preparación de la Instancia
1. **Crear/Acceder Instancia**: Usa instancia Ubuntu en OCI (ej: VM.Standard.E5.Flex).
2. **Actualizar Sistema**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
3. **Instalar Dependencias Base**:
   ```bash
   sudo apt install python3 python3-pip git curl -y
   ```

#### Instalación Automática con Script
1. **Descargar Script**:
   ```bash
   wget https://raw.githubusercontent.com/salvazz/poly1argo/main/setup.sh
   chmod +x setup.sh
   ```
2. **Ejecutar Setup Completo**:
   ```bash
   ./setup.sh
   ```
   - Instala Ollama y modelos IA (llama3.1, gemma2:9b).
   - Clona el repositorio.
   - Instala dependencias Python.
   - Configura cron para ejecución automática.
   - Inicia la aplicación web.

#### Configuración Manual de Claves API
Después del setup, configura `.env`:
```bash
nano poly1argo/.env
```
Agrega:
```
TELEGRAM_TOKEN=tu_token
CHAT_ID=tu_chat_id
GROQ_API_KEY=tu_groq_key
GEMINI_API_KEY=tu_gemini_key
TAVILY_API_KEY=tu_tavily_key
```

#### Verificación de Procesos
- **Ollama**: `ollama list` (debe mostrar modelos).
- **App Web**: `curl http://localhost:5000` (debe responder).
- **Cron**: `crontab -l` (debe tener líneas para --trade y --monitor).
- **Logs**: `tail -f nohup.out` (para ver ejecución).

#### Acceso Externo
- **Interfaz Web**: http://[IP_INSTANCIA]:5000
- **API Directa**: curl -X POST http://[IP_INSTANCIA]:5000/trade
- **Telegram**: Recibe notificaciones automáticas.

#### Monitoreo y Mantenimiento
- Reinicia app: `pkill gunicorn && cd poly1argo && gunicorn -w 4 -b 0.0.0.0:5000 app:app &`
- Actualizar: `cd poly1argo && git pull && pip3 install -r requirements.txt`
- Backup data: Copia `poly1argo/data/` regularmente.

El sistema ahora opera 24/7 con IA local, sin dependencias externas fallidas.

### Notas:
- La app Flask corre en la instancia en puerto 5000.
- Si usas API Gateway, configura un deployment con backend HTTP a http://158.179.208.247:5000/trade
- Revisa logs en la instancia: `tail -f nohup.out`
- Asegura que el puerto 5000 esté abierto en la Security List de la VCN.

---
*Este proyecto tiene fines educativos y de investigación cuantitativa.*