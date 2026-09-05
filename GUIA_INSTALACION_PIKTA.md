# 🚀 Guía de Instalación: Sistema PIK'TA POS (Nube)

Esta guía detalla los pasos para instalar el sistema PIK'TA en una computadora nueva desde cero. El sistema funciona en **Modo Nube**, lo que permite sincronización en tiempo real con los dispositivos móviles.

---

## 1. Requisitos Previos
*   **Conexión a Internet**: Estable y permanente (necesaria para conectar con la base de datos).
*   **Sistema Operativo**: Windows 10 o Windows 11.
*   **Impresora Térmica**: Instalada en Windows con sus drivers correspondientes.

---

## 2. Instalación de Python (El Motor)
El sistema requiere Python para funcionar. Siga estos pasos cuidadosamente:

1.  Descargue el instalador oficial: [Python 3.12 para Windows](https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe).
2.  Abra el instalador.
3.  **⚠️ MUY IMPORTANTE**: En la primera pantalla, marque la casilla que dice **"Add Python to PATH"**. Si no la marca, el sistema no podrá iniciarse.
4.  Haga clic en **"Install Now"**.
5.  Al finalizar, haga clic en "Close".

---

## 3. Preparación de Archivos
1.  Cree una carpeta en su disco local llamada `C:\PIKTA`.
2.  Copie todos los archivos del proyecto dentro de esa carpeta.
3.  Asegúrese de que existan las siguientes carpetas y archivos:
    *   📁 `Imagenes/` (Fotos de los productos)
    *   📁 `assets/` (Iconos y logos)
    *   📄 `main_app.py` (Archivo principal)
    *   📄 `Iniciar_PIKTA.bat` (Lanzador del sistema)
    *   📄 `requirements.txt` (Configuración de librerías)

---

## 4. Configuración Automática (Primer Inicio)
No necesita instalar nada manualmente. El sistema lo hará por usted:

1.  Entre a la carpeta `C:\PIKTA`.
2.  Haga doble clic en el archivo **`Iniciar_PIKTA.bat`**.
3.  Se abrirá una ventana negra. **Espere unos minutos** mientras el sistema descarga e instala los componentes necesarios automáticamente.
4.  Al terminar, el sistema se abrirá solo y mostrará la pantalla de Login.

---

## 5. Acceso Directo y Personalización
Para facilitar el uso diario:

1.  Haga clic derecho sobre el archivo **`Iniciar_PIKTA.bat`** > **Enviar a** > **Escritorio (crear acceso directo)**.
2.  En el escritorio, cambie el nombre del icono a **"PIK'TA POS"**.
3.  **(Opcional)** Cambie el icono: Clic derecho > Propiedades > Cambiar Icono > Seleccione el archivo `assets/logo.ico`.

---

## 6. Configuración de Impresión
1.  Inicie sesión en el sistema.
2.  Vaya al módulo de **Caja / POS**.
3.  Al realizar la primera venta, el sistema le pedirá seleccionar la impresora. Seleccione su impresora térmica (Ej: `POS-80` o `XP-80`).

---

## 7. Soporte del Servidor
El "corazón" del sistema está en la nube: `https://Davis2025.pythonanywhere.com`.
*   Si el sistema no conecta, verifique que la PC tenga internet.
*   Los pedidos realizados desde el celular (APK) aparecerán automáticamente en este panel.

---
**Desarrollado por: PIK'TA SOFT FACT 2025**
