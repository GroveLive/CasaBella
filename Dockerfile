   # Usar una imagen base oficial de Python
   FROM python:3.13-alpine

   # Establecer el directorio de trabajo en /app
   WORKDIR /app

   # Copiar los archivos de requisitos primero (para aprovechar el caché de capas)
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copiar el resto del código de la aplicación
   COPY . .

   # Exponer el puerto 8080
   EXPOSE 8080

   # Crear un directorio para las migraciones y la base de datos (si usas SQLite)
   RUN mkdir -p migrations

   # Comando para ejecutar la aplicación
   CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]