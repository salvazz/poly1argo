#!/bin/bash

# Argo V3.5 - Setup Script para Instancia OCI
# Instala dependencias, Ollama, modelos, y configura ejecución automática

echo "🚀 Iniciando setup de Argo en instancia OCI..."

# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python y pip
sudo apt install python3 python3-pip -y

# Instalar git
sudo apt install git -y

# Descargar proyecto desde Git
git clone https://github.com/salvazz/poly1argo.git
cd poly1argo

# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Esperar a que Ollama se instale
sleep 10

# Descargar modelos
ollama pull llama3.1
ollama pull gemma2:9b

# Iniciar Ollama en background
ollama serve &

# Esperar a que inicie
sleep 10

# Verificar Ollama
curl -s http://localhost:11434/api/tags | grep llama3.1

if [ $? -eq 0 ]; then
    echo "✅ Ollama listo con modelos"
else
    echo "❌ Error en Ollama"
    exit 1
fi

# Instalar dependencias
pip3 install -r requirements.txt
pip3 install gunicorn flask

# Crear .env vacío (configurar claves manualmente)
touch .env

# Crear directorio data
mkdir -p data

# Configurar cron para ejecución automática
(crontab -l ; echo "*/20 * * * * cd /home/opc/poly1argo && python3 app.py --trade") | crontab -
(crontab -l ; echo "*/10 * * * * cd /home/opc/poly1argo && python3 app.py --monitor") | crontab -

# Iniciar app con Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app &

echo "🎉 Setup completo. Argo ejecutándose automáticamente."
echo "Configura .env con tus claves API."
echo "Accede a http://158.179.208.247:5000 para interfaz web."