# Instrucciones para Construir el APK (Complemento Móvil)

Este proyecto utiliza **Kivy** y **Buildozer** para generar la aplicación Android (.apk).

## Requisitos Previos
1. Un sistema operativo **Linux** (Ubuntu recomendado) o usar **Google Colab**.
2. Python 3 instalado.
3. Instalar Buildozer: `pip install buildozer`
4. Instalar dependencias de Buildozer: `sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev`

## Pasos para generar el APK
1. Copia los archivos `mobile_app.py` y `buildozer.spec` a una carpeta vacía en tu sistema Linux.
2. Abre una terminal en esa carpeta.
3. Ejecuta el comando:
   ```bash
   buildozer -v android debug
   ```
4. El proceso tardará varios minutos la primera vez (descargará el SDK de Android, NDK, etc.).
5. Una vez finalizado, encontrarás el archivo `.apk` en la carpeta `bin/`.

## Configuración de Conexión
Para que la aplicación móvil funcione, debes editar la variable `SERVER_URL` en `mobile_app.py` con la dirección IP de la computadora donde corre el servidor principal (`main_app.py`).

Ejemplo:
`SERVER_URL = "http://192.168.1.100:5000"`

---
**Nota:** Este es un complemento móvil básico que se conecta a la API de `main_app.py`.
