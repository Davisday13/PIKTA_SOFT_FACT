# 🏗️ Arquitectura del Sistema: Restaurante Automatizado

Basado en el flujo operacional solicitado, este documento define la estructura técnica para construir el sistema de restaurante de punta a punta.

---

## 🟢 1. Canales de Pedido (Entradas)
Todos los canales convergen en un único punto de entrada digital (n8n).

| Canal | Descripción | Tecnología Recomendada |
| :--- | :--- | :--- |
| **WhatsApp** | Bot automático para pedidos por chat. | n8n + WhatsApp Business API (Meta) |
| **Kiosco en local** | Pantalla táctil de autoservicio. | Next.js (Web App) en modo pantalla completa |
| **App / Web** | Pedido online desde cualquier dispositivo. | Next.js (PWA) con React |
| **Caja / POS** | Registro presencial de pedidos. | Next.js (Dashboard de Cajero) |

---

## 🟣 2. n8n — Motor de Automatización (Cerebro)
El núcleo que orquestra la lógica de negocio y distribuye la información.

- **Receptor Universal:** Webhooks que reciben datos de todos los canales.
- **Validador de Reglas:** Verifica stock, disponibilidad de productos y métodos de pago.
- **Distribuidor Inteligente:** Envía la información a los tres sistemas operativos en paralelo.

---

## 🟠 3. Sistemas Operativos (Procesamiento)

### A. POS + Facturación
- Gestión de órdenes activas.
- Registro de pagos y emisión de comprobantes digitales.
- Integración con pasarelas de pago.

### B. Cocina (KDS)
- Pantalla interactiva para cocineros.
- Gestión de tiempos de preparación.
- Notificación automática al terminar ("Listo para entrega").

### C. Inventario
- Control de stock automático (descuento por receta).
- Alertas de stock bajo enviadas proactivamente al administrador.
- Registro de mermas y ajustes.

---

## ⚪ 4. Salidas Automatizadas (Resultados)

- **Confirmación:** Mensaje automático por WhatsApp al cliente confirmando su pedido y tiempo estimado.
- **Ticket / Comanda:** Envío de orden a impresora térmica en cocina y barra vía ESC/POS.
- **Reportes:** Dashboard en tiempo real con ventas, métricas de rendimiento y tendencias.
- **Pagos:** Generación de QR dinámico para Yappy o enlaces de pago de tarjeta.

---

## 🛠️ Stack de Implementación Sugerido
- **Frontend Unified:** React / Next.js para todos los dashboards (Admin, KDS, POS, Kiosco).
- **Base de Datos:** PostgreSQL para persistencia de datos relacionales.
- **Automatización:** n8n (Instalado vía Docker para mayor control).
- **Tiempo Real:** Supabase Realtime para la comunicación entre n8n y las pantallas de cocina.
- **Impresión:** Librerías `escpos` en Node.js o PrintNode para impresión remota.
