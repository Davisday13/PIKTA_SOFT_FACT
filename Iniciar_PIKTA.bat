@echo off
setlocal
title Iniciando Sistema PIK'TA POS - Modo Nube

:: Cambiar al directorio donde esta el script
cd /d "%~dp0"

echo [1/3] Verificando conexion a internet...
ping 8.8.8.8 -n 1 -w 1000 > nul
if errorlevel 1 (
    echo ERROR: No hay conexion a internet.
    echo El sistema requiere internet para conectar con la base de datos en la nube.
    pause
    exit
)

echo [2/3] Verificando librerias...
:: Si no existe la carpeta venv, la crea e instala todo
if not exist ".venv" (
    echo Instalando entorno virtual y dependencias...
    python -m venv .venv
    call .venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

echo [3/3] Iniciando aplicacion...
:: Ejecutar con pythonw para que no se vea la consola negra
start /b "" ".venv\Scripts\pythonw.exe" "main_app.py"

echo Sistema iniciado correctamente.
timeout /t 3 > nul
exit
