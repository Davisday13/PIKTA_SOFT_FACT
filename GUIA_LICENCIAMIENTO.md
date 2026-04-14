# GUÍA DE LICENCIAMIENTO - SISTEMA POS PIK'TA

## DESCRIPCIÓN GENERAL

El sistema incluye un módulo de licenciamiento que permite:
- Período de prueba inicial (demo) de 30 días
- Activación por clave de licencia
- Diferentes duraciones de licencia (1 año, 3 años, 5 años, perpetua)

---

## TIPOS DE LICENCIA DISPONIBLES

| Tipo | Clave | Duración | Descripción |
|------|-------|----------|-------------|
| **PRO** | PIKTA-2026-PRO-A1B2C3D4 | 365 días (1 año) | Licencia profesional anual |
| **BIZ** | PIKTA-2026-BIZ-E5F6G7H8 | 1095 días (3 años) | Licencia de negocios |
| **ENT** | PIKTA-2026-ENT-I9J0K1L2 | 1825 días (5 años) | Licencia empresarial |
| **ULT** | PIKTA-2026-ULT-M3N4O5P6 | Indefinida | Licencia perpetua |

---

## CONFIGURACIÓN EN CÓDIGO

### Archivo: `main_app.py` (líneas 216-227)

```python
LICENSE_KEY_PRO = "PIKTA-2026-PRO-A1B2C3D4"
LICENSE_KEY_BIZ = "PIKTA-2026-BIZ-E5F6G7H8"
LICENSE_KEY_ENT = "PIKTA-2026-ENT-I9J0K1L2"
LICENSE_KEY_ULT = "PIKTA-2026-ULT-M3N4O5P6"
TRIAL_DAYS = 30

LICENSE_TYPES = {
    'PRO': {'name': 'Anual', 'days': 365, 'key': LICENSE_KEY_PRO},
    'BIZ': {'name': '3 Años', 'days': 1095, 'key': LICENSE_KEY_BIZ},
    'ENT': {'name': '5 Años', 'days': 1825, 'key': LICENSE_KEY_ENT},
    'ULT': {'name': 'Perpetua', 'days': None, 'key': LICENSE_KEY_ULT},
}
```

### Parámetros modificables:

| Parámetro | Descripción | Valor por defecto |
|------------|-------------|-------------------|
| `TRIAL_DAYS` | Días del período de prueba/demo | 30 días |
| `LICENSE_KEY_*` | Claves de cada tipo de licencia | (ver arriba) |

---

## CÓMO ACTIVAR/DESACTIVAR LICENCIAS

### Método 1: Desde la Interfaz Gráfica (Recomendado)

1. **Al iniciar el sistema** → Aparece ventana de licencia
2. **Si está en período de prueba:** Muestra los días restantes y tipos de licencia disponibles
3. **Si está bloqueado (demo expirado):** Debe ingresar la clave para continuar
4. **Panel de Administración → Pestaña "Seguridad":**
   - Ver estado actual de la licencia (tipo y días restantes)
   - Botón "🔐 Activar Sistema" para cambiar/actualizar licencia

### Método 2: Directamente en la Base de Datos

1. Abrir `PIKTA_SOFT.db` con SQLite Browser, DBeaver, o línea de comandos
2. Consultar/editar la tabla `sistema_config`:

```sql
-- Ver estado actual de licencias
SELECT * FROM sistema_config WHERE clave IN ('install_date', 'activated', 'license_type', 'license_expires');

-- ACTIVAR manualmente el sistema (NO especifica tipo ni expiración)
UPDATE sistema_config SET valor = '1' WHERE clave = 'activated';

-- ACTIVAR con tipo y fecha de expiración
UPDATE sistema_config SET valor = '1' WHERE clave = 'activated';
UPDATE sistema_config SET valor = 'PRO' WHERE clave = 'license_type';
UPDATE sistema_config SET valor = '2027-04-14T00:00:00.000000' WHERE clave = 'license_expires';

-- DESACTIVAR (vuelve a período de prueba)
UPDATE sistema_config SET valor = '0' WHERE clave = 'activated';
UPDATE sistema_config SET valor = '' WHERE clave = 'license_type';
UPDATE sistema_config SET valor = '' WHERE clave = 'license_expires';

-- REINICIAR período de prueba (cambiar fecha de instalación)
UPDATE sistema_config SET valor = '2026-04-14T00:00:00.000000' WHERE clave = 'install_date';
```

### Método 3: Por Código Python

```python
# En main_app.py
from main_app import verify_license, activate_license, LicenseWindow

# Verificar estado actual
info = verify_license()
print(f"Estado: {info['status']}")
print(f"Días restantes: {info['days_left']}")
print(f"Tipo de licencia: {info['type']}")

# Activar con clave
# activate_license("PIKTA-2026-PRO-A1B2C3D4", db_instance)
```

---

## ESTRUCTURA DE CLAVES DE LICENCIA

### Formato:
```
PIKTA-{AÑO}-{TIPO}-{HASH}
```

### Componentes:
- `PIKTA` - Prefijo fijo del sistema
- `{AÑO}` - Año de emisión (2026, 2027, etc.)
- `{TIPO}` - Tipo de licencia:
  - `PRO` - Licencia profesional (anual)
  - `BIZ` - Licencia de negocios (3 años)
  - `ENT` - Licencia empresarial (5 años)
  - `ULT` - Licencia perpetua
- `{HASH}` - Código de seguridad (8 caracteres)

### Claves actualmente configuradas:

| Tipo | Clave Completa |
|------|----------------|
| Anual (PRO) | `PIKTA-2026-PRO-A1B2C3D4` |
| 3 Años (BIZ) | `PIKTA-2026-BIZ-E5F6G7H8` |
| 5 Años (ENT) | `PIKTA-2026-ENT-I9J0K1L2` |
| Perpetua (ULT) | `PIKTA-2026-ULT-M3N4O5P6` |

---

## ESCENARIOS DE USO

### Escenario 1: Demo para nuevo cliente
1. Instalar sistema en máquina del cliente
2. Período de prueba inicia automáticamente (30 días)
3. Durante demo, todas las funcionalidades están activas
4. Al terminar demo, negociar tipo de licencia a comprar

### Escenario 2: Activación para cliente (ejemplo: 1 año)
1. Cliente acepta licencia PRO (anual)
2. Proporcionar clave: `PIKTA-2026-PRO-A1B2C3D4`
3. Cliente ingresa clave en ventana de activación
4. Sistema queda activado por 365 días

### Escenario 3: Activación licencia perpetua
1. Cliente compra licencia perpetua
2. Proporcionar clave: `PIKTA-2026-ULT-M3N4O5P6`
3. Sistema queda activado SIN fecha de expiración

### Escenario 4: Renovación de licencia
1. Aproximarse fecha de vencimiento (30 días antes, sistema lo advierte)
2. Generar nueva clave del tipo correspondiente
3. Cliente activa con nueva clave
4. Nueva fecha de expiración se calcula desde la fecha de activación

### Escenario 5: Cambiar tipo de licencia
1. Cliente quiere cambiar de PRO a BIZ (1 año → 3 años)
2. Ingresar nueva clave: `PIKTA-2026-BIZ-E5F6G7H8`
3. Sistema actualiza tipo y nueva fecha de expiración

### Escenario 6: Desactivar temporalmente
1. Cliente desea pausar uso
2. En base de datos: `UPDATE sistema_config SET valor = '0' WHERE clave = 'activated'`
3. Sistema volverá a mostrar ventana de licencia
4. Para reactivar, usar clave original (la fecha de expiración se recalcula)

---

## FLUJO DEL SISTEMA DE LICENCIAS

```
┌─────────────────────────────────────────────────────────────┐
│                    INICIO DEL SISTEMA                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ ¿DB existe?           │
              └───────────┬───────────┘
                    SÍ    │    NO
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────┐           ┌─────────────────┐
│ Leer estado de  │           │ Crear DB con    │
│ licencia en BD  │           │ status='trial'  │
└────────┬────────┘           └────────┬────────┘
         │                             │
         ▼                             ▼
┌─────────────────────────────────────────────────┐
│         verify_license()                        │
│  ┌─────────────────────────────────────────┐   │
│  │ 'trial' → Período de prueba activo      │   │
│  │ 'expired' → Demo terminado, bloqueado   │   │
│  │ 'activated' → Licencia válida          │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │  TRIAL   │ │ EXPIRED  │ │ACTIVATED │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │             │            │
        ▼             ▼            ▼
   Muestra       Bloquea      Muestra
   ventana       acceso y     "Sistema
   con días      pide clave   Activado"
   restantes     para         y permite
   y botón       activar      continuar
   "Activar"
```

---

## UBICACIÓN DE ARCHIVOS RELACIONADOS

| Archivo | Descripción |
|---------|-------------|
| `PIKTA_SOFT.db` | Base de datos con configuración de licencia |
| `main_app.py` | Código fuente con lógica de licenciamiento |
| `Imagenes/pikta2.png` | Logo mostrado en ventana de licencia |
| `GUIA_LICENCIAMIENTO.md` | Este documento |

---

## TABLA `sistema_config` - Campos de Licencia

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `install_date` | TEXT | Fecha ISO de primera instalación | `2026-04-14T00:00:00.000000` |
| `activated` | TEXT | '0' = no activado, '1' = activado | `1` |
| `license_type` | TEXT | Tipo de licencia (PRO/BIZ/ENT/ULT) | `PRO` |
| `license_expires` | TEXT | Fecha ISO de expiración (vacío si perpetua) | `2027-04-14T00:00:00.000000` |

---

## NOTAS IMPORTANTES

1. **No eliminar `PIKTA_SOFT.db`** - Contiene toda la información de activación
2. **Respaldar base de datos** antes de modificar configuraciones manualmente
3. **Las claves son case-insensitive** - Se validan en mayúsculas automáticamente
4. **El sistema funciona offline** - No requiere conexión a internet
5. **La fecha de instalación NO se reinicia** al cambiar licencias
6. **Perpetua (ULT)** tiene `license_expires` vacío (`''`)

---

## MODIFICAR CLAVES DE LICENCIA

Para cambiar las claves (ej: después de renovar con cliente):

1. Abrir `main_app.py`
2. Buscar líneas 216-220:
```python
LICENSE_KEY_PRO = "PIKTA-2026-PRO-A1B2C3D4"
LICENSE_KEY_BIZ = "PIKTA-2026-BIZ-E5F6G7H8"
LICENSE_KEY_ENT = "PIKTA-2026-ENT-I9J0K1L2"
LICENSE_KEY_ULT = "PIKTA-2026-ULT-M3N4O5P6"
```
3. Reemplazar las claves por las nuevas proporcionadas

---

## MODIFICAR PERÍODO DE PRUEBA

Para cambiar los días de demo (ej: de 30 a 7 días para evaluación rápida):

1. Abrir `main_app.py`
2. Buscar línea 226:
```python
TRIAL_DAYS = 30
```
3. Cambiar el valor al deseado

---

## SOPORTE TÉCNICO

Para asistencia técnica:
- Email: soporte@yafasolutions.com
- Teléfono: [número de contacto]
- Horario: Lunes a Viernes 8:00 AM - 5:00 PM

---

*Documento creado: Abril 2026*
*Última actualización: Abril 2026*
*Sistema POS PIK'TA - Desarrollado por YAFA SOLUTIONS*
