# 🚀 Guía de Operación: Cómo Correr tu Sistema en una PC

Para interactuar visualmente con el sistema que diseñamos basado en tu imagen, sigue esta guía. El sistema está compuesto por tres "apps web" que corren en cualquier navegador (Chrome, Edge, etc.).

---

## 🖥️ 1. Configuración de Pantallas (Idealmente)
Si tienes una PC con varios monitores o tablets, así es como se vería en tu local:

| Monitor / Dispositivo | App que debe estar abierta | Función |
| :--- | :--- | :--- |
| **Monitor de Caja** | [pos_demo.html](file:///c:/Users/DAVIS/Downloads/files%20(2)/pos_demo.html) | El cajero registra pedidos presenciales. |
| **Tablet en Cocina** | [kds_demo.html](file:///c:/Users/DAVIS/Downloads/files%20(2)/kds_demo.html) | Los cocineros ven los pedidos y los marcan como listos. |
| **PC de Oficina** | [admin_dashboard_demo.html](file:///c:/Users/DAVIS/Downloads/files%20(2)/admin_dashboard_demo.html) | El dueño ve las ventas y las alertas de inventario. |

---

## 🛡️ 1.1. Modo Kiosco (Terminal Profesional)
Si vas a montar una pantalla táctil para autoservicio o para tu cajero, **no quieres que se vean las barras del navegador** (pestañas, URL, botones de cerrar).

He creado un lanzador especial: [lanzar_kiosco.ps1](file:///c:/Users/DAVIS/Downloads/files%20(2)/lanzar_kiosco.ps1).

**Ventajas del Modo Kiosco:**
- **Pantalla Completa Total:** Oculta Windows y el navegador por completo.
- **Sin Errores:** Evita que el cajero o cliente accidentalmente cierre la app o navegue a otro sitio.
- **Interacción Táctil:** Desactiva gestos de zoom y navegación (adelante/atrás) que pueden molestar.

> **⚠️ NOTA:** Una vez en modo kiosco, para salir debes presionar la combinación de teclas **`ALT + F4`**.

---

## 🖨️ 1.2. Impresión de Tickets (Caja y Cocina)
El sistema está preparado para enviar órdenes a impresoras térmicas de 58mm o 80mm.

**Cómo funciona:**
1. **Acción de Pago:** Al presionar "PAGAR" en el POS, se genera un ticket digital.
2. **Cola de Impresión:** n8n recibe la orden y la guarda en la tabla `cola_impresion`.
3. **Hardware:** Una pequeña aplicación (script) en la PC conectada a la impresora física detecta la nueva orden y la imprime.

**Formato del Ticket:**
- Encabezado con logo y fecha.
- Detalle de productos con cantidades.
- Total y método de pago.
- Código QR para seguimiento del pedido.

---

## 🖱️ 2. Cómo interactuar con cada una

### **🛒 El POS (Caja / Kiosco)**
- **Acción:** Abre [pos_demo.html](file:///c:/Users/DAVIS/Downloads/files%20(2)/pos_demo.html).
- **Interacción:** Haz clic en los iconos de hamburguesas o papas. Verás cómo se agregan al carrito a la derecha. Puedes limpiar la orden o simular un pago con Yappy.

### **👨‍🍳 El KDS (Cocina)**
- **Acción:** Abre [kds_demo.html](file:///c:/Users/DAVIS/Downloads/files%20(2)/kds_demo.html).
- **Interacción:** Los pedidos aparecerán aquí automáticamente (vía n8n). El cocinero hace clic en **"EMPEZAR"** cuando inicia y **"COMPLETAR"** cuando el plato sale. El cronómetro te dice cuánto tiempo lleva esperando el cliente.

### **📊 El Dashboard (Administración)**
- **Acción:** Abre [admin_dashboard_demo.html](file:///c:/Users/DAVIS/Downloads/files%20(2)/admin_dashboard_demo.html).
- **Interacción:** Aquí no haces clic en botones de proceso, sino que **observas datos**. Si el stock baja de cierto nivel, verás la alerta roja y el botón para generar la orden de compra al proveedor.

---

## ⚡ 3. Cómo correrlo todo ahora mismo
He creado un script para que abras todo de un solo golpe y veas la experiencia completa:

1. Busca el archivo [abrir_sistema.ps1](file:///c:/Users/DAVIS/Downloads/files%20(2)/abrir_sistema.ps1).
2. Haz clic derecho y selecciona **"Ejecutar con PowerShell"**.
3. Se abrirán 3 pestañas en tu navegador con todo el sistema listo para que juegues con él.

---

## 🧠 4. ¿Qué pasa "por detrás"?
Mientras tú ves estas pantallas, el archivo [flujo_maestro_n8n.json](file:///c:/Users/DAVIS/Downloads/files%20(2)/flujo_maestro_n8n.json) está corriendo en segundo plano:
1. Recibe el pedido de la Caja o de WhatsApp.
2. Actualiza los números en el Dashboard de Admin.
3. Envía la orden a la pantalla de Cocina.
4. Manda el mensaje de confirmación al cliente.
