# PIK'TA POS - Sistema de Punto de Venta

Sistema completo de punto de venta para restaurante con interfaz de escritorio (Tkinter) y servidor API para movil.

## Despliegue en Render (Gratis)

### Pasos:

1. **Crear cuenta en Render**: https://render.com (plan gratuito disponible)

2. **Subir codigo a GitHub**:
   ```bash
   cd "C:\Users\DAVIS\Desktop\PIK'TA_SOFT_FACT - copia"
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/TU_USUARIO/pikta-pos.git
   git push -u origin main
   ```

3. **Crear servicio en Render**:
   - Ir a https://dashboard.render.com
   - Click "New +" -> "Web Service"
   - Conectar repositorio GitHub
   - Configurar:
     - **Name**: pikta-pos-api
     - **Runtime**: Python
     - **Build Command**: `pip install -r requirements_render.txt`
     - **Start Command**: `gunicorn api_server:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
     - **Plan**: Free

4. **Variables de entorno** (en Render):
   - `PYTHON_VERSION`: 3.11
   - `PIKTA_JWT_SECRET`: (se genera automaticamente)
   - `PIKTA_PEPPER`: (se genera automaticamente)

5. **Deploy**: Render desplegara automaticamente al hacer push a GitHub

### Endpoints disponibles:

- `GET /api/version` - Version del sistema
- `POST /api/login` - Inicio de sesion
- `GET /api/menu` - Menu de productos
- `POST /api/pedidos` - Crear pedido
- `GET /api/pedidos/activos` - Pedidos activos
- Y mas...

### Credenciales por defecto:
- **admin** / admin (Administrador)

## Uso local (Escritorio)

```bash
# Ejecutar directamente
python main_app.py

# O usar el lanzador
Iniciar_PIKTA.bat
```

## Requisitos

- Python 3.11+
- Windows 10/11 (para la app de escritorio)
- Impresora termica (opcional)

## Desarrollado por

YAFA SOLUTIONS - 2026
