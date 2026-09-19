FROM python:3.11-slim

# Forzar codificación UTF-8 en la entrada/salida de Python
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8

WORKDIR /app

# Instalar git por si tienes dependencias desde GitHub
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código del proyecto
COPY . .

# Exponer el puerto de FastAPI
EXPOSE 8000

# Apuntar a la subcarpeta app -> archivo main.py -> instancia app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]