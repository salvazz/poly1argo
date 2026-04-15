#!/bin/bash

# Argo V3.5 - Setup Optimizado para Instancia OCI
# Instala todo automáticamente: dependencias, Ollama con modelos IA locales, app y automatización

echo "🚀 Iniciando setup optimizado de Argo V3.5 en OCI..."

# Verificar si es root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Ejecuta como root: sudo ./setup.sh"
    exit 1
fi

# Actualizar sistema silenciosamente
apt update -qq && apt upgrade -y -qq

# Instalar dependencias base
apt install -y python3 python3-pip git curl wget

# Instalar Ollama (última versión)
curl -fsSL https://ollama.ai/install.sh | sh

# Esperar instalación
sleep 15

# Verificar instalación Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Error instalando Ollama"
    exit 1
fi

# Iniciar Ollama en background
ollama serve &

# Esperar que inicie
sleep 10

# Instalar modelos IA locales (optimizados para CPU)
echo "📥 Descargando modelos IA..."
ollama pull llama3.1:latest  # Modelo principal para análisis
ollama pull gemma2:9b        # Backup para consistencia

# Verificar modelos
echo "🔍 Verificando modelos..."
ollama list

if ollama list | grep -q "llama3.1"; then
    echo "✅ Modelos IA instalados correctamente"
else
    echo "❌ Error descargando modelos"
    exit 1
fi

# Clonar repositorio
git clone https://github.com/salvazz/poly1argo.git /home/opc/poly1argo
cd /home/opc/poly1argo

# Instalar dependencias Python
pip3 install -r requirements.txt gunicorn flask --quiet

# Crear directorio data
mkdir -p data

# Configurar .env básico (usuario debe agregar claves)
cat > .env << EOF
# Configura tus claves API aquí
TELEGRAM_TOKEN=
CHAT_ID=
GROQ_API_KEY=
GEMINI_API_KEY=
TAVILY_API_KEY=
EOF

# Configurar cron para ejecución automática (como opc)
crontab -u opc -l 2>/dev/null | { cat; echo "*/20 * * * * cd /home/opc/poly1argo && python3 app.py --trade"; } | crontab -u opc -
crontab -u opc -l 2>/dev/null | { cat; echo "*/10 * * * * cd /home/opc/poly1argo && python3 app.py --monitor"; } | crontab -u opc -

# Cambiar propietario a opc
chown -R opc:opc /home/opc/poly1argo

# Iniciar aplicación como opc
su - opc -c "cd /home/opc/poly1argo && gunicorn -w 2 -b 0.0.0.0:5000 app:app &"

# Verificar que la app responde
sleep 5
if curl -s http://localhost:5000 | grep -q "Argo"; then
    echo "✅ Aplicación web funcionando"
else
    echo "⚠️ Aplicación iniciada, verifica manualmente"
fi

# Información final
echo ""
echo "🎉 SETUP COMPLETO - Argo V3.5 listo en OCI"
echo "📍 URL: http://$(hostname -I | awk '{print $1}'):5000"
echo "🤖 IA Local: Ollama con llama3.1 y gemma2:9b"
echo "⏰ Automático: Ejecuta cada 20min análisis, 10min monitoreo"
echo "🔧 Configura .env en /home/opc/poly1argo/ con tus claves API"
echo "📊 Monitorea: tail -f /home/opc/poly1argo/nohup.out"