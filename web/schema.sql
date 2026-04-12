-- ============================================================
-- BASE DE DATOS: RESTAURANTE AUTOMATIZADO
-- Motor: PostgreSQL 14+
-- Instrucciones: Ejecuta este script completo en tu base de datos
-- para crear todas las tablas, índices y datos iniciales.
-- ============================================================

-- -----------------------------------------------
-- EXTENSIONES
-- -----------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------
-- TABLA: proveedores
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS proveedores (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  nombre      VARCHAR(120) NOT NULL,
  telefono    VARCHAR(30),
  email       VARCHAR(120),
  direccion   TEXT,
  activo      BOOLEAN DEFAULT true,
  created_at  TIMESTAMP DEFAULT NOW(),
  updated_at  TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE proveedores IS 'Empresas o personas que abastecen el restaurante';

-- -----------------------------------------------
-- TABLA: categorias_menu
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS categorias_menu (
  id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  nombre   VARCHAR(80) NOT NULL,
  orden    INT DEFAULT 0
);

INSERT INTO categorias_menu (nombre, orden) VALUES
  ('Combos', 1),
  ('Hamburguesas', 2),
  ('Pollo', 3),
  ('Acompañantes', 4),
  ('Bebidas', 5),
  ('Postres', 6)
ON CONFLICT DO NOTHING;

-- -----------------------------------------------
-- TABLA: productos_menu
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS productos_menu (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  nombre        VARCHAR(120) NOT NULL,
  descripcion   TEXT,
  precio        NUMERIC(8,2) NOT NULL,
  categoria_id  UUID REFERENCES categorias_menu(id),
  disponible    BOOLEAN DEFAULT true,
  imagen_url    VARCHAR(255),
  created_at    TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE productos_menu IS 'Productos que aparecen en el menú del restaurante';

-- Datos iniciales de ejemplo
INSERT INTO productos_menu (nombre, descripcion, precio, categoria_id) VALUES
  ('Combo Clásico', 'Hamburguesa clásica + papas medianas + refresco', 5.50,
    (SELECT id FROM categorias_menu WHERE nombre = 'Combos')),
  ('Combo Doble', 'Hamburguesa doble + papas medianas + refresco', 7.50,
    (SELECT id FROM categorias_menu WHERE nombre = 'Combos')),
  ('Combo Pollo', 'Sándwich de pollo + papas medianas + refresco', 6.00,
    (SELECT id FROM categorias_menu WHERE nombre = 'Combos')),
  ('Papas fritas', 'Papas fritas medianas crujientes', 1.50,
    (SELECT id FROM categorias_menu WHERE nombre = 'Acompañantes')),
  ('Refresco', 'Lata 355ml, variedad disponible', 1.00,
    (SELECT id FROM categorias_menu WHERE nombre = 'Bebidas')),
  ('Agua botella', 'Agua purificada 500ml', 0.75,
    (SELECT id FROM categorias_menu WHERE nombre = 'Bebidas'))
ON CONFLICT DO NOTHING;

-- -----------------------------------------------
-- TABLA: ingredientes (inventario)
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS inventario (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  ingrediente     VARCHAR(120) NOT NULL UNIQUE,
  cantidad        NUMERIC(10,3) NOT NULL DEFAULT 0,
  unidad          VARCHAR(20) NOT NULL,  -- kg, litro, unidad, gramo, etc.
  stock_minimo    NUMERIC(10,3) NOT NULL DEFAULT 0,
  costo_unitario  NUMERIC(8,4),          -- costo por unidad para calcular costo de plato
  proveedor_id    UUID REFERENCES proveedores(id),
  activo          BOOLEAN DEFAULT true,
  updated_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE inventario IS 'Stock de ingredientes en tiempo real';

-- Ingredientes iniciales de ejemplo
INSERT INTO inventario (ingrediente, cantidad, unidad, stock_minimo, costo_unitario) VALUES
  ('carne molida',    10.0,  'kg',      5.0,   6.50),
  ('pan de hamburguesa', 100, 'unidad', 40,    0.25),
  ('pollo filete',    8.0,   'kg',      4.0,   5.00),
  ('papa cruda',      15.0,  'kg',      6.0,   0.80),
  ('aceite freir',    5.0,   'litro',   2.0,   2.50),
  ('lechuga',         3.0,   'kg',      1.5,   1.50),
  ('tomate',          4.0,   'kg',      2.0,   1.20),
  ('queso tajada',    2.0,   'kg',      1.0,   8.00),
  ('refresco lata',   48,    'unidad',  24,    0.40),
  ('agua botella',    24,    'unidad',  12,    0.35)
ON CONFLICT DO NOTHING;

-- -----------------------------------------------
-- TABLA: recetas (ingredientes por producto)
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS recetas (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  producto_id     UUID REFERENCES productos_menu(id) NOT NULL,
  ingrediente_id  UUID REFERENCES inventario(id) NOT NULL,
  cantidad        NUMERIC(10,4) NOT NULL,  -- cantidad que usa este producto
  UNIQUE(producto_id, ingrediente_id)
);

COMMENT ON TABLE recetas IS 'Define cuánto de cada ingrediente usa cada producto del menú. Se descuenta automáticamente al vender.';

-- -----------------------------------------------
-- TABLA: clientes
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  telefono    VARCHAR(30) UNIQUE NOT NULL,
  nombre      VARCHAR(120),
  pedidos_count INT DEFAULT 0,
  ultimo_pedido TIMESTAMP,
  canal_registro VARCHAR(30) DEFAULT 'WHATSAPP',
  created_at  TIMESTAMP DEFAULT NOW()
);

-- -----------------------------------------------
-- TABLA: pedidos
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS pedidos (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  numero           VARCHAR(30) UNIQUE NOT NULL,  -- WA-123456, POS-789, etc.
  cliente_telefono VARCHAR(30),
  cliente_nombre   VARCHAR(120),
  items            JSONB NOT NULL,               -- [{nombre, precio, cantidad}]
  subtotal         NUMERIC(8,2),
  descuento        NUMERIC(8,2) DEFAULT 0,
  total            NUMERIC(8,2) NOT NULL,
  estado           VARCHAR(30) DEFAULT 'RECIBIDO',
  -- Estados: RECIBIDO → EN_PREPARACION → LISTO → ENTREGADO → CANCELADO
  canal            VARCHAR(30) NOT NULL,         -- WHATSAPP, POS, KIOSCO, APP
  metodo_pago      VARCHAR(30),                  -- EFECTIVO, TARJETA, YAPPY
  pagado           BOOLEAN DEFAULT false,
  notas            TEXT,
  created_at       TIMESTAMP DEFAULT NOW(),
  updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos(estado);
CREATE INDEX IF NOT EXISTS idx_pedidos_fecha  ON pedidos(created_at);
CREATE INDEX IF NOT EXISTS idx_pedidos_canal  ON pedidos(canal);

COMMENT ON TABLE pedidos IS 'Todos los pedidos del restaurante de todos los canales';

-- -----------------------------------------------
-- TABLA: movimientos_inventario (auditoría)
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS movimientos_inventario (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  ingrediente_id  UUID REFERENCES inventario(id),
  tipo            VARCHAR(20) NOT NULL, -- ENTRADA, SALIDA, AJUSTE, MERMA
  cantidad        NUMERIC(10,3) NOT NULL,
  cantidad_antes  NUMERIC(10,3),
  cantidad_despues NUMERIC(10,3),
  pedido_id       UUID REFERENCES pedidos(id),
  referencia      VARCHAR(120),         -- factura proveedor, etc.
  usuario         VARCHAR(80),
  notas           TEXT,
  created_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE movimientos_inventario IS 'Historial completo de cada cambio en el inventario';

-- -----------------------------------------------
-- TABLA: ordenes_compra
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS ordenes_compra (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  proveedor    VARCHAR(120),
  proveedor_id UUID REFERENCES proveedores(id),
  items        JSONB NOT NULL,   -- [{ingrediente, cantidadSugerida, unidad}]
  estado       VARCHAR(30) DEFAULT 'PENDIENTE',
  -- Estados: PENDIENTE → ENVIADA → RECIBIDA → CANCELADA
  total_estimado NUMERIC(8,2),
  notas        TEXT,
  created_at   TIMESTAMP DEFAULT NOW(),
  updated_at   TIMESTAMP DEFAULT NOW()
);

-- -----------------------------------------------
-- TABLA: sesiones_caja (turnos)
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS sesiones_caja (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  cajero          VARCHAR(120) NOT NULL,
  apertura        TIMESTAMP DEFAULT NOW(),
  cierre          TIMESTAMP,
  monto_apertura  NUMERIC(8,2) DEFAULT 0,
  monto_cierre    NUMERIC(8,2),
  ventas_total    NUMERIC(10,2),
  diferencia      NUMERIC(8,2),
  estado          VARCHAR(20) DEFAULT 'ABIERTA'  -- ABIERTA, CERRADA
);

-- -----------------------------------------------
-- TABLA: comprobantes (Facturación)
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS comprobantes (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  pedido_id    UUID REFERENCES pedidos(id) NOT NULL,
  tipo         VARCHAR(20) DEFAULT 'FACTURA', -- FACTURA, RECIBO
  numero       VARCHAR(50) UNIQUE NOT NULL,
  datos_emisor JSONB,
  datos_receptor JSONB,
  total        NUMERIC(8,2) NOT NULL,
  pdf_url      VARCHAR(255),
  created_at   TIMESTAMP DEFAULT NOW()
);

-- -----------------------------------------------
-- TABLA: cola_impresion
-- -----------------------------------------------
CREATE TABLE IF NOT EXISTS cola_impresion (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  pedido_id   UUID REFERENCES pedidos(id),
  destino     VARCHAR(30) NOT NULL, -- COCINA, BARRA, CAJA
  contenido   TEXT NOT NULL,
  estado      VARCHAR(20) DEFAULT 'PENDIENTE', -- PENDIENTE, IMPRESO, ERROR
  reintentos  INT DEFAULT 0,
  created_at  TIMESTAMP DEFAULT NOW()
);

-- -----------------------------------------------
-- FUNCIÓN: descuento automático de inventario al vender
-- -----------------------------------------------
CREATE OR REPLACE FUNCTION descontar_inventario_por_pedido(p_pedido_id UUID)
RETURNS void AS $$
DECLARE
  v_item JSONB;
  v_producto_id UUID;
  v_receta RECORD;
BEGIN
  -- Para cada item del pedido
  FOR v_item IN
    SELECT jsonb_array_elements(items) FROM pedidos WHERE id = p_pedido_id
  LOOP
    v_producto_id := (v_item->>'producto_id')::UUID;

    -- Descontar cada ingrediente según la receta
    FOR v_receta IN
      SELECT r.ingrediente_id, r.cantidad, i.ingrediente
      FROM recetas r
      JOIN inventario i ON r.ingrediente_id = i.id
      WHERE r.producto_id = v_producto_id
    LOOP
      UPDATE inventario
      SET cantidad = cantidad - v_receta.cantidad,
          updated_at = NOW()
      WHERE id = v_receta.ingrediente_id;

      -- Registrar movimiento
      INSERT INTO movimientos_inventario
        (ingrediente_id, tipo, cantidad, pedido_id, referencia)
      VALUES
        (v_receta.ingrediente_id, 'SALIDA', v_receta.cantidad, p_pedido_id, 'Venta automática');
    END LOOP;
  END LOOP;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------
-- VISTA: resumen de ventas del día
-- -----------------------------------------------
CREATE OR REPLACE VIEW ventas_hoy AS
SELECT
  COUNT(*) AS total_pedidos,
  SUM(total) AS ingresos_totales,
  AVG(total) AS ticket_promedio,
  canal,
  COUNT(*) FILTER (WHERE metodo_pago = 'EFECTIVO') AS pagos_efectivo,
  COUNT(*) FILTER (WHERE metodo_pago = 'TARJETA') AS pagos_tarjeta,
  COUNT(*) FILTER (WHERE metodo_pago = 'YAPPY') AS pagos_yappy
FROM pedidos
WHERE created_at >= CURRENT_DATE
  AND estado != 'CANCELADO'
GROUP BY canal;

-- -----------------------------------------------
-- VISTA: alertas de stock
-- -----------------------------------------------
CREATE OR REPLACE VIEW alertas_stock AS
SELECT
  i.ingrediente,
  i.cantidad,
  i.unidad,
  i.stock_minimo,
  ROUND((i.cantidad / NULLIF(i.stock_minimo, 0) * 100)::numeric, 0) AS pct_disponible,
  CASE
    WHEN i.cantidad = 0 THEN 'SIN STOCK'
    WHEN i.cantidad < i.stock_minimo * 0.5 THEN 'CRITICO'
    WHEN i.cantidad <= i.stock_minimo THEN 'BAJO'
    ELSE 'OK'
  END AS estado,
  p.nombre AS proveedor,
  p.telefono AS tel_proveedor
FROM inventario i
LEFT JOIN proveedores p ON i.proveedor_id = p.id
WHERE i.activo = true
ORDER BY pct_disponible ASC;
