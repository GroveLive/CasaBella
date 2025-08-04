FROM python:3.13-alpine 
# Establecer el directorio de trabajo
WORKDIR /app
# Copiar requirements.txt e instalar dependencias
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt
# Copiar el resto del código
COPY . .
EXPOSE 3000
CMD [ "python", "app.py" ]
#CMD sh -c "gunicorn --bind 0.0.0.0:8081 --workers 4 --forwarded-allow-ips=*  wsgi:app"