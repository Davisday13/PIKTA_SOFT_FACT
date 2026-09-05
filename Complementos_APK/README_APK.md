# Instrucciones para el APK (Opción B) y Sistema de Actualizaciones

Este proyecto utiliza **Kivy** y **Buildozer** para generar la aplicación Android (.apk) que sirve como cliente móvil para Meseros y Cocina.

## Sistema de Versiones y Actualizaciones (Opción B)

Al elegir la **Opción B** (Aplicación Nativa APK), debe tener en cuenta que las aplicaciones móviles instaladas en celulares no se actualizan solas (a menos que se suban a la Google Play Store).

Para evitar que los meseros utilicen una aplicación vieja que cause errores en la base de datos cuando el sistema principal se actualice, hemos implementado una **Verificación de Versión Obligatoria**:

1. Cada vez que inicie el sistema principal (`main_app.py`), el servidor API expone su versión actual (Ej: `1.0.0`).
2. Al abrir la app en el celular, ésta se conecta a la API y verifica su propia versión interna contra la del sistema.
3. **Si el sistema de la PC se actualiza** (por ejemplo, a la versión `1.1.0`), todos los celulares mostrarán una pantalla roja de **"ACTUALIZACIÓN REQUERIDA"** y se bloquearán por seguridad.
4. En ese momento, usted deberá generar un nuevo archivo `.apk` (siguiendo las instrucciones abajo), pasarlo a los celulares, y reinstalar la aplicación.

## Requisitos Previos para Compilar
1. Un sistema operativo **Linux** (Ubuntu recomendado) o usar **Google Colab**.
2. Python 3 instalado.
3. Instalar Buildozer: `pip install buildozer`
4. Instalar dependencias de Buildozer: `sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev`

## Pasos para generar el nuevo APK
1. Abra `api_server.py` y asegúrese de saber la versión actual (ej. `SYSTEM_VERSION = "1.0.0"`).
2. Abra `mobile_app.py` y actualice la variable `APK_VERSION` para que coincida exactamente con la del servidor.
3. Abra `mobile_app.py` y actualice la variable `SERVER_URL` con la IP actual de la computadora que hará de caja.
4. Copie los archivos `mobile_app.py` y `buildozer.spec` a una carpeta vacía en su sistema Linux.
5. Ejecute el comando:
   ```bash
   buildozer -v android debug
   ```
6. Pase el archivo `.apk` resultante (en la carpeta `bin/`) a los celulares y actualice.
