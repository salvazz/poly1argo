FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos
COPY requirements.txt .
COPY . .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorios de datos
RUN mkdir -p data

# Exponer puerto para dashboard
EXPOSE 8501

# Comando por defecto (puedes override)
CMD ["python", "Argo_Motor_24x7.py"]