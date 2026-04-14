#!/bin/bash
# Script de despliegue para Argo V3 en servidor

echo "🚀 Iniciando despliegue de Argo V3..."

# Instalar dependencias del sistema (ej. para Ollama si es necesario)
# sudo apt update && sudo apt install -y python3 python3-pip

# Clonar o actualizar repo
if [ ! -d "poly1argo" ]; then
    git clone https://github.com/salvazz/poly1argo.git
    cd poly1argo
else
    cd poly1argo
    git pull origin main
fi

# Configurar entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Verificar que Ollama esté corriendo (opcional)
# ollama serve &

# Crear directorios de datos
mkdir -p data

# Configurar .env (debes crear este archivo manualmente con tus claves)
# cp .env.example .env
# nano .env  # Editar con tus claves

echo "✅ Despliegue completado. Para iniciar:"
echo "  Motor: python Argo_Motor_24x7.py"
echo "  Dashboard: streamlit run Argo_Dashboard_Autonomo.py --server.port 8501"
echo "  Watchdog: python Argo_Watchdog.py"

# Opcional: Ejecutar con PM2 o systemd para producción
# pm2 start Argo_Motor_24x7.py --name "argo-motor"
# pm2 start Argo_Watchdog.py --name "argo-watchdog"
# pm2 start "streamlit run Argo_Dashboard_Autonomo.py --server.port 8501" --name "argo-dashboard"