# 🧪 Guía de Validación: Prueba de Funcionalidad

Para probar el sistema de restaurante automatizado, sigue estos pasos en orden.

---

## 🟢 Paso 1: Configuración de Base de Datos
Ejecuta el archivo [schema.sql](file:///c:/Users/DAVIS/Downloads/files%20(2)/schema.sql) en tu motor PostgreSQL.
Esto creará las tablas, los datos iniciales (combos, ingredientes) y la lógica de descuento automático.

---

## 🟣 Paso 2: Importar Flujo en n8n
1. Abre tu instancia de n8n.
2. Ve a **Workflows > Import from File** y selecciona [flujo_maestro_n8n.json](file:///c:/Users/DAVIS/Downloads/files%20(2)/flujo_maestro_n8n.json).
3. Asegúrate de configurar las credenciales de PostgreSQL en los nodos correspondientes.
4. Haz clic en **Execute Workflow** para ponerlo en modo espera de datos.

---

## 🟢 Paso 3: Simular un Pedido (Entrada)
Usa el script de PowerShell [test_order.ps1](file:///c:/Users/DAVIS/Downloads/files%20(2)/test_order.ps1) para enviar un pedido de prueba:
1. Abre una terminal (PowerShell).
2. Ejecuta: `.\test_order.ps1`
   - *Nota: Asegúrate de que la URL del webhook en el script coincida con la de tu n8n.*

---

## 🟠 Paso 4: Verificar Procesamiento (Salida)
Ejecuta estas consultas SQL para validar que n8n hizo su trabajo:

```sql
-- 1. ¿Se guardó el pedido correctamente?
SELECT * FROM pedidos ORDER BY created_at DESC LIMIT 1;

-- 2. ¿Se descontó el inventario automáticamente?
-- (Verifica que 'carne molida' y 'pan' tengan menos cantidad que el inicio)
SELECT ingrediente, cantidad, unidad FROM inventario 
WHERE ingrediente IN ('carne molida', 'pan de hamburguesa');

-- 3. ¿Se generó la orden para la cocina?
SELECT * FROM cola_impresion WHERE destino = 'COCINA' ORDER BY created_at DESC;
```

---

## ⚪ Paso 5: Experiencia Visual (Frontend)
Abre los archivos HTML en tu navegador para simular la operación:
1. **POS ([pos_demo.html](file:///c:/Users/DAVIS/Downloads/files%20(2)/pos_demo.html)):** Haz clic en los combos para ver cómo se arma la orden y simula el pago.
2. **Cocina ([kds_demo.html](file:///c:/Users/DAVIS/Downloads/files%20(2)/kds_demo.html)):** Verás los pedidos activos. Haz clic en "EMPEZAR" y luego en "COMPLETAR".
3. **Admin ([admin_dashboard_demo.html](file:///c:/Users/DAVIS/Downloads/files%20(2)/admin_dashboard_demo.html)):** Revisa las alertas de stock bajo y las ventas del día.
