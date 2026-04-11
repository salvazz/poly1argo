# Proyecto Argo

Bot de trading automatizado para Polymarket utilizando CrewAI y agentes de IA.

## Descripción

Argo es un sistema de trading predictivo que utiliza agentes de IA para analizar mercados en Polymarket, gestionar riesgos con el Criterio de Kelly, y ejecutar operaciones de manera segura.

## Características

- **Análisis de Mercados**: Agentes que buscan oportunidades en tiempo real usando Tavily Search.
- **Gestión de Riesgos**: Implementación del Criterio de Kelly para posiciones óptimas.
- **Aprendizaje Continuo**: Sistema de lecciones aprendidas para evitar errores recurrentes.
- **Dashboard Interactivo**: Interfaz en Streamlit para monitoreo y control.
- **Notificaciones**: Alertas vía Telegram.
- **Modo Piloto Automático**: Ejecución automática de trades aprobados.

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/salvazz/proyecto-argo.git
   cd proyecto-argo
   ```

2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Configura variables de entorno:
   Crea un archivo `.env` con tus claves API:
   ```
   GROQ_API_KEY=tu_clave_groq
   TAVILY_API_KEY=tu_clave_tavily
   TELEGRAM_TOKEN=tu_token_telegram
   CHAT_ID=tu_chat_id
   ```

## Uso

- **Simulación**: Ejecuta `python argo_full.py` para análisis simulado.
- **Dashboard**: Ejecuta `streamlit run argo_terminal.py` para la interfaz web.
- **Modo Real**: Usa `argo_real.py` con datos reales (requiere API de Polymarket).

## Archivos Principales

- `argo_terminal.py`: Dashboard principal en Streamlit.
- `argo_real.py`: Análisis con datos reales.
- `lecciones.py`: Sistema de aprendizaje.
- `registro_operaciones.py`: Registro de operaciones.
- `modo_piloto.py`: Ejecución automática.

## Seguridad

- Las claves API se cargan desde `.env` (no incluido en el repo).
- Usa cuentas de prueba para desarrollo.
- El bot está diseñado para posiciones conservadoras (5-10% del capital).

## Licencia

Este proyecto es para fines educativos. No se recomienda usar en producción sin pruebas exhaustivas.

## Contribuciones

Bienvenidas. Crea un issue o pull request.