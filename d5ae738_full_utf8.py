"""
main_app.py - Interfaz de escritorio estilo 'web' (Tkinter)

Este archivo contiene una versi├│n de escritorio del panel del
restaurante (POS, KDS, Admin) adaptada desde la carpeta `web/`.

Componentes principales:
- `DatabaseManager`: Inicializa y gestiona la base de datos SQLite y migraciones.
- `LoginWindow`: Ventana modal para inicio de sesi├│n con control de roles.
- `App`: Clase principal de la aplicaci├│n que gestiona el contenedor de pesta├▒as (Notebook).
- `POSFrame`: Interfaz de Punto de Venta (Caja).
- `KDSFrame`: Monitor de Cocina para gesti├│n de pedidos.
- `AdminFrame`: Panel administrativo para inventario y usuarios.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import PRIMARY, SUCCESS, DANGER, WARNING, INFO, LIGHT, DARK
import sqlite3
import json
import os
import webbrowser
import threading
import multiprocessing
try:
    import webview
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False
from datetime import datetime, timedelta
import logging
import sys
import tempfile
import hashlib
import secrets
import winsound
import shutil
try:
    import win32print
    import win32api
    WIN32_PRINT_AVAILABLE = True
except ImportError:
    WIN32_PRINT_AVAILABLE = False

# =============================================================================
# FUNCIONES DE SONIDO Y NOTIFICACI├ôN
# =============================================================================

def play_sound_error():
    """Sonido para errores del sistema."""
    try:
        winsound.MessageBeep(winsound.MB_ICONHAND)
    except:
        pass

def play_sound_new_order():
    """Sonido suave para nuevos pedidos entrantes."""
    try:
        winsound.Beep(800, 300)
        winsound.Beep(1000, 300)
    except:
        pass

def play_sound_order_ready():
    """Sonido fuerte de campanas para cuando un pedido est├í listo."""
    try:
        # Simulaci├│n de campana con frecuencias altas y decrecientes
        for _ in range(2):
            winsound.Beep(2500, 150)
            winsound.Beep(2000, 150)
            winsound.Beep(1500, 150)
            time.sleep(0.1)
    except:
        pass

# =============================================================================
# FUNCIONES DE IMPRESI├ôN Y HARDWARE
# =============================================================================

def find_pos_printer():
    """Busca autom├íticamente una impresora t├®rmica USB conectada."""
    if not WIN32_PRINT_AVAILABLE: return None
    try:
        # 1. Intentar con la impresora por defecto
        default = win32print.GetDefaultPrinter()
        # 2. Si no es obvia, buscar una que diga POS, Thermal o 80
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        for flags, description, name, comment in printers:
            n = name.upper()
            if "POS" in n or "THERMAL" in n or "80MM" in n or "58MM" in n or "XP-80" in n:
                return name
        return default
    except:
        return None

# =============================================================================
# FUNCIONES DE SEGURIDAD (ENCRIPTACI├ôN)
# =============================================================================

def hash_password(password):
    """Genera un hash seguro para la contrase├▒a usando PBKDF2."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{hash_obj.hex()}"

def verify_password(stored_password, provided_password):
    """Verifica si la contrase├▒a proporcionada coincide con el hash guardado."""
    if not stored_password or ':' not in stored_password:
        return False
    try:
        salt, hash_value = stored_password.split(':')
        hash_obj = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt.encode(), 100000)
        return hash_obj.hex() == hash_value
    except Exception:
        return False

# =============================================================================
# GESTOR DE SESIONES
# =============================================================================

class SessionManager:
    """Gestiona las sesiones activas de los usuarios y su tiempo de expiraci├│n."""
    def __init__(self, timeout_seconds=1800): # 30 minutos por defecto
        self.sessions = {}
        self.session_timeout = timeout_seconds
    
    def create_session(self, user_data):
        """Crea una nueva sesi├│n y devuelve el ID ├║nico."""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            'user': user_data,
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        return session_id
    
    def validate_session(self, session_id):
        """Verifica si la sesi├│n es v├ílida y no ha expirado."""
        if session_id not in self.sessions:
            return False
        session = self.sessions[session_id]
        # Verificar expiraci├│n por inactividad
        if (datetime.now() - session['last_activity']).total_seconds() > self.session_timeout:
            del self.sessions[session_id]
            return False
        # Actualizar ├║ltima actividad
        session['last_activity'] = datetime.now()
        return True

    def get_user(self, session_id):
        """Retorna los datos del usuario de una sesi├│n activa."""
        if self.validate_session(session_id):
            return self.sessions[session_id]['user']
        return None

    def close_session(self, session_id):
        """Elimina una sesi├│n activa."""
        if session_id in self.sessions:
            del self.sessions[session_id]

# Instancia global del gestor de sesiones
session_manager = SessionManager()

# =============================================================================
# CONFIGURACI├ôN DE REGISTRO DE ERRORES (LOGGING)
# =============================================================================
# Se registran todos los errores en 'error_log.txt' para facilitar el diagn├│stico.
logging.basicConfig(filename='error_log.txt', filemode='a', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# Manejador global de excepciones: asegura que errores no capturados se guarden en el archivo log.
def _log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error('Excepci├│n no capturada', exc_info=(exc_type, exc_value, exc_traceback))
    play_sound_error()

sys.excepthook = _log_uncaught_exceptions

# Manejador espec├¡fico para errores en los callbacks de Tkinter.
def _tk_report_callback_exception(self, exc, val, tb):
    logging.error('Excepci├│n en callback de Tkinter', exc_info=(exc, val, tb))
    play_sound_error()

tk.Tk.report_callback_exception = _tk_report_callback_exception

# =============================================================================
# CONFIGURACI├ôN VISUAL Y CONSTANTES
# =============================================================================
DB_NAME = "PIk'TADB.db"  # Nombre del archivo de base de datos SQLite
BG = '#2b3e50'          # Color de fondo principal (Azul Petr├│leo Superhero)
PANEL = '#4e5d6c'       # Color de fondo para paneles y tarjetas
FG = '#ebebeb'          # Color de texto principal (blanco gris├íceo)
ACCENT = '#df691a'      # Color de acento (Naranja Superhero)
INFO = '#5bc0de'        # Azul claro para informaci├│n
OK = '#5cb85c'          # Color para acciones exitosas (verde)
WARN = '#f0ad4e'        # Color para advertencias (naranja)
ERR = '#d9534f'         # Color para errores cr├¡ticos (rojo)
FONT_SIZE_L = 16        # Tama├▒o de fuente grande
FONT_SIZE_XL = 22       # Tama├▒o de fuente extra grande
FONT_SIZE_NORMAL = 12   # Tama├▒o de fuente normal

# Intentar importar Pillow para soporte avanzado de im├ígenes (JPEG, redimensionamiento)
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

def load_image(path, size=None):
    """
    Carga una imagen desde el disco.
    Si Pillow est├í instalado, permite cambiar el tama├▒o (redimensionar).
    Si no, usa el PhotoImage b├ísico de Tkinter (solo PNG/GIF).
    """
    if not os.path.exists(path):
        return None
    try:
        if PIL_AVAILABLE:
            img = Image.open(path)
            if size:
                img = img.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        else:
            return tk.PhotoImage(file=path)
    except Exception:
        return None


def center_window(win, width, height):
    """Calcula y aplica la posici├│n central para una ventana en la pantalla."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 3 # Un poco m├ís arriba del centro absoluto para mejor visibilidad
    win.geometry(f"{width}x{height}+{x}+{y}")

LICENSE_KEY_PRO = "PIKTA-2026-PRO-A1B2C3D4"
LICENSE_KEY_BIZ = "PIKTA-2026-BIZ-E5F6G7H8"
LICENSE_KEY_ENT = "PIKTA-2026-ENT-I9J0K1L2"
LICENSE_KEY_ULT = "PIKTA-2026-ULT-M3N4O5P6"
TRIAL_DAYS = 30

LICENSE_TYPES = {
    'PRO': {'name': 'Anual', 'days': 365, 'key': LICENSE_KEY_PRO},
    'BIZ': {'name': '3 A├▒os', 'days': 1095, 'key': LICENSE_KEY_BIZ},
    'ENT': {'name': '5 A├▒os', 'days': 1825, 'key': LICENSE_KEY_ENT},
    'ULT': {'name': 'Perpetua', 'days': None, 'key': LICENSE_KEY_ULT},
}

def verify_license():
    """Verifica si el sistema est├í activado o en per├¡odo de prueba."""
    db_name = "PIKTA_SOFT.db"
    if not os.path.exists(db_name):
        return {'status': 'trial', 'days_left': TRIAL_DAYS, 'type': None}
    try:
        conn = sqlite3.connect(db_name, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT valor FROM sistema_config WHERE clave = 'install_date'")
        row = cur.fetchone()
        if not row:
            conn.close()
            return {'status': 'trial', 'days_left': TRIAL_DAYS, 'type': None}
        install_date = datetime.fromisoformat(row[0])
        cur.execute("SELECT valor FROM sistema_config WHERE clave = 'activated'")
        row = cur.fetchone()
        activated = row[0] if row else '0'
        cur.execute("SELECT valor FROM sistema_config WHERE clave = 'license_expires'")
        row = cur.fetchone()
        license_expires = row[0] if row else None
        cur.execute("SELECT valor FROM sistema_config WHERE clave = 'license_type'")
        row = cur.fetchone()
        license_type = row[0] if row else None
        if activated == '1':
            if license_expires:
                expires = datetime.fromisoformat(license_expires)
                if expires < datetime.now():
                    conn.close()
                    return {'status': 'expired', 'days_left': 0, 'type': license_type}
                days_left = (expires - datetime.now()).days
                conn.close()
                return {'status': 'activated', 'days_left': days_left, 'type': license_type}
            conn.close()
            return {'status': 'activated', 'days_left': None, 'type': license_type}
        days_passed = (datetime.now() - install_date).days
        days_left = max(0, TRIAL_DAYS - days_passed)
        conn.close()
        if days_left <= 0:
            return {'status': 'expired', 'days_left': 0, 'type': None}
        return {'status': 'trial', 'days_left': days_left, 'type': None}
    except Exception:
        return {'status': 'trial', 'days_left': TRIAL_DAYS, 'type': None}

def activate_license(key, db):
    """Activa el sistema con la clave de licencia proporcionada."""
    key_upper = key.strip().upper()
    for lic_type, info in LICENSE_TYPES.items():
        if key_upper == info['key']:
            db.execute("UPDATE sistema_config SET valor = '1' WHERE clave = 'activated'")
            db.execute("UPDATE sistema_config SET valor = ? WHERE clave = 'license_type'", (lic_type,))
            if info['days']:
                expires = datetime.now() + timedelta(days=info['days'])
                db.execute("UPDATE sistema_config SET valor = ? WHERE clave = 'license_expires'", (expires.isoformat(),))
            else:
                db.execute("UPDATE sistema_config SET valor = NULL WHERE clave = 'license_expires'")
            return True
    return False

class LicenseWindow:
    """Ventana modal para mostrar estado de licencia y permitir activaci├│n."""
    def __init__(self, parent, db, on_close_callback=None):
        self.result = False
        self.db = db
        self.on_close_callback = on_close_callback
        top = tk.Toplevel(parent)
        top.title("Activaci├│n del Sistema PIK'TA")
        top.geometry("450x400")
        center_window(top, 450, 400)
        top.transient(parent)
        top.grab_set()
        self.top = top
        logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(logo_path) and PIL_AVAILABLE:
            try:
                from PIL import Image, ImageTk
                logo = Image.open(logo_path)
                logo = logo.resize((100, 100), Image.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(logo)
                ttk.Label(top, image=self.logo_img).pack(pady=10)
            except:
                pass
        ttk.Label(top, text="SISTEMA POS PIK'TA", font=(None, 18, 'bold')).pack(pady=5)
        ttk.Label(top, text="Gesti├│n de Restaurante", font=(None, 12)).pack()
        info = verify_license()
        if info['status'] == 'activated':
            lic_name = LICENSE_TYPES.get(info['type'], {}).get('name', 'Desconocida') if info['type'] else 'Lifetime'
            days_msg = f" ({info['days_left']} d├¡as restantes)" if info['days_left'] else ""
            ttk.Label(top, text=f"Ô£ô SISTEMA ACTIVADO - {lic_name}{days_msg}", font=(None, 12, 'bold'), bootstyle="success").pack(pady=20)
            ttk.Button(top, text="Continuar", command=self._on_continue, bootstyle="success", width=20).pack(pady=10)
        elif info['status'] == 'expired':
            ttk.Label(top, text="ÔÜá PER├ìODO DE PRUEBA EXPIRADO", font=(None, 14, 'bold'), bootstyle="danger").pack(pady=10)
            ttk.Label(top, text="Licencias disponibles:", font=(None, 11, 'bold')).pack(pady=5)
            for lt, li in LICENSE_TYPES.items():
                days_str = f"({li['days']} d├¡as)" if li['days'] else "(Permanente)"
                ttk.Label(top, text=f"ÔÇó {li['name']} - {days_str}", font=(None, 10)).pack()
            ttk.Label(top, text="\nIngrese su clave de activaci├│n:", font=(None, 11)).pack(pady=5)
            self.key_entry = ttk.Entry(top, width=35, font=(None, 12))
            self.key_entry.pack(pady=10)
            ttk.Button(top, text="ACTIVAR SISTEMA", command=self.try_activate, bootstyle="primary", width=20).pack(pady=10)
            ttk.Label(top, text=f"Clave de licencia proporcionada por YAFA SOLUTIONS", font=(None, 8), bootstyle="secondary").pack(pady=5)
        else:
            ttk.Label(top, text=f"­ƒôà Per├¡odo de Prueba: {info['days_left']} d├¡as restantes", font=(None, 14, 'bold'), bootstyle="info").pack(pady=20)
            ttk.Label(top, text="Licencias disponibles:", font=(None, 11, 'bold')).pack(pady=5)
            for lt, li in LICENSE_TYPES.items():
                days_str = f"({li['days']} d├¡as)" if li['days'] else "(Permanente)"
                ttk.Label(top, text=f"ÔÇó {li['name']} - {days_str}", font=(None, 10)).pack()
            ttk.Label(top, text="\nIngrese su clave de activaci├│n para usar sin l├¡mites:", font=(None, 11)).pack(pady=5)
            self.key_entry = ttk.Entry(top, width=35, font=(None, 12))
            self.key_entry.pack(pady=10)
            ttk.Button(top, text="ACTIVAR", command=self.try_activate, bootstyle="primary", width=20).pack(pady=10)
            ttk.Button(top, text="Usar Versi├│n de Prueba", command=self._on_continue, bootstyle="secondary", width=20).pack(pady=5)
        top.protocol("WM_DELETE_WINDOW", self.on_close)

    def _on_continue(self):
        self.top.destroy()
        if self.on_close_callback:
            self.on_close_callback()

    def on_close(self):
        """Maneja el cierre de la ventana de licencia."""
        info = verify_license()
        if info['status'] == 'expired':
            self.top.destroy()
            self.result = False
            if self.on_close_callback:
                self.on_close_callback()
        else:
            self.top.destroy()
            if self.on_close_callback:
                self.on_close_callback()

    def try_activate(self):
        key = self.key_entry.get()
        if activate_license(key, self.db):
            messagebox.showinfo("Activaci├│n", "┬íSistema activado correctamente!")
            self.top.destroy()
            if self.on_close_callback:
                self.on_close_callback()
        else:
            messagebox.showerror("Error", "Clave de activaci├│n inv├ílida.\nVerifique e intente de nuevo.")
            play_sound_error()


class DatabaseManager:
    """
    Controlador de la base de datos SQLite.
    Se encarga de crear las tablas, manejar las conexiones y realizar migraciones.
    """

    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        """Abre y retorna una conexi├│n activa a la base de datos."""
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Inicializa las tablas base y asegura que existan los campos necesarios."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            # Creaci├│n de tabla de usuarios
            cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                rol TEXT NOT NULL,
                nombre_completo TEXT
            )''')

            # Creaci├│n de tabla de productos del men├║
            cur.execute('''CREATE TABLE IF NOT EXISTS productos_menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                categoria TEXT,
                emoji TEXT,
                disponible BOOLEAN DEFAULT 1
            )''')

            # Creaci├│n de tabla de pedidos
            cur.execute('''CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                cliente_telefono TEXT,
                cliente_nombre TEXT,
                items TEXT NOT NULL,
                subtotal REAL,
                descuento REAL DEFAULT 0,
                total REAL NOT NULL,
                estado TEXT DEFAULT 'RECIBIDO',
                canal TEXT,
                metodo_pago TEXT,
                pagado BOOLEAN DEFAULT 0,
                notas TEXT,
                mesa TEXT,
                sesion_id INTEGER,
                usuario_id INTEGER,
                created_at TEXT,
                factura_text TEXT
            )''')

            # Creaci├│n de tabla de inventario
            cur.execute('''CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingrediente TEXT NOT NULL UNIQUE,
                cantidad REAL NOT NULL DEFAULT 0,
                unidad TEXT NOT NULL,
                stock_minimo REAL NOT NULL DEFAULT 0
            )''')

            # Creaci├│n de tabla de auditor├¡a (Registro de cambios en datos)
            cur.execute('''CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabla TEXT NOT NULL,
                accion TEXT NOT NULL,
                usuario TEXT,
                detalles TEXT,
                datos_previos TEXT,
                datos_nuevos TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

            # Tabla de configuraci├│n del sistema (Demo/Activaci├│n)
            cur.execute('''CREATE TABLE IF NOT EXISTS sistema_config (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )''')

            # Inicializar fecha de instalaci├│n si no existe
            cur.execute("SELECT valor FROM sistema_config WHERE clave = 'install_date'")
            if not cur.fetchone():
                cur.execute("INSERT INTO sistema_config (clave, valor) VALUES ('install_date', ?)", (datetime.now().isoformat(),))
            cur.execute("SELECT valor FROM sistema_config WHERE clave = 'activated'")
            if not cur.fetchone():
                cur.execute("INSERT INTO sistema_config (clave, valor) VALUES ('activated', '0')")
            cur.execute("SELECT valor FROM sistema_config WHERE clave = 'license_type'")
            if not cur.fetchone():
                cur.execute("INSERT INTO sistema_config (clave, valor) VALUES ('license_type', '')")
            cur.execute("SELECT valor FROM sistema_config WHERE clave = 'license_expires'")
            if not cur.fetchone():
                cur.execute("INSERT INTO sistema_config (clave, valor) VALUES ('license_expires', '')")

            # Migraciones: Asegurar columnas nuevas
            self._ensure_column('productos_menu', 'categoria', 'TEXT')
            self._ensure_column('productos_menu', 'emoji', 'TEXT')
            self._ensure_column('pedidos', 'subtotal', 'REAL')
            self._ensure_column('pedidos', 'descuento', 'REAL')
            self._ensure_column('pedidos', 'canal', 'TEXT')
            self._ensure_column('pedidos', 'usuario_id', 'INTEGER')
            self._ensure_column('pedidos', 'sesion_id', 'INTEGER')
            self._ensure_column('pedidos', 'created_at', 'TEXT')
            self._ensure_column('pedidos', 'mesa', 'TEXT')
            self._ensure_column('pedidos', 'metodo_pago', 'TEXT')
            self._ensure_column('pedidos', 'pagado', 'BOOLEAN')
            self._ensure_column('pedidos', 'factura_text', 'TEXT')

            # Migraci├│n de contrase├▒as a formato hash si es necesario
            cur.execute("SELECT id, username, password FROM usuarios")
            users = cur.fetchall()
            for uid, uname, pwd in users:
                # Si la contrase├▒a no tiene el formato de hash (no contiene ':'), encriptarla
                if ':' not in pwd:
                    new_pwd = hash_password(pwd)
                    cur.execute("UPDATE usuarios SET password = ? WHERE id = ?", (new_pwd, uid))
                    logging.info(f"Contrase├▒a migrada a hash para usuario: {uname}")

            # Usuarios por defecto (con contrase├▒as ya encriptadas)
            seeds = [
                ("Davis", "1234", "Administrador", "Davis Admin"),
                ("Rommel", "1234", "Supervisor", "Rommel Supervisor"),
                ("Estefani", "1234", "Cajera", "Estefani Cajera"),
                ("cocina", "1234", "Cocina", "Personal de Cocina"),
                ("mesero", "1234", "Mesero", "Personal de Mesas"),
                ("admin", "admin", "Administrador", "Administrador Sistema")
            ]
            for u, p, r, n in seeds:
                try:
                    # Buscar si el usuario ya existe
                    cur.execute('SELECT id FROM usuarios WHERE username = ?', (u,))
                    if not cur.fetchone():
                        hashed_p = hash_password(p)
                        cur.execute('INSERT INTO usuarios (username, password, rol, nombre_completo) VALUES (?,?,?,?)', (u, hashed_p, r, n))
                except Exception as e:
                    logging.error(f"Error al insertar usuario base: {e}")

            # --- PRODUCTOS DE PRUEBA (CATEGOR├ìAS POR DEFECTO) ---
            test_products = [
                ("Hamburguesa Cl├ísica", 8.50, "­ƒìö Combos", "­ƒìö"),
                ("Pizza Pepperoni", 12.00, "­ƒìö Combos", "­ƒìò"),
                ("Papas Fritas XL", 4.50, "­ƒìƒ Extras", "­ƒìƒ"),
                ("Alitas BBQ (6 unidades)", 7.25, "­ƒìƒ Extras", "­ƒìù"),
                ("Coca Cola 600ml", 2.00, "­ƒÑñ Bebidas", "­ƒÑñ"),
                ("Jugo de Naranja Natural", 3.50, "­ƒÑñ Bebidas", "­ƒìè")
            ]
            for n, p, c, e in test_products:
                try:
                    cur.execute('SELECT id FROM productos_menu WHERE nombre = ?', (n,))
                    if not cur.fetchone():
                        cur.execute('INSERT INTO productos_menu (nombre, precio, categoria, emoji) VALUES (?,?,?,?)', (n, p, c, e))
                except Exception as e:
                    logging.error(f"Error al insertar producto de prueba: {e}")

            # Registro de logs de acceso (qui├®n entra y sale del sistema)
            cur.execute('''CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT,
                details TEXT,
                created_at TEXT
            )''')

            # Sesiones de caja (apertura y cierre de caja)
            cur.execute('''CREATE TABLE IF NOT EXISTS caja_sesiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                inicio TEXT,
                inicial REAL DEFAULT 0,
                monto_apertura REAL,
                estado TEXT DEFAULT 'ABIERTO',
                cierre_total REAL,
                cierre_at TEXT,
                reporte_texto TEXT
            )''')

            # Migraciones: Asegurar columnas nuevas
            self._ensure_column('caja_sesiones', 'reporte_texto', 'TEXT')
            
            conn.commit()

    def audit_log(self, tabla, accion, usuario=None, detalles='', prev=None, new=None):
        """Registra un evento en la tabla de auditor├¡a."""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute('''INSERT INTO auditoria (tabla, accion, usuario, detalles, datos_previos, datos_nuevos) 
                             VALUES (?,?,?,?,?,?)''',
                            (tabla, accion, usuario, detalles, 
                             json.dumps(prev) if prev else None, 
                             json.dumps(new) if new else None))
                conn.commit()
        except Exception as e:
            logging.error(f"Error en log de auditor├¡a: {e}")

    def create_backup(self):
        """Crea una copia de seguridad de la base de datos actual."""
        if not os.path.exists('Backups'):
            os.makedirs('Backups')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join('Backups', f'PIkTA_DB_backup_{timestamp}.db')
        
        try:
            shutil.copy2(self.db_name, backup_path)
            # Limpiar backups antiguos (mantener solo los ├║ltimos 30 d├¡as)
            now = datetime.now()
            for f in os.listdir('Backups'):
                f_path = os.path.join('Backups', f)
                if os.path.isfile(f_path):
                    f_time = datetime.fromtimestamp(os.path.getctime(f_path))
                    if (now - f_time).days > 30:
                        os.remove(f_path)
            return backup_path
        except Exception as e:
            logging.error(f"Error al crear backup: {e}")
            return None

    def _ensure_column(self, table, column, col_type):
        """Funci├│n auxiliar para a├▒adir columnas si no existen (idempotente)."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(f"PRAGMA table_info({table})")
                cols = [r[1] for r in cur.fetchall()]
                if column not in cols:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                    conn.commit()
            except Exception as e:
                logging.error(f"Error al a├▒adir columna {column} a {table}: {e}")

    def log_access(self, user_id, username, action, details=''):
        """Guarda un evento de acceso en la tabla access_logs."""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute('INSERT INTO access_logs (user_id, username, action, details, created_at) VALUES (?,?,?,?,?)',
                            (user_id, username, action, details, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            logging.exception(f'Error al registrar acceso: {e}')

    def fetch_all(self, query, params=()):
        """Ejecuta una consulta SELECT y devuelve todas las filas."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def fetch_one(self, query, params=()):
        """Ejecuta una consulta SELECT y devuelve una sola fila."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()

    def execute(self, query, params=()):
        """Ejecuta INSERT, UPDATE o DELETE y confirma los cambios."""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                return cur
        except Exception as e:
            logging.exception(f'Error de ejecuci├│n DB: {e} - Query: {query}')
            raise


class POSFrame(tk.Canvas):
    """
    Interfaz de Punto de Venta (Caja).
    Permite realizar ventas directas y cobrar pedidos de meseros.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(parent, bg=BG, highlightthickness=0, *args, **kwargs)
        self.db = db
        self.user = user
        self.session_id = None
        self.cart = [] 
        
        # Logo de Fondo en POS
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            self.bg_raw = Image.open(bg_logo_path)
            self.last_bg_w, self.last_bg_h = 0, 0
            def draw_pos_bg(e):
                cw, ch = e.width, e.height
                if cw < 10 or ch < 10: return
                if abs(cw - self.last_bg_w) < 20 and abs(ch - self.last_bg_h) < 20: return
                
                self.last_bg_w, self.last_bg_h = cw, ch
                self.delete("bg")
                img_res = self.bg_raw.resize((cw, ch), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(img_res)
                self.create_image(cw//2, ch//2, image=self.bg_photo, tags="bg")
                self.tag_lower("bg")
            self.bind("<Configure>", draw_pos_bg)

        # --- Contenedores para Secciones (Sin main_container que tape todo) ---
        # Cabecera - Flota sobre el canvas
        self.header = ttk.Frame(self, bootstyle="info", padding=15)
        self.header_win = self.create_window(0, 0, window=self.header, anchor='nw', tags="header")
        
        # Cuerpo - Pesta├▒as de POS
        self.body = ttk.Frame(self, padding=10)
        self.body_win = self.create_window(0, 70, window=self.body, anchor='nw', tags="body")
        
        def resize_pos_content(e):
            # Ajustar anchos de las ventanas del canvas
            self.itemconfig("header", width=e.width)
            self.itemconfig("body", width=e.width, height=e.height - 70)
            if hasattr(self, 'bg_raw'): draw_pos_bg(e)
            
        self.bind("<Configure>", resize_pos_content)

        # --- Contenido de la Cabecera ---
        # Icono decorativo del POS
        pos_img = load_image(os.path.join('Imagenes', 'pos.png'), size=(60, 60))
        if pos_img:
            lbl = ttk.Label(self.header, image=pos_img, bootstyle="inverse-info")
            lbl.image = pos_img
            lbl.pack(side='left', padx=10)
        
        ttk.Label(self.header, text='­ƒøÆ PUNTO DE VENTA (Caja)', font=(None, 24, 'bold'), bootstyle="inverse-info").pack(side='left', padx=10)
        
        # Botones de acci├│n r├ípida en la cabecera (m├ís grandes)
        ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10, takefocus=True).pack(side='right', padx=5)

        self.btn_open_caja = ttk.Button(self.header, text='Abrir Caja', command=self.open_caja, bootstyle="success", cursor="hand2", padding=10)
        self.btn_open_caja.pack(side='right', padx=5)
        self.btn_close_caja = ttk.Button(self.header, text='Cerrar Caja', command=self.cerrar_caja, bootstyle="danger", cursor="hand2", padding=10)
        self.btn_close_caja.pack(side='right', padx=5)

        # --- Contenedor de Pesta├▒as Internas ---
        self.pos_notebook = ttk.Notebook(self.body)
        self.pos_notebook.pack(fill='both', expand=True, pady=10)

        # Pesta├▒a 1: Venta Directa
        self.tab_venta = ttk.Frame(self.pos_notebook, padding=10)
        self.pos_notebook.add(self.tab_venta, text='­ƒøÆ Venta Directa')

        # Lado izquierdo de Venta Directa: Cat├ílogo
        left_v = ttk.Frame(self.tab_venta)
        left_v.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Filtro de categor├¡as
        self.categories = ['­ƒìö Combos', '­ƒìƒ Extras', '­ƒÑñ Bebidas']
        self.selected_category = tk.StringVar(value=self.categories[0])
        cat_frame = ttk.Frame(left_v)
        cat_frame.pack(fill='x', pady=(0, 15))
        for c in self.categories:
            ttk.Radiobutton(cat_frame, text=c, variable=self.selected_category, value=c, 
                           command=self.render_products, bootstyle="info-toolbutton", padding=10).pack(side='left', padx=5)

        # Contenedor con scroll para los productos
        self.products_canvas = tk.Canvas(left_v, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(left_v, orient="vertical", command=self.products_canvas.yview)
        self.products_frame = ttk.Frame(self.products_canvas)

        self.products_frame.bind("<Configure>", lambda e: self.products_canvas.configure(scrollregion=self.products_canvas.bbox("all")))
        self.products_canvas.create_window((0, 0), window=self.products_frame, anchor="nw")
        self.products_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.products_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Lado derecho de Venta Directa: Carrito (Estilo Excel)
        right_v = ttk.Frame(self.tab_venta, width=500, bootstyle="secondary")
        right_v.pack(side='right', fill='y')
        right_v.pack_propagate(False)
        
        ttk.Label(right_v, text='­ƒôï ORDEN ACTUAL', font=(None, 14, 'bold'), bootstyle="inverse-secondary", padding=10).pack(fill='x')
        
        # Carrito estilo Excel con Treeview editable
        cart_frame = ttk.Frame(right_v, padding=5)
        cart_frame.pack(fill='both', expand=True, padx=5)
        
        cols = ('Producto', 'Cant', 'Precio', 'Subtotal')
        self.cart_tree = ttk.Treeview(cart_frame, columns=cols, show='headings', height=8)
        for col in cols:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, anchor='center', width=80)
        
        self.cart_tree.column('Producto', width=180, anchor='w')
        self.cart_tree.column('Cant', width=60, anchor='center')
        self.cart_tree.pack(fill='both', expand=True)
        
        # Vincular doble clic para edici├│n tipo Excel en la cantidad
        self.cart_tree.bind("<Double-1>", self.on_cart_double_click)
        
        # Scrollbar para el carrito
        cart_scroll = ttk.Scrollbar(cart_frame, orient='vertical', command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_scroll.set)
        cart_scroll.pack(side='right', fill='y')
        
        # Marco para controles de cantidad
        qty_frame = ttk.Frame(right_v, padding=5)
        qty_frame.pack(fill='x', padx=5)
        
        ttk.Label(qty_frame, text="Cantidad:").pack(side='left', padx=5)
        self.qty_var = tk.StringVar(value="1")
        self.qty_entry = ttk.Entry(qty_frame, textvariable=self.qty_var, width=5, font=(None, 14, 'bold'))
        self.qty_entry.pack(side='left', padx=5)
        
        def qty_increase():
            try:
                val = int(self.qty_var.get()) + 1
                self.qty_var.set(str(val))
            except: self.qty_var.set("1")
        def qty_decrease():
            try:
                val = int(self.qty_var.get()) - 1
                if val < 1: val = 1
                self.qty_var.set(str(val))
            except: self.qty_var.set("1")
        
        ttk.Button(qty_frame, text='+', command=qty_increase, width=3, bootstyle="success-outline").pack(side='left', padx=2)
        ttk.Button(qty_frame, text='-', command=qty_decrease, width=3, bootstyle="danger-outline").pack(side='left', padx=2)
        
        self.total_label = ttk.Label(right_v, text='Total: $0.00', font=(None, 18, 'bold'), bootstyle="inverse-secondary", padding=10)
        self.total_label.pack(fill='x')

        # Selector de canal en Caja (SOLO Para llevar - el local se maneja por mesero)
        chan_frame = ttk.Frame(right_v, bootstyle="secondary", padding=5)
        chan_frame.pack(fill='x')
        ttk.Label(chan_frame, text="Tipo de Pedido:", bootstyle="inverse-secondary").pack(side='left', padx=5)
        self.order_channel = tk.StringVar(value="LLEVAR") # Por defecto Para Llevar
        ttk.Radiobutton(chan_frame, text="­ƒøì´©Å Llevar", variable=self.order_channel, value="LLEVAR", bootstyle="success-toolbutton").pack(side='left', padx=10)

        # Botones de acci├│n
        btn_frame = ttk.Frame(right_v, padding=5)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text='ÔØî QUITAR', command=self.remove_selected_cart, bootstyle="danger", cursor="hand2", padding=8).pack(side='left', padx=2, expand=True, fill='x')
        ttk.Button(btn_frame, text='­ƒùæ´©Å LIMPIAR', command=self.clear_cart, bootstyle="secondary", cursor="hand2", padding=8).pack(side='left', padx=2, expand=True, fill='x')
        
        ttk.Button(right_v, text='Ô£à CONFIRMAR PEDIDO', command=self.process_order, bootstyle="success", cursor="hand2", padding=15).pack(fill='x', padx=10, pady=10)

        # Pesta├▒a 2: Cobrar Mesas
        self.tab_cobros = ttk.Frame(self.pos_notebook, padding=10)
        self.pos_notebook.add(self.tab_cobros, text='­ƒôï Cobrar Mesas')
        
        self.build_cobros_tab()

        # Cargar productos inicialmente
        self.render_products()

    def build_cobros_tab(self):
        """Construye la interfaz para cobrar pedidos de meseros con teclado num├®rico y m├®todos de pago."""
        # Lado izquierdo: Lista de pedidos pendientes
        left_c = ttk.Frame(self.tab_cobros)
        left_c.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        ttk.Label(left_c, text='PEDIDOS PENDIENTES DE COBRO', font=(None, 14, 'bold')).pack(pady=10)
        
        # Tabla de pedidos pendientes
        cols = ('ID', 'N├║mero', 'Mesa', 'Total', 'Fecha')
        self.unpaid_tree = ttk.Treeview(left_c, columns=cols, show='headings', bootstyle="info")
        for col in cols:
            self.unpaid_tree.heading(col, text=col)
            self.unpaid_tree.column(col, width=100)
        
        self.unpaid_tree.pack(fill='both', expand=True)
        
        ttk.Button(left_c, text='Actualizar Lista', command=self.refresh_unpaid_orders, bootstyle="info-outline").pack(pady=10)
        
        # Lado derecho: Detalles y Cobro (M├ís ancho para el teclado y detalle)
        right_c = ttk.Frame(self.tab_cobros, width=750, bootstyle="secondary")
        right_c.pack(side='right', fill='y')
        right_c.pack_propagate(False)
        
        ttk.Label(right_c, text='DETALLE DE CUENTA', font=(None, 16, 'bold'), bootstyle="inverse-secondary", padding=5).pack(fill='x')
        # Detalle m├ís compacto verticalmente
        self.detail_text = tk.Text(right_c, bg=PANEL, fg=FG, font=(None, 14), height=5)
        self.detail_text.pack(fill='x', padx=10, pady=2)
        self.detail_text.config(state='disabled')
        
        self.total_cobro_label = ttk.Label(right_c, text='Total a Cobrar: $0.00', font=(None, 24, 'bold'), bootstyle="inverse-secondary", padding=5)
        self.total_cobro_label.pack(fill='x')

        # Bot├│n para Agregar m├ís productos a la mesa seleccionada
        ttk.Button(right_c, text='Ô£Ü AGREGAR PRODUCTOS A ESTA MESA', 
                  command=self.add_more_to_table, bootstyle="warning", cursor="hand2", padding=8).pack(fill='x', padx=10, pady=2)

        # --- Teclado Num├®rico y M├®todos de Pago ---
        pay_frame = ttk.Frame(right_c, bootstyle="secondary", padding=5)
        pay_frame.pack(fill='both', expand=True)

        # Entrada de "Paga con"
        ttk.Label(pay_frame, text="Paga con $:", font=(None, 12), bootstyle="inverse-secondary").grid(row=0, column=0, columnspan=2, sticky='w')
        self.pay_amount_var = tk.StringVar(value="0.00")
        self.pay_entry = ttk.Entry(pay_frame, textvariable=self.pay_amount_var, font=(None, 20, 'bold'), justify='right')
        self.pay_entry.grid(row=1, column=0, columnspan=3, sticky='ew', pady=5)

        # Teclado Num├®rico (M├ís grande)
        numpad = ttk.Frame(pay_frame, bootstyle="secondary")
        numpad.grid(row=2, column=0, rowspan=4, columnspan=2, pady=5)

        buttons = [
            '7', '8', '9',
            '4', '5', '6',
            '1', '2', '3',
            '0', '.', 'C'
        ]

        def press_key(key):
            curr = self.pay_amount_var.get()
            if key == 'C':
                self.pay_amount_var.set("0.00")
            elif key == '.':
                if '.' not in curr: self.pay_amount_var.set(curr + '.')
            else:
                if curr == "0.00": self.pay_amount_var.set(key)
                else: self.pay_amount_var.set(curr + key)

        for i, b in enumerate(buttons):
            btn = ttk.Button(numpad, text=b, width=5, style="Light.Large.TButton", 
                            command=lambda x=b: press_key(x), padding=12)
            btn.grid(row=i//3, column=i%3, padx=2, pady=2, sticky='nsew')
            btn.configure(cursor="hand2")

        # M├®todos de Pago con Im├ígenes (Convertidos a botones funcionales)
        methods_frame = ttk.Frame(pay_frame, bootstyle="secondary")
        methods_frame.grid(row=2, column=2, rowspan=4, padx=(10, 0), sticky='nsew')

        self.payment_method = tk.StringVar(value="EFECTIVO")
        
        methods = [
            ('EFECTIVO', 'efectivo.jpeg', 'success'),
            ('YAPPY', 'yappy.png', 'info'),
            ('TARJETA', 'visa.png', 'primary')
        ]

        ttk.Label(methods_frame, text="M├ëTODOS DE PAGO", font=(None, 11, 'bold'), bootstyle="inverse-secondary").pack(pady=(0, 5))

        for i, (name, img_file, style) in enumerate(methods):
            m_btn_container = ttk.Frame(methods_frame, bootstyle="secondary")
            m_btn_container.pack(fill='x', pady=2)
            
            img = load_image(os.path.join('Imagenes', img_file), size=(45, 45))
            
            # Bot├│n de pago directo
            btn_pay = ttk.Button(m_btn_container, text=f"{name}", 
                                image=img, compound='left',
                                command=lambda n=name: self.pay_with_method(n), 
                                bootstyle=f"{style}", cursor="hand2", padding=10)
            btn_pay.image = img
            btn_pay.pack(fill='x', expand=True)

        # Cambio
        self.change_label = ttk.Label(right_c, text='Cambio: $0.00', font=(None, 18, 'bold'), bootstyle="inverse-secondary", padding=5)
        self.change_label.pack(fill='x')
        
        def update_change(*args):
            try:
                total = float(self.total_cobro_label.cget("text").split('$')[1])
                paid = float(self.pay_amount_var.get())
                change = paid - total
                self.change_label.config(text=f"Cambio: ${max(0, change):.2f}")
            except: pass
        
        self.pay_amount_var.trace_add("write", update_change)

        self.unpaid_tree.bind('<<TreeviewSelect>>', self.on_unpaid_select)
        self.refresh_unpaid_orders()

    def pay_with_method(self, method):
        """Asigna el m├®todo de pago y procesa la transacci├│n inmediatamente."""
        self.payment_method.set(method)
        self.pay_order()

    def refresh_unpaid_orders(self):
        """Consulta pedidos de meseros y de caja (para llevar) que a├║n no han sido pagados."""
        # Solo refrescar si no hay un elemento seleccionado para evitar perder la selecci├│n del usuario
        has_selection = bool(self.unpaid_tree.selection())
        
        if not has_selection:
            for r in self.unpaid_tree.get_children(): self.unpaid_tree.delete(r)
            
            # Incluimos 'LLEVAR' en la consulta para que el cajero pueda cobrarlos
            query = "SELECT id, numero, mesa, total, created_at FROM pedidos WHERE pagado = 0 AND canal IN ('MESERO', 'LLEVAR') ORDER BY created_at DESC"
            rows = self.db.fetch_all(query)
            for r in rows:
                # Si mesa es None (pedidos para llevar), mostrar 'PARA LLEVAR'
                values = list(r)
                if values[2] is None: values[2] = 'PARA LLEVAR'
                self.unpaid_tree.insert('', 'end', values=values)
        
        # Programar el siguiente refresco autom├ítico en 5 segundos (5000 ms)
        self.after(5000, self.refresh_unpaid_orders)

    def on_unpaid_select(self, event):
        """Muestra el detalle del pedido seleccionado."""
        sel = self.unpaid_tree.selection()
        if not sel: return
        item = self.unpaid_tree.item(sel[0])
        order_id = item['values'][0]
        
        order = self.db.fetch_one("SELECT items, total FROM pedidos WHERE id = ?", (order_id,))
        if order:
            items = json.loads(order[0])
            self.detail_text.config(state='normal')
            self.detail_text.delete('1.0', 'end')
            # Detalle con fuente m├ís legible
            self.detail_text.insert('end', f"{'PRODUCTO':<20} {'PRECIO':>10}\n")
            self.detail_text.insert('end', "-"*35 + "\n")
            for it in items:
                self.detail_text.insert('end', f"{it['nombre']:<20} ${it['precio']:>10.2f}\n")
            self.detail_text.config(state='disabled')
            self.total_cobro_label.config(text=f"Total a Cobrar: ${order[1]:.2f}")
            self.pay_amount_var.set(f"{order[1]:.2f}")

    def generate_invoice(self, order_id, paid_amount, change):
        """Genera el texto de una factura estilo ticket con el formato Pik'ta Grill."""
        order = self.db.fetch_one("SELECT numero, items, total, created_at, metodo_pago, mesa FROM pedidos WHERE id = ?", (order_id,))
        if not order: return ""

        numero, items_json, total, fecha, metodo, mesa = order
        items = json.loads(items_json) if items_json else []
        fecha_fmt = datetime.fromisoformat(fecha).strftime('%d/%m/%Y %H:%M:%S')
        usuario = self.user.get('nombre_completo') if self.user else "Davis" # Default to Davis if no user
        mesa_display = mesa if mesa else 'PARA LLEVAR'

        # Formato exacto seg├║n la imagen proporcionada
        factura =  "    *** PIK'TA GRILL ***\n"
        factura += "    DONDE SI SABEMOS DE HAMBURGUESAS\n"
        factura += "    ------------------------------------\n"
        factura += f"    FACTURA: {numero}\n"
        factura += f"    FECHA:   {fecha_fmt}\n"
        factura += f"    MESA:    {mesa_display}\n"
        factura += f"    CAJERO:  {usuario}\n"
        factura += "    ------------------------------------\n"
        factura += f"    {'CANT':<5} {'DESCRIPCI├ôN':<20} {'SUBT':>8}\n"
        factura += "    ------------------------------------\n"

        for it in items:
            nombre = it.get('nombre', 'N/A')[:20]
            precio = it.get('precio', 0)
            qty = it.get('qty', 1)
            subt = precio * qty
            factura += f"    {qty:<5} {nombre:<20} {subt:>8.2f}\n"

        factura += "    ------------------------------------\n"
        factura += f"    TOTAL:                    $ {total:>8.2f}\n"
        factura += f"    RECIBIDO:                 $ {paid_amount:>8.2f}\n"
        factura += f"    CAMBIO:                   $ {change:>8.2f}\n"
        factura += "    ------------------------------------\n"
        factura += f"    M├ëTODO DE PAGO: {metodo.upper()}\n"
        factura += "    ------------------------------------\n"
        factura += "         ┬íGRACIAS POR SU VISITA!\n"
        factura += "              REGRESE PRONTO\n"
        factura += "    " + "*" * 36 + "\n"
        factura += "\n\n\n" # L├¡neas extra para el corte

        return factura

    def pay_order(self):
        """Registra el pago del pedido seleccionado y genera la factura."""
        sel = self.unpaid_tree.selection()
        if not sel:
            messagebox.showwarning('Aviso', 'Seleccione un pedido para cobrar')
            return
        
        if not self.session_id:
            messagebox.showwarning('Caja', 'Debe abrir la caja antes de procesar pagos')
            return

        item = self.unpaid_tree.item(sel[0])
        order_id = item['values'][0]
        method = self.payment_method.get()
        
        try:
            total_str = self.total_cobro_label.cget("text").split("$")[1]
            total = float(total_str)
            paid_amount = float(self.pay_amount_var.get())
            
            if paid_amount < total:
                messagebox.showerror("Error", "El monto pagado es menor al total.")
                return
                
            change = paid_amount - total
            
            if messagebox.askyesno('Confirmar Pago', f'┬┐Confirmar el pago de ${total:.2f} con {method}?\nCambio: ${change:.2f}'):
                # Generar Factura PRIMERO para guardarla en la BD
                factura_text = self.generate_invoice(order_id, paid_amount, change)
                
                self.db.execute('UPDATE pedidos SET pagado = 1, sesion_id = ?, metodo_pago = ?, factura_text = ? WHERE id = ?', 
                                (self.session_id, method, factura_text, order_id))
                
                messagebox.showinfo('├ëxito', f'Pago procesado correctamente.\nCambio: ${change:.2f}')
                
                # Mostrar factura y opci├│n de imprimir
                self.show_invoice_popup(factura_text)
                
                self.refresh_unpaid_orders()
                self.detail_text.config(state='normal')
                self.detail_text.delete('1.0', 'end')
                self.detail_text.config(state='disabled')
                self.total_cobro_label.config(text="Total a Cobrar: $0.00")
                self.pay_amount_var.set("0.00")
                
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto v├ílido.")
        except Exception as e:
            logging.error(f"Error al procesar pago: {e}")
            messagebox.showerror('Error', 'No se pudo procesar el pago')

    def show_invoice_popup(self, text, title="FACTURA PIK'TA"):
        """Muestra la factura o reporte en una ventana emergente con opci├│n de impresi├│n."""
        top = tk.Toplevel(self)
        top.title(title)
        top.geometry("400x650")
        
        # Logo en la factura popup
        logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(logo_path):
            img = load_image(logo_path, size=(100, 100))
            if img:
                lbl_logo = ttk.Label(top, image=img)
                lbl_logo.image = img
                lbl_logo.pack(pady=10)

        t = tk.Text(top, height=25, width=40, font=("Courier", 10))
        t.insert('1.0', text)
        t.config(state='disabled')
        t.pack(padx=10, pady=10)
        
        def print_invoice():
            logo_path = os.path.join('Imagenes', 'pikta2.png')
            
            # Usar carpeta temporal para la impresi├│n
            temp_dir = os.path.join(os.environ.get('TEMP', 'C:\\temp'), 'PiktaInvoices')
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            # Detectar impresora autom├íticamente
            printer_name = find_pos_printer()
            
            # 1. Intentar abrir el caj├│n de dinero (ESC/POS command)
            if WIN32_PRINT_AVAILABLE and printer_name:
                try:
                    hPrinter = win32print.OpenPrinter(printer_name)
                    try:
                        # Comando ESC/POS para abrir caj├│n: ESC p m t1 t2
                        # \x1b\x70\x00\x19\xfa es el est├índar para cajones de 24V/12V
                        raw_data = b'\x1b\x70\x00\x19\xfa'
                        win32print.StartDocPrinter(hPrinter, 1, ("Cajon", None, "RAW"))
                        win32print.StartPagePrinter(hPrinter)
                        win32print.WritePrinter(hPrinter, raw_data)
                        win32print.EndPagePrinter(hPrinter)
                        win32print.EndDocPrinter(hPrinter)
                    finally:
                        win32print.ClosePrinter(hPrinter)
                except Exception as e:
                    logging.error(f"Error al abrir caj├│n: {e}")

            # 2. Generar y enviar factura
            if PIL_AVAILABLE:
                from PIL import Image, ImageDraw, ImageFont
                
                # Ticket est├índar de 80mm
                img_width = 380 
                
                # Calcular altura din├ímica
                lines = text.split('\n')
                line_height = 22 # Un poco m├ís de espacio entre l├¡neas
                header_space = 180 
                footer_space = 40
                img_height = header_space + (len(lines) * line_height) + footer_space
                
                img = Image.new('RGB', (img_width, img_height), 'white')
                draw = ImageDraw.Draw(img)
                
                # Centrar Logo
                try:
                    if os.path.exists(logo_path):
                        logo = Image.open(logo_path)
                        logo = logo.resize((150, 150), Image.LANCZOS)
                        logo_x = (img_width - 150) // 2
                        img.paste(logo, (logo_x, 10))
                except:
                    pass
                    
                # Fuentes - Arial es est├índar en Windows
                try:
                    font_bold = ImageFont.truetype("arialbd.ttf", 15)
                    font_regular = ImageFont.truetype("arial.ttf", 12)
                except:
                    font_bold = ImageFont.load_default()
                    font_regular = ImageFont.load_default()
                
                y = 170
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean: 
                        y += line_height
                        continue
                        
                    # Centrar l├¡neas que empiezan con * o son cabeceras
                    is_centered = line_clean.startswith('*') or 'PIK' in line or 'GRACIAS' in line or 'REGRESE' in line or 'GRILL' in line
                    
                    if is_centered:
                        try:
                            bbox = draw.textbbox((0, 0), line_clean, font=font_bold)
                            w = bbox[2] - bbox[0]
                            draw.text(((img_width - w) // 2, y), line_clean, fill='black', font=font_bold)
                        except:
                            draw.text((10, y), line, fill='black', font=font_bold)
                    elif '====' in line or '----' in line:
                        draw.text((10, y), line, fill='black', font=font_bold)
                    else:
                        draw.text((10, y), line, fill='black', font=font_regular)
                    y += line_height
                
                # Guardar en la carpeta temporal
                base_name = f"factura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                filename = os.path.join(temp_dir, base_name)
                img.save(filename)
                
                # Enviar a imprimir usando la impresora detectada
                try:
                    if WIN32_PRINT_AVAILABLE and printer_name:
                        # Usar win32api para imprimir en la impresora espec├¡fica
                        win32api.ShellExecute(0, "printto", filename, f'"{printer_name}"', ".", 0)
                        messagebox.showinfo("Impresi├│n", f"Enviado a: {printer_name}\nCaj├│n abierto.")
                    else:
                        os.startfile(filename, "print")
                        messagebox.showinfo("Impresi├│n", "Enviado a impresora por defecto.")
                except Exception as e:
                    logging.error(f"Error al imprimir: {e}")
                    # Fallback
                    os.startfile(filename)
            else:
                # Fallback a texto plano
                base_name = f"factura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                filename = os.path.join(temp_dir, base_name)
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(text)
                os.startfile(filename)

        ttk.Button(top, text="­ƒû¿ IMPRIMIR FACTURA", command=print_invoice, bootstyle="success").pack(pady=10)
        ttk.Button(top, text="Cerrar", command=top.destroy, bootstyle="secondary").pack(pady=5)

    def add_more_to_table(self):
        """Prepara el sistema para agregar m├ís productos a un pedido de mesa ya existente."""
        sel = self.unpaid_tree.selection()
        if not sel:
            messagebox.showwarning('Aviso', 'Seleccione una mesa primero')
            return
            
        item = self.unpaid_tree.item(sel[0])
        order_id = item['values'][0]
        mesa = item['values'][2]
        
        # Guardar en memoria que estamos editando una mesa
        self.editing_table_id = order_id
        
        # Cambiar a la pesta├▒a de Venta Directa
        self.pos_notebook.select(0)
        
        # Mostrar aviso visual de que estamos editando
        messagebox.showinfo("Modo Edici├│n", f"EST├ü EDITANDO LA {mesa}.\n\nAgregue los productos extras y presione 'CONFIRMAR PEDIDO' para guardarlos en la cuenta de la mesa.")

    def update_existing_order(self):
        """Actualiza un pedido existente con los nuevos productos del carrito."""
        if not self.cart: return
        
        try:
            # Obtener items actuales
            res = self.db.fetch_one("SELECT items, mesa FROM pedidos WHERE id=?", (self.editing_table_id,))
            if not res: return
            
            current_items = json.loads(res[0])
            mesa = res[1]
            
            # A├▒adir nuevos respetando la cantidad
            new_items_to_add = []
            for p in self.cart:
                qty = p.get('qty', 1)
                for _ in range(qty):
                    new_items_to_add.append({'id': p['id'], 'nombre': p['nombre'], 'precio': p['precio']})
            
            updated_items = current_items + new_items_to_add
            new_total = sum(p['precio'] for p in updated_items)
            
            self.db.execute("UPDATE pedidos SET items=?, subtotal=?, total=? WHERE id=?", 
                            (json.dumps(updated_items, ensure_ascii=False), new_total, new_total, self.editing_table_id))
            
            # Registrar en auditor├¡a
            self.db.audit_log('pedidos', 'UPDATE', self.user.get('username'), f'Productos extras a├▒adidos a {mesa}', new=new_items_to_add)
            
            messagebox.showinfo("├ëxito", f"Productos a├▒adidos correctamente a la {mesa}.")
            
            # Limpiar estado
            self.cart.clear()
            self.update_cart_display()
            self.editing_table_id = None
            
            # Volver a pesta├▒a de cobros
            self.pos_notebook.select(1)
            self.refresh_unpaid_orders()
            
        except Exception as e:
            logging.error(f"Error al actualizar mesa: {e}")
            messagebox.showerror("Error", "No se pudo actualizar la mesa.")

    def render_products(self):
        """Genera din├ímicamente las tarjetas de productos seg├║n la categor├¡a."""
        # Limpiar productos anteriores
        for w in self.products_frame.winfo_children():
            w.destroy()
        
        # Obtener productos de la base de datos
        products = self.db.fetch_all('SELECT id, nombre, precio, categoria, emoji FROM productos_menu')
        filtered = [p for p in products if (p[3] or '').strip() == self.selected_category.get()]
        
        if not filtered:
            ttk.Label(self.products_frame, text="No hay productos en esta categor├¡a", padding=20).pack()
            return

        # Dibujar productos en un grid de 3 columnas (M├ís grandes)
        cols = 3
        product_btns = []
        for idx, p in enumerate(filtered):
            r, c = divmod(idx, cols)
            card = ttk.Frame(self.products_frame, bootstyle="light", padding=15)
            card.grid(row=r, column=c, padx=12, pady=12, sticky='nsew')
            
            ttk.Label(card, text=p[4] or '­ƒì¢', font=(None, 40), bootstyle="inverse-light").pack(pady=5)
            ttk.Label(card, text=p[1], font=(None, 14, 'bold'), bootstyle="inverse-light", wraplength=140, justify='center').pack()
            ttk.Label(card, text=f"${p[2]:.2f}", font=(None, 16), bootstyle="info").pack(pady=5)
            
            # Bot├│n para a├▒adir al carrito (m├ís grande)
            btn = ttk.Button(card, text='A├▒adir', command=lambda pid=p: self.add_product(pid), bootstyle="info", cursor="hand2", takefocus=True, padding=8)
            btn.pack(fill='x')
            product_btns.append(btn)
            
            # Navegaci├│n por flechas entre botones de productos
            def make_pos_nav(idx):
                def nav(e):
                    if e.keysym == 'Left' and idx > 0: product_btns[idx-1].focus_set()
                    elif e.keysym == 'Right' and idx < len(product_btns)-1: product_btns[idx+1].focus_set()
                    elif e.keysym == 'Up' and idx >= cols: product_btns[idx-cols].focus_set()
                    elif e.keysym == 'Down' and idx + cols < len(product_btns): product_btns[idx+cols].focus_set()
                return nav
            
            btn.bind("<Left>", make_pos_nav(idx))
            btn.bind("<Right>", make_pos_nav(idx))
            btn.bind("<Up>", make_pos_nav(idx))
            btn.bind("<Down>", make_pos_nav(idx))

        # Configurar pesos de columnas para que sean uniformes
        for i in range(cols):
            self.products_frame.columnconfigure(i, weight=1)

    def add_product(self, product):
        """Agrega un producto a la lista del carrito con la cantidad seleccionada."""
        try:
            qty = int(self.qty_var.get()) if hasattr(self, 'qty_var') else 1
        except:
            qty = 1
        if qty < 1: qty = 1
        
        # Verificar si el producto ya existe para incrementar cantidad
        existing = None
        for i, item in enumerate(self.cart):
            if item['id'] == product[0]:
                existing = i
                break
        
        if existing is not None:
            self.cart[existing]['qty'] += qty
        else:
            self.cart.append({'id': product[0], 'nombre': product[1], 'precio': product[2], 'qty': qty})
        
        self.update_cart_display()
        self.qty_var.set("1") # Reset cantidad

    def remove_selected_cart(self):
        """Elimina el producto seleccionado del carrito."""
        sel = self.cart_tree.selection()
        if not sel: return
        idx = int(sel[0].replace('I', '')) - 1
        if 0 <= idx < len(self.cart):
            del self.cart[idx]
        self.update_cart_display()

    def clear_cart(self):
        """Limpia todo el carrito."""
        self.cart.clear()
        self.update_cart_display()

    def on_cart_double_click(self, event):
        """Habilita la edici├│n manual de la cantidad al hacer doble clic (Estilo Excel)."""
        region = self.cart_tree.identify_region(event.x, event.y)
        if region != "cell": return

        column = self.cart_tree.identify_column(event.x)
        if column != '#2': return # Solo permitir edici├│n en la columna 'Cant'

        item_id = self.cart_tree.identify_row(event.y)
        if not item_id: return

        # Obtener dimensiones de la celda
        x, y, width, height = self.cart_tree.bbox(item_id, column)

        # Crear Entry flotante
        entry = ttk.Entry(self.cart_tree)
        entry.place(x=x, y=y, width=width, height=height)
        
        # Obtener cantidad actual (quitando la 'x')
        curr_val = self.cart_tree.item(item_id, 'values')[1].replace('x', '')
        entry.insert(0, curr_val)
        entry.select_range(0, 'end')
        entry.focus_set()

        def save_edit(e=None):
            try:
                new_qty = int(entry.get())
                if new_qty < 1: new_qty = 1
                
                # Actualizar el objeto en el carrito
                idx = int(item_id) - 1
                if 0 <= idx < len(self.cart):
                    self.cart[idx]['qty'] = new_qty
                    self.update_cart_display()
            except ValueError:
                pass # Ignorar si no es n├║mero
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", lambda e: entry.destroy())
        entry.bind("<Escape>", lambda e: entry.destroy())

    def update_cart_display(self):
        """Refresca la visualizaci├│n del carrito estilo Excel y calcula el total."""
        # Limpiar treeview
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        total = 0
        for i, p in enumerate(self.cart):
            qty = p.get('qty', 1)
            precio = p.get('precio', 0)
            subtotal = qty * precio
            total += subtotal
            self.cart_tree.insert('', 'end', iid=str(i+1), values=(p['nombre'], f"x{qty}", f"${precio:.2f}", f"${subtotal:.2f}"))
        
        self.total_label.config(text=f'Total: ${total:.2f}')

    def process_order(self):
        """Guarda un pedido nuevo o actualiza uno existente si estamos en modo edici├│n."""
        if not self.cart:
            messagebox.showinfo('Aviso', 'El carrito est├í vac├¡o')
            return

        # Si estamos en modo edici├│n, usamos la l├│gica de actualizaci├│n
        if hasattr(self, 'editing_table_id') and self.editing_table_id:
            self.update_existing_order()
            return
        
        # Preparar datos del pedido con cantidades
        items_list = []
        for p in self.cart:
            qty = p.get('qty', 1)
            for _ in range(qty): # Agregar tantas entradas como la cantidad
                items_list.append({'id': p['id'], 'nombre': p['nombre'], 'precio': p['precio'], 'qty': qty})
        
        items = json.dumps(items_list, ensure_ascii=False)
        total = sum((p.get('precio', 0) * p.get('qty', 1)) for p in self.cart)
        subtotal = total
        
        try:
            # Generar n├║mero de pedido ├║nico basado en fecha/hora
            canal = self.order_channel.get()
            # N├║mero m├ís corto y profesional: PG + 8 ├║ltimos d├¡gitos del timestamp
            numero = f"PG-{datetime.now().strftime('%d%H%M%S')}"
            created_at = datetime.now().isoformat()
            usuario_id = self.user.get('id') if self.user else None
            sesion_id = self.session_id
            
            # Insertar en la base de datos
            self.db.execute('INSERT INTO pedidos (numero, items, subtotal, total, estado, canal, usuario_id, sesion_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                            (numero, items, subtotal, total, 'RECIBIDO', canal, usuario_id, sesion_id, created_at))
            
            # Registrar en auditor├¡a
            self.db.audit_log('pedidos', 'INSERT', self.user.get('username'), f'Pedido {canal} creado: {numero}', new=items_list)
            
            messagebox.showinfo('├ëxito', f'Pedido {canal} procesado correctamente')
        except Exception as e:
            logging.error(f'Error al procesar pedido POS: {e}')
            messagebox.showerror('Error', 'No se pudo crear el pedido')
        
        # Limpiar carrito despu├®s de la venta
        self.cart.clear()
        self.update_cart_display()

    def open_caja(self):
        """Inicia una nueva sesi├│n de caja con un monto inicial."""
        if self.session_id:
            messagebox.showinfo('Caja', 'Ya hay una sesi├│n de caja abierta')
            return
        inicial = simpledialog.askfloat('Abrir Caja', 'Monto inicial en caja:', minvalue=0.0)
        if inicial is None: return # El usuario cancel├│ el di├ílogo
        
        usuario_id = self.user.get('id') if self.user else None
        inicio = datetime.now().isoformat()
        try:
            cur = self.db.execute('INSERT INTO caja_sesiones (usuario_id, inicio, inicial, monto_apertura, estado) VALUES (?,?,?,?,?)', 
                                (usuario_id, inicio, inicial, inicial, 'ABIERTO'))
            self.session_id = cur.lastrowid
            messagebox.showinfo('Caja', f'Caja abierta exitosamente (ID {self.session_id})')
        except Exception as e:
            logging.exception(f'Error al abrir caja: {e}')
            messagebox.showerror('Error', 'No se pudo abrir la caja')

    def cerrar_caja(self):
        """Finaliza la sesi├│n de caja, calcula totales y muestra reporte detallado (estilo ticket)."""
        if not self.session_id:
            messagebox.showwarning('Caja', 'No hay sesi├│n de caja abierta')
            return
        
        cierre_at = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        usuario_id = self.user.get('id') if self.user else "N/A"
        usuario_nombre = self.user.get('nombre_completo') if self.user else "Cajero Desconocido"
        
        # Obtener todas las ventas realizadas en esta sesi├│n (CAJA y cobros de MESERO)
        # Filtramos por sesion_id que es el que vincula las ventas a esta apertura de caja
        query = '''
            SELECT numero, total, created_at, metodo_pago, canal 
            FROM pedidos 
            WHERE sesion_id = ? AND pagado = 1
            ORDER BY created_at ASC
        '''
        rows = self.db.fetch_all(query, (self.session_id,))
        
        sum_total = sum(float(r[1] or 0) for r in rows)
        total_tickets = len(rows)

        # Obtener monto inicial
        caja_row = self.db.fetch_one('SELECT inicial FROM caja_sesiones WHERE id = ?', (self.session_id,)) or (0.0,)
        inicial = float(caja_row[0] or 0)
        
        # --- CONSTRUCCI├ôN DEL REPORTE ESTILO TICKET ---
        reporte =  "    ==========================================\n"
        reporte += "    *        ­ƒìò PIK'TA RESTAURANTE ­ƒìò        *\n"
        reporte += "    *       INFORME DE CIERRE DE CAJA        *\n"
        reporte += "    ==========================================\n"
        reporte += f"    Cierre:  {cierre_at}\n"
        reporte += f"Cajero:  ID {usuario_id} - {usuario_nombre}\n"
        reporte += f"Caja:    1\n"
        reporte += f"Sesi├│n:  {self.session_id}\n"
        reporte += "------------------------------------------\n"
        reporte += f"{'TICKET':<15} {'FECHA':<15} {'TOTAL':>10}\n"
        reporte += "------------------------------------------\n"
        
        # Agrupar por m├®todo de pago para totales parciales (opcional pero ├║til)
        por_metodo = {}
        
        for r in rows:
            num, tot, fecha, metodo, canal = r
            metodo = metodo or "EFECTIVO"
            fecha_fmt = datetime.fromisoformat(fecha).strftime('%H:%M:%S') if fecha else "N/A"
            reporte += f"{num[-8:]:<15} {fecha_fmt:<15} {tot:>10.2f}\n"
            por_metodo[metodo] = por_metodo.get(metodo, 0) + float(tot)

        reporte += "------------------------------------------\n"
        for met, val in por_metodo.items():
            reporte += f"Total {met:<15} {val:>20.2f}\n"
            
        reporte += "==========================================\n"
        reporte += f"Monto Inicial:             {inicial:>15.2f}\n"
        reporte += f"Total Ventas Turno:        {sum_total:>15.2f}\n"
        reporte += "------------------------------------------\n"
        reporte += f"TOTAL EN CAJA:             {sum_total + inicial:>15.2f}\n"
        reporte += "==========================================\n"
        reporte += f"N┬║ Total de Tickets:       {total_tickets:>15}\n"
        reporte += "******************************************\n"
        reporte += "      SISTEMA POS PIK'TA - 2026       \n"
        reporte += "******************************************\n"

        try:
            # Actualizar estado de la sesi├│n a CERRADO y guardar reporte
            self.db.execute('UPDATE caja_sesiones SET estado = ?, cierre_total = ?, cierre_at = ?, reporte_texto = ? WHERE id = ?', 
                            ('CERRADO', sum_total, datetime.now().isoformat(), reporte, self.session_id))
            
            # --- IMPRESI├ôN AUTOM├üTICA DEL CIERRE ---
            temp_dir = os.path.join(os.environ.get('TEMP', 'C:\\temp'), 'PiktaInvoices')
            if not os.path.exists(temp_dir): os.makedirs(temp_dir)
            
            base_name = f"cierre_automatico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filename = os.path.join(temp_dir, base_name)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(reporte)
            os.startfile(filename)
            
            messagebox.showinfo('Caja', 'Caja cerrada exitosamente. Reporte generado para impresi├│n.')
        except Exception:
            logging.exception('Error al cerrar caja')

        self.show_report(reporte)
        self.session_id = None

    def show_report(self, text):
        """Muestra una pantalla con el resumen del cierre de caja y permite imprimir."""
        for w in self.products_frame.winfo_children():
            w.destroy()
        frm = ttk.Frame(self.products_frame, padding=20)
        frm.pack(fill='both', expand=True)
        
        ttk.Label(frm, text="REPORTE DE CIERRE", font=(None, 14, 'bold')).pack(pady=5)
        
        t = tk.Text(frm, height=18, width=50, font=("Courier", 10))
        t.insert('1.0', text)
        t.config(state='disabled')
        t.pack(pady=10)
        
        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill='x', pady=10)
        
        def print_report():
            temp_dir = os.path.join(os.environ.get('TEMP', 'C:\\temp'), 'PiktaInvoices')
            if not os.path.exists(temp_dir): os.makedirs(temp_dir)
            
            base_name = f"cierre_caja_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filename = os.path.join(temp_dir, base_name)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text)
            os.startfile(filename)
            messagebox.showinfo("Impresi├│n", "Reporte enviado a imprimir.")

        ttk.Button(btn_frame, text='­ƒû¿ IMPRIMIR REPORTE', command=print_report, bootstyle="success").pack(side='left', padx=5, expand=True)
        ttk.Button(btn_frame, text='Regresar al Men├║', command=self.render_products, bootstyle="info").pack(side='left', padx=5, expand=True)


class MeseroFrame(tk.Canvas):
    """
    Interfaz para Meseros.
    Permite realizar pedidos asignados a mesas o para llevar.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(parent, bg=BG, highlightthickness=0, *args, **kwargs)
        self.db = db
        self.user = user
        self.cart = []
        self.selected_mesa = tk.StringVar(value="Mesa 1")
        
        # Logo de Fondo en Mesero
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        self.last_bg_w, self.last_bg_h = 0, 0
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            self.bg_raw = Image.open(bg_logo_path)
            def draw_mes_bg(e):
                cw, ch = e.width, e.height
                if cw < 10 or ch < 10: return
                if abs(cw - self.last_bg_w) < 20 and abs(ch - self.last_bg_h) < 20: return
                
                self.last_bg_w, self.last_bg_h = cw, ch
                self.delete("bg")
                img_res = self.bg_raw.resize((cw, ch), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(img_res)
                self.create_image(cw//2, ch//2, image=self.bg_photo, tags="bg")
                self.tag_lower("bg")
            self.bind("<Configure>", draw_mes_bg)

        # --- Contenedores para Secciones ---
        # Cabecera
        self.header = ttk.Frame(self, bootstyle="warning", padding=15)
        self.header_win = self.create_window(0, 0, window=self.header, anchor='nw', tags="header")
        
        # Cuerpo
        self.body = ttk.Frame(self, padding=10)
        self.body_win = self.create_window(0, 70, window=self.body, anchor='nw', tags="body")
        
        def resize_mes_content(e):
            self.itemconfig("header", width=e.width)
            self.itemconfig("body", width=e.width, height=e.height - 70)
            if hasattr(self, 'bg_raw'): draw_mes_bg(e)
            
        self.bind("<Configure>", resize_mes_content)

        # --- Contenido de la Cabecera ---
        mesero_img = load_image(os.path.join('Imagenes', 'user.png'), size=(60, 60))
        if mesero_img:
            lbl = ttk.Label(self.header, image=mesero_img, bootstyle="inverse-warning")
            lbl.image = mesero_img
            lbl.pack(side='left', padx=10)
        
        ttk.Label(self.header, text='­ƒì¢´©Å M├ôDULO DE MESERO', font=(None, 24, 'bold'), bootstyle="inverse-warning").pack(side='left', padx=10)
        ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10, takefocus=True).pack(side='right', padx=5)

        # --- Cuerpo ---
        # Lado izquierdo: Mesas y Productos
        left = ttk.Frame(self.body)
        left.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Selecci├│n de Mesa / Para Llevar
        mesa_frame = ttk.LabelFrame(left, text="Seleccionar Mesa / Destino")
        mesa_frame.pack(fill='x', pady=(0, 15), padx=10)
        
        mesas = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Mesa 5", "Mesa 6", "Para Llevar"]
        for m in mesas:
            ttk.Radiobutton(mesa_frame, text=m, variable=self.selected_mesa, value=m, 
                           bootstyle="warning-toolbutton", padding=8).pack(side='left', padx=5)

        # Filtro de categor├¡as
        self.categories = ['­ƒìö Combos', '­ƒìƒ Extras', '­ƒÑñ Bebidas']
        self.selected_category = tk.StringVar(value=self.categories[0])
        cat_frame = ttk.Frame(left)
        cat_frame.pack(fill='x', pady=(0, 15))
        for c in self.categories:
            ttk.Radiobutton(cat_frame, text=c, variable=self.selected_category, value=c, 
                           command=self.render_products, bootstyle="warning-outline-toolbutton", padding=10).pack(side='left', padx=5)

        # Contenedor de productos
        self.products_canvas = tk.Canvas(left, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(left, orient="vertical", command=self.products_canvas.yview)
        self.products_frame = ttk.Frame(self.products_canvas)

        self.products_frame.bind("<Configure>", lambda e: self.products_canvas.configure(scrollregion=self.products_canvas.bbox("all")))
        self.products_canvas.create_window((0, 0), window=self.products_frame, anchor="nw")
        self.products_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.products_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Lado derecho: Resumen
        right = ttk.Frame(self.body, width=350, bootstyle="secondary")
        right.pack(side='right', fill='y')
        right.pack_propagate(False)
        
        ttk.Label(right, text='PEDIDO ACTUAL', font=(None, 12, 'bold'), bootstyle="inverse-secondary", padding=10).pack(fill='x')
        self.cart_list = tk.Listbox(right, bg=PANEL, fg=FG, font=(None, 11), bd=0, highlightthickness=0, selectbackground=ACCENT)
        self.cart_list.pack(fill='both', expand=True, padx=10, pady=10)
        self.total_label = ttk.Label(right, text='Total: $0.00', font=(None, 14, 'bold'), bootstyle="inverse-secondary", padding=10)
        self.total_label.pack(fill='x')

        ttk.Button(right, text='Quitar Item', command=self.remove_selected, bootstyle="danger", cursor="hand2").pack(fill='x', padx=10, pady=5)
        ttk.Button(right, text='ENVIAR A COCINA', command=self.process_order, bootstyle="warning", cursor="hand2", padding=10).pack(fill='x', padx=10, pady=10)

        self.render_products()

    def render_products(self):
        for w in self.products_frame.winfo_children(): w.destroy()
        products = self.db.fetch_all('SELECT id, nombre, precio, categoria, emoji FROM productos_menu')
        filtered = [p for p in products if (p[3] or '').strip() == self.selected_category.get()]
        
        cols = 3
        product_btns = []
        for idx, p in enumerate(filtered):
            r, c = divmod(idx, cols)
            card = ttk.Frame(self.products_frame, bootstyle="light", padding=15)
            card.grid(row=r, column=c, padx=12, pady=12, sticky='nsew')
            ttk.Label(card, text=p[4] or '­ƒì¢', font=(None, 40), bootstyle="inverse-light").pack(pady=5)
            ttk.Label(card, text=p[1], font=(None, 14, 'bold'), bootstyle="inverse-light", wraplength=140, justify='center').pack()
            ttk.Label(card, text=f"${p[2]:.2f}", font=(None, 16), bootstyle="warning").pack(pady=5)
            btn = ttk.Button(card, text='A├▒adir', command=lambda pid=p: self.add_product(pid), bootstyle="warning", cursor="hand2", padding=8, takefocus=True)
            btn.pack(fill='x')
            # btn.bind('<Return>', lambda e, pid=p: self.add_product(pid)) # Redundante con global handler
            product_btns.append(btn)

            # Navegaci├│n por flechas entre botones de productos
            def make_mesero_nav(idx):
                def nav(e):
                    if e.keysym == 'Left' and idx > 0: product_btns[idx-1].focus_set()
                    elif e.keysym == 'Right' and idx < len(product_btns)-1: product_btns[idx+1].focus_set()
                    elif e.keysym == 'Up' and idx >= cols: product_btns[idx-cols].focus_set()
                    elif e.keysym == 'Down' and idx + cols < len(product_btns): product_btns[idx+cols].focus_set()
                return nav
            
            btn.bind("<Left>", make_mesero_nav(idx))
            btn.bind("<Right>", make_mesero_nav(idx))
            btn.bind("<Up>", make_mesero_nav(idx))
            btn.bind("<Down>", make_mesero_nav(idx))
            
        for i in range(cols): self.products_frame.columnconfigure(i, weight=1)

    def add_product(self, product):
        self.cart.append(product)
        self.update_cart_display()

    def remove_selected(self):
        sel = self.cart_list.curselection()
        if not sel: return
        del self.cart[sel[0]]
        self.update_cart_display()

    def update_cart_display(self):
        self.cart_list.delete(0, 'end')
        total = sum(p[2] for p in self.cart)
        for p in self.cart:
            self.cart_list.insert('end', f"{p[1]:<20} ${p[2]:>6.2f}")
        self.total_label.config(text=f'Total: ${total:.2f}')

    def process_order(self):
        if not self.cart:
            messagebox.showinfo('Aviso', 'El pedido est├í vac├¡o')
            return
        
        items_list = [{'id': p[0], 'nombre': p[1], 'precio': p[2]} for p in self.cart]
        items = json.dumps(items_list, ensure_ascii=False)
        total = sum(p[2] for p in self.cart)
        mesa = self.selected_mesa.get()
        
        try:
            # N├║mero profesional: PG-M- + 8 d├¡gitos del timestamp
            numero = f"PG-M-{datetime.now().strftime('%d%H%M%S')}"
            created_at = datetime.now().isoformat()
            usuario_id = self.user.get('id') if self.user else None
            
            # Los pedidos de mesero se guardan como NO PAGADOS para que caja los cobre luego
            self.db.execute('INSERT INTO pedidos (numero, items, subtotal, total, estado, canal, usuario_id, created_at, mesa, pagado) VALUES (?,?,?,?,?,?,?,?,?,?)',
                            (numero, items, total, total, 'RECIBIDO', 'MESERO', usuario_id, created_at, mesa, 0))
            
            messagebox.showinfo('├ëxito', f'Pedido de {mesa} enviado a cocina')
            self.cart.clear()
            self.update_cart_display()
        except Exception as e:
            logging.error(f'Error al procesar pedido mesero: {e}')
            messagebox.showerror('Error', 'No se pudo enviar el pedido')


class KDSFrame(tk.Canvas):
    """
    Monitor de Cocina (KDS).
    Visualiza los pedidos pendientes y permite marcarlos como listos.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(parent, bg=BG, highlightthickness=0, *args, **kwargs)
        self.db = db
        self.user = user
        self.last_order_count = 0
        self.confirm_finish = set() # IDs de pedidos en modo confirmaci├│n de finalizar
        
        # Logo de Fondo en KDS
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        self.last_bg_w, self.last_bg_h = 0, 0
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            self.bg_raw = Image.open(bg_logo_path)
            def draw_kds_bg(e):
                cw, ch = e.width, e.height
                if cw < 10 or ch < 10: return
                if abs(cw - self.last_bg_w) < 20 and abs(ch - self.last_bg_h) < 20: return
                
                self.last_bg_w, self.last_bg_h = cw, ch
                self.delete("bg")
                img_res = self.bg_raw.resize((cw, ch), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(img_res)
                self.create_image(cw//2, ch//2, image=self.bg_photo, tags="bg")
                self.tag_lower("bg")
            self.bind("<Configure>", draw_kds_bg)

        # --- Contenedores para Secciones ---
        self.header = ttk.Frame(self, bootstyle="warning", padding=15)
        self.header_win = self.create_window(0, 0, window=self.header, anchor='nw', tags="header")
        
        # Guardar referencia al bot├│n para el atajo de teclado
        self.btn_back = ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10, takefocus=True)
        self.btn_back.pack(side='right', padx=5)
        
        ttk.Button(self.header, text='Refrescar', command=self.refresh, bootstyle="light-outline", cursor="hand2", padding=10, takefocus=True).pack(side='right', padx=5)
        
        self.body = ttk.Frame(self, padding=10)
        self.body_win = self.create_window(0, 70, window=self.body, anchor='nw', tags="body")
        
        def resize_kds_content(e):
            self.itemconfig("header", width=e.width)
            self.itemconfig("body", width=e.width, height=e.height - 70)
            if hasattr(self, 'bg_raw'): draw_kds_bg(e)
            
        self.bind("<Configure>", resize_kds_content)

        # --- Contenido de la Cabecera ---
        kds_img = load_image(os.path.join('Imagenes', 'cocina.jpeg'), size=(60,60))
        if kds_img:
            lbl = ttk.Label(self.header, image=kds_img, bootstyle="inverse-warning")
            lbl.image = kds_img
            lbl.pack(side='left', padx=10)
            
        ttk.Label(self.header, text='­ƒì│ MONITOR DE COCINA (KDS)', font=(None, 24, 'bold'), bootstyle="inverse-warning").pack(side='left', padx=10)
        
        # --- Instrucciones ---
        instr = ttk.Label(self.header, text="TAB: Navegar / ENTER: Iniciar o Finalizar", font=(None, 12, 'italic'), bootstyle="inverse-warning")
        instr.pack(side='left', padx=20)

        # --- ├ürea de Pedidos Scrolleable ---
        # Usamos un Canvas con un Frame interno para las tarjetas
        self.kds_canvas = tk.Canvas(self.body, bg=BG, highlightthickness=0)
        self.kds_scrollbar = ttk.Scrollbar(self.body, orient="vertical", command=self.kds_canvas.yview)
        self.cards_container = ttk.Frame(self.kds_canvas, bootstyle="dark")
        
        self.kds_canvas.create_window((0, 0), window=self.cards_container, anchor="nw", tags="inner_frame")
        self.kds_canvas.configure(yscrollcommand=self.kds_scrollbar.set)
        
        self.kds_scrollbar.pack(side="right", fill="y")
        self.kds_canvas.pack(side="left", fill="both", expand=True)
        
        def on_frame_configure(e):
            self.kds_canvas.configure(scrollregion=self.kds_canvas.bbox("all"))
            # Forzar el ancho del frame interno al del canvas
            self.kds_canvas.itemconfig("inner_frame", width=self.kds_canvas.winfo_width())

        self.cards_container.bind("<Configure>", on_frame_configure)
        self.kds_canvas.bind("<Configure>", lambda e: self.kds_canvas.itemconfig("inner_frame", width=e.width))

        self.refresh()

    def refresh(self):
        """Consulta la base de datos y renderiza tarjetas para cada pedido activo (estilo WEB)."""
        # Guardar qu├® ID ten├¡a el foco antes de limpiar
        focused_widget = self.focus_get()
        
        # Si el foco est├í en un bot├│n del header, no lo movemos al refrescar
        is_header_focused = False
        if focused_widget and focused_widget.master == self.header:
            is_header_focused = True
            
        last_focused_id = getattr(focused_widget, '_order_id', None) if focused_widget else None

        # Limpiar tarjetas actuales
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        # Traer pedidos que NO tengan estado 'LISTO'
        rows = self.db.fetch_all("SELECT id, numero, items, estado, mesa, created_at FROM pedidos WHERE estado NOT IN ('LISTO', 'CANCELADO') ORDER BY id ASC LIMIT 50")
        
        # Reproducir sonido si hay pedidos nuevos
        if len(rows) > self.last_order_count:
            play_sound_new_order()
        self.last_order_count = len(rows)
        
        if not rows:
            ttk.Label(self.cards_container, text="No hay pedidos activos en cocina.", font=(None, 16), bootstyle="inverse-dark").pack(pady=50)
            return

        # Grid de tarjetas (3 columnas)
        cols = 3
        first_btn = None
        target_btn = None

        for idx, r in enumerate(rows):
            row, col = divmod(idx, cols)
            pid, num, items_json, estado, mesa, fecha = r
            
            # Determinar color seg├║n estado (estilo web)
            # RECIBIDO -> Azul (info) - "EN PROCESO" -> Naranja (warning) - LISTO -> Verde
            if estado == 'RECIBIDO':
                card_style = "info"
                btn_text = "­ƒÜÇ INICIAR PREPARACI├ôN (15 min)"
                btn_style = "warning"
            elif estado == 'EN PROCESO':
                card_style = "warning"
                # Si est├í en modo confirmaci├│n, cambiar texto
                if pid in self.confirm_finish:
                    btn_text = "Ô£à FINALIZAR Y ENTREGAR"
                    btn_style = "success"
                else:
                    btn_text = "­ƒæ®ÔÇì­ƒì│ EN PROCESO (CLICK AL TERMINAR)"
                    btn_style = "warning"
            else:
                continue # No mostrar otros estados
            
            # Crear la tarjeta (Frame)
            card = ttk.Frame(self.cards_container, bootstyle="secondary", padding=2)
            card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            
            # Header de la tarjeta
            header = ttk.Frame(card, bootstyle=card_style, padding=10)
            header.pack(fill='x')
            
            ttk.Label(header, text=f"#{pid}", font=(None, 18, 'bold'), bootstyle=f"inverse-{card_style}").pack(side='left')
            ttk.Label(header, text=f"MESA: {mesa if mesa else 'CAJA'}", font=(None, 12, 'bold'), bootstyle=f"inverse-{card_style}").pack(side='right')
            
            # Cuerpo de la tarjeta (Items)
            body = ttk.Frame(card, bootstyle="light", padding=15)
            body.pack(fill='both', expand=True)
            
            try:
                items_list = json.loads(items_json) if items_json else []
                for it in items_list:
                    it_frame = ttk.Frame(body, bootstyle="light")
                    it_frame.pack(fill='x', pady=2)
                    ttk.Label(it_frame, text=f"ÔÇó {it.get('nombre')}", font=(None, 13), bootstyle="inverse-light").pack(side='left')
                    ttk.Label(it_frame, text=f"x{it.get('qty', 1)}", font=(None, 13, 'bold'), bootstyle="info").pack(side='right')
            except:
                ttk.Label(body, text=items_json, font=(None, 11), wraplength=200).pack()
            
            # Footer con bot├│n de acci├│n (Focusable para TAB)
            footer = ttk.Frame(card, bootstyle="light", padding=10)
            footer.pack(fill='x')
            
            # El bot├│n captura el foco TAB y ENTER (ya manejado globalmente por App._on_global_return)
            btn = ttk.Button(footer, text=btn_text, bootstyle=btn_style, cursor="hand2", 
                            command=lambda p=pid: self.advance_order_state_by_id(p))
            btn.pack(fill='x', ipady=10)
            btn._order_id = pid # Guardar ID para persistencia de foco
            
            # Forzar el foco si es el bot├│n que buscamos
            if pid == last_focused_id: target_btn = btn
            if not first_btn: first_btn = btn
            
            # ELIMINADO: btn.bind('<Return>') para evitar doble ejecuci├│n con el manejador global
            
            # Efecto visual de foco para toda la tarjeta
            def on_btn_focus(e, c=card):
                c.configure(bootstyle="primary") 
            
            def on_btn_blur(e, c=card):
                c.configure(bootstyle="secondary")
            
            btn.bind("<FocusIn>", on_btn_focus)
            btn.bind("<FocusOut>", on_btn_blur)


        # Configurar peso de columnas del grid
        for i in range(cols):
            self.cards_container.columnconfigure(i, weight=1)

        # Restaurar foco de forma inteligente
        if is_header_focused:
            # Mantener foco en el header
            if focused_widget: focused_widget.focus_set()
        elif target_btn:
            target_btn.focus_set()
        elif first_btn:
            # Si el pedido que ten├¡a el foco ya no est├í (porque se complet├│), ir al primero
            first_btn.focus_set()

        # Configurar peso de columnas del grid
        for i in range(cols):
            self.cards_container.columnconfigure(i, weight=1)

    def advance_order_state_by_id(self, pid):
        """Avanza el estado de un pedido espec├¡fico por su ID: RECIBIDO -> EN PROCESO -> LISTO."""
        try:
            # Obtener estado actual
            with self.db.get_connection() as conn:
                res = conn.execute("SELECT estado FROM pedidos WHERE id=?", (pid,)).fetchone()
                if not res: return
                current_state = res[0].upper()

                if current_state == 'RECIBIDO':
                    new_state = 'EN PROCESO'
                    conn.execute('UPDATE pedidos SET estado=? WHERE id=?', (new_state, pid))
                elif current_state == 'EN PROCESO':
                    # Si no estaba en modo confirmaci├│n, activarlo
                    if pid not in self.confirm_finish:
                        self.confirm_finish.add(pid)
                        conn.commit()
                        self.refresh()
                        return
                    
                    # Si ya estaba en modo confirmaci├│n, proceder a finalizar
                    new_state = 'LISTO'
                    conn.execute('UPDATE pedidos SET estado=? WHERE id=?', (new_state, pid))
                    if pid in self.confirm_finish: self.confirm_finish.remove(pid)
                    # El sonido se dispara aqu├¡ al finalizar
                    play_sound_order_ready()
                else:
                    return 
                conn.commit()
            
            # Forzar refresco visual total para actualizar colores y botones
            self.refresh()
        except Exception as e:
            logging.error(f"Error en KDS advance_order_state_by_id: {str(e)}")
            play_sound_error()

    def advance_order_state(self):
        """Mantenemos por compatibilidad, pero ahora usamos advance_order_state_by_id."""
        pass

    def mark_ready(self):
        """Mantenemos por compatibilidad."""
        pass

class WhatsAppFrame(tk.Canvas):
    """
    M├│dulo de WhatsApp Business PIK'TA.
    Se abre autom├íticamente en una ventana profesional integrada.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(parent, bg=BG, highlightthickness=0, *args, **kwargs)
        self.db = db
        self.user = user
        self.wa_process = None
        
        # Logo de Fondo en WhatsApp
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            self.bg_raw = Image.open(bg_logo_path)
            self.last_bg_w, self.last_bg_h = 0, 0
            def draw_wa_bg(e):
                cw, ch = e.width, e.height
                if cw < 10 or ch < 10: return
                if cw == self.last_bg_w and ch == self.last_bg_h: return
                self.last_bg_w, self.last_bg_h = cw, ch
                self.delete("bg")
                img_res = self.bg_raw.resize((cw, ch), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(img_res)
                self.create_image(cw//2, ch//2, image=self.bg_photo, tags="bg")
                self.tag_lower("bg")
            self.bind("<Configure>", draw_wa_bg)

        # --- Contenedores para Secciones ---
        self.header = ttk.Frame(self, bootstyle="success", padding=15)
        self.header_win = self.create_window(0, 0, window=self.header, anchor='nw', tags="header")
        
        self.body = ttk.Frame(self, padding=10)
        self.body_win = self.create_window(0, 70, window=self.body, anchor='nw', tags="body")
        
        def resize_wa_content(e):
            self.itemconfig("header", width=e.width)
            self.itemconfig("body", width=e.width, height=e.height - 70)
            if hasattr(self, 'bg_raw'): draw_wa_bg(e)
            
        self.bind("<Configure>", resize_wa_content)

        # --- Contenido de la Cabecera ---
        wa_img = load_image(os.path.join('Imagenes', 'WhatsApp.jpg'), size=(60, 60))
        if wa_img:
            lbl = ttk.Label(self.header, image=wa_img, bootstyle="inverse-success")
            lbl.image = wa_img
            lbl.pack(side='left', padx=10)
        
        ttk.Label(self.header, text='­ƒÆ¼ WHATSAPP BUSINESS PIK\'TA', font=(None, 24, 'bold'), bootstyle="inverse-success").pack(side='left', padx=10)
        ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10).pack(side='right', padx=5)

        # --- Cuerpo Informativo ---
        info_container = tk.Frame(self.body, bg=BG)
        info_container.place(relx=0.5, rely=0.5, anchor='center')
        
        ttk.Label(info_container, text="WhatsApp Business se est├í ejecutando de forma integrada.", 
                 font=(None, 16, 'bold'), bootstyle="inverse-dark").pack(pady=10)
        ttk.Label(info_container, text="Gestione sus pedidos y clientes desde la ventana profesional de WhatsApp.", 
                 font=(None, 12), bootstyle="inverse-dark").pack(pady=5)
        
        ttk.Button(info_container, text='REABRIR WHATSAPP INTEGRADO', bootstyle="success", 
                  command=self.connect_wa, padding=15).pack(pady=20)
        
        # --- PRUEBA DE SONIDOS ---
        test_frame = ttk.LabelFrame(info_container, text="Pruebas de Sonido del Sistema")
        test_frame.pack(pady=10, fill='x')
        
        # Usamos un frame interno para el padding ya que LabelFrame no lo soporta directamente en algunas versiones
        inner_test = ttk.Frame(test_frame, padding=10)
        inner_test.pack(fill='both', expand=True)
        
        ttk.Button(inner_test, text="­ƒöö Probar Nuevo Pedido", command=play_sound_new_order, bootstyle="info-outline").pack(side='left', padx=5)
        ttk.Button(inner_test, text="­ƒôó Probar Pedido Listo", command=play_sound_order_ready, bootstyle="warning-outline").pack(side='left', padx=5)
        ttk.Button(inner_test, text="ÔØî Probar Error", command=play_sound_error, bootstyle="danger-outline").pack(side='left', padx=5)

    def connect_wa(self):
        """Abre WhatsApp Web de forma integrada y silenciosa, evitando duplicados."""
        try:
            # Verificar si ya hay un proceso en ejecuci├│n
            if self.wa_process and self.wa_process.poll() is None:
                # El proceso sigue vivo, no lanzar otro
                logging.info("WhatsApp ya est├í abierto o conectando...")
                return

            script_path = os.path.join(os.getcwd(), 'whatsapp_launcher.py')
            if os.path.exists(script_path):
                import subprocess
                # CREATE_NO_WINDOW (0x08000000) evita el CMD negro
                # DETACHED_PROCESS (0x00000008) asegura independencia total
                self.wa_process = subprocess.Popen([sys.executable, script_path], 
                               creationflags=0x08000008, 
                               close_fds=True)
            else:
                webbrowser.open("https://web.whatsapp.com/")
        except Exception as e:
            logging.error(f"Error al lanzar WhatsApp silencioso: {e}")
            webbrowser.open("https://web.whatsapp.com/")

class AdminFrame(tk.Canvas):
    """
    Panel de Administraci├│n con sistema de tarjetas similar al principal.
    Permite gestionar el inventario, usuarios y seguridad.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(parent, bg=BG, highlightthickness=0, *args, **kwargs)
        self.db = db
        self.user = user
        
        # Logo de Fondo en Admin
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            self.bg_raw = Image.open(bg_logo_path)
            self.last_bg_w, self.last_bg_h = 0, 0
            def draw_adm_bg(e):
                cw, ch = e.width, e.height
                if cw < 10 or ch < 10: return
                # Solo redibujar si el cambio es significativo (>20px) para evitar lentitud
                if abs(cw - self.last_bg_w) < 20 and abs(ch - self.last_bg_h) < 20: return
                
                self.last_bg_w, self.last_bg_h = cw, ch
                self.delete("bg")
                img_res = self.bg_raw.resize((cw, ch), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(img_res)
                self.create_image(cw//2, ch//2, image=self.bg_photo, tags="bg")
                self.tag_lower("bg")
            self.bind("<Configure>", draw_adm_bg)

        # --- Contenedores para Secciones ---
        self.header = ttk.Frame(self, bootstyle="success", padding=15)
        self.header_win = self.create_window(0, 0, window=self.header, anchor='nw', tags="header")
        
        self.body = ttk.Frame(self, padding=10)
        self.body_win = self.create_window(0, 70, window=self.body, anchor='nw', tags="body")
        
        def resize_adm_content(e):
            self.itemconfig("header", width=e.width)
            self.itemconfig("body", width=e.width, height=e.height - 70)
            if hasattr(self, 'bg_raw'): draw_adm_bg(e)
            
        self.bind("<Configure>", resize_adm_content)

        # --- Contenido de la Cabecera ---
        img = load_image(os.path.join('Imagenes', 'admin.jpeg'), size=(60,60))
        if img:
            lbl = ttk.Label(self.header, image=img, bootstyle="inverse-success")
            lbl.image = img
            lbl.pack(side='left', padx=10)

        self.title_lbl = ttk.Label(self.header, text='­ƒôè PANEL DE ADMINISTRACI├ôN', font=(None, 24, 'bold'), bootstyle="inverse-success")
        self.title_lbl.pack(side='left', padx=10)
        
        self.btn_back_main = ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="light-outline", cursor="hand2", padding=10, takefocus=True)
        self.btn_back_main.pack(side='right', padx=5)
        # self.btn_back_main.bind('<Return>', lambda e: self.master.select(0)) # Redundante
        
        self.btn_back_admin = ttk.Button(self.header, text='Volver al Admin', command=self.show_admin_menu, bootstyle="light-outline", cursor="hand2", padding=10, takefocus=True)
        # self.btn_back_admin.bind('<Return>', lambda e: self.show_admin_menu()) # Redundante

        # --- Contenedor Principal con Notebook Oculto en el cuerpo ---
        self.notebook = ttk.Notebook(self.body, style='Hidden.TNotebook')
        self.notebook.pack(fill='both', expand=True)

        # 1. Pesta├▒a del Men├║ de Tarjetas (Cuadritos)
        self.menu_frame = ttk.Frame(self.notebook, padding=30)
        self.notebook.add(self.menu_frame, text='Men├║ Admin')
        self.setup_admin_menu()

        # 2. Pesta├▒a de Inventario
        self.inv_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.inv_frame, text='Inventario')

        # 3. Pesta├▒a de Usuarios
        self.users_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.users_frame, text='Usuarios')

        # 4. Pesta├▒a de Seguridad
        self.security_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.security_frame, text='Seguridad')

        # 5. Pesta├▒a de Men├║ / Productos
        self.products_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.products_frame, text='Men├║ / Productos')

        # 6. Pesta├▒a de Historial de Cierres
        self.cierre_history_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.cierre_history_frame, text='Historial de Cierres')

        self.show_admin_menu() # Mostrar el men├║ de cuadritos al inicio

    def setup_admin_menu(self):
        """Crea el dashboard interno de administraci├│n con un dise├▒o profesional, limpio y con scroll."""
        for w in self.menu_frame.winfo_children():
            w.destroy()

        # --- CONTENEDOR CON SCROLL ---
        canvas = tk.Canvas(self.menu_frame, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.menu_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def configure_canvas(event):
            # Hacer que el frame interno tenga el mismo ancho que el canvas
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", configure_canvas)

        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # --- CONTENIDO DEL DASHBOARD ---
        main_container = ttk.Frame(scrollable_frame, padding=40)
        main_container.pack(fill='both', expand=True)

        # T├¡tulo decorativo interno
        ttk.Label(main_container, text="Panel de Gesti├│n Administrativa", font=(None, 24, 'bold'), bootstyle="light").pack(pady=(0, 40), anchor='w')

        # Grid para las tarjetas
        cards_wrap = ttk.Frame(main_container)
        cards_wrap.pack(fill='x', expand=True)

        def make_admin_card(parent, img_name, title, desc, cmd, color="success"):
            # Aumento de tama├▒o para una mejor apreciaci├│n (Dashboard Moderno)
            card = ttk.Frame(parent, bootstyle="secondary", padding=2, cursor="hand2", takefocus=True, width=320, height=360)
            card.pack_propagate(False)

            inner = ttk.Frame(card, padding=25)
            inner.pack(fill='both', expand=True)

            img = None
            if img_name:
                path = os.path.join('Imagenes', img_name)
                img = load_image(path, size=(140, 140)) # Im├ígenes m├ís grandes

            if img:
                lbl = ttk.Label(inner, image=img)
                lbl.image = img
                lbl.pack(pady=10)
            else:
                emoji = '­ƒôª'
                if 'Usuarios' in title: emoji = '­ƒæÑ'
                if 'Seguridad' in title: emoji = '­ƒøí´©Å'
                ttk.Label(inner, text=emoji, font=(None, 70)).pack(pady=10)

            ttk.Label(inner, text=title, font=(None, 22, 'bold'), wraplength=280, justify='center').pack(pady=10)
            ttk.Label(inner, text=desc, wraplength=260, justify='center', font=(None, 12), bootstyle="secondary").pack(pady=5, fill='both', expand=True)

            def on_enter(e):
                card.configure(bootstyle=color, padding=4)
                inner.configure(bootstyle="light")
            def on_leave(e):
                card.configure(bootstyle="secondary", padding=2)
                inner.configure(bootstyle="default")

            for widget in (card, inner):
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)
                widget.bind("<Button-1>", lambda e: cmd())
                widget.bind("<Return>", lambda e: cmd())
            
            return card

        admin_cards = []
        role = (self.user.get('rol') or '').lower() if self.user else 'admin'

        all_configs = [
            ('inventario.jpg', 'Inventario', 'Control de stock y materia prima.', lambda: self.open_section(1, "GESTI├ôN DE INVENTARIO"), "success", ('administrador', 'admin', 'supervisor')),
            ('user.png', 'Usuarios', 'Gesti├│n de personal y accesos.', lambda: self.open_section(2, "GESTI├ôN DE USUARIOS"), "info", ('administrador', 'admin')),
            ('seguridad.png', 'Seguridad', 'Auditor├¡a y respaldos de DB.', lambda: self.open_section(3, "SEGURIDAD Y AUDITOR├ìA"), "warning", ('administrador', 'admin')),
            ('pos.png', 'Men├║ / Productos', 'Gesti├│n de productos y precios.', lambda: self.open_section(4, "GESTI├ôN DE MEN├Ü"), "primary", ('administrador', 'admin', 'supervisor')),
            ('efectivo.jpeg', 'Cierres de Caja', 'Historial de reportes de cierre.', lambda: self.open_section(5, "HISTORIAL DE CIERRES"), "success", ('administrador', 'admin', 'supervisor'))
        ]

        visible_configs = [c for c in all_configs if role in c[5]]

        for i, (img, title, desc, cmd, color, roles) in enumerate(visible_configs):
            row, col = divmod(i, 3)
            card = make_admin_card(cards_wrap, img, title, desc, cmd, color)
            card.grid(row=row, column=col, padx=25, pady=25)
            admin_cards.append(card)

        for i in range(3):
            cards_wrap.columnconfigure(i, weight=1)

        # --- SECCI├ôN DE HERRAMIENTAS SIEMPRE VISIBLE AL FINAL ---
        ttk.Separator(main_container, orient='horizontal').pack(fill='x', pady=50)
        self.setup_admin_tools(main_container)

    def setup_cierre_history(self):
        """Configura la pesta├▒a para ver el historial de cierres de caja."""
        for w in self.cierre_history_frame.winfo_children():
            w.destroy()

        # Logo Pik'ta en la cabecera
        logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(logo_path):
            img = load_image(logo_path, size=(80, 80))
            if img:
                lbl = ttk.Label(self.cierre_history_frame, image=img)
                lbl.image = img
                lbl.pack(pady=5)

        ttk.Label(self.cierre_history_frame, text="­ƒôè HISTORIAL DE CIERRES DE CAJA", font=(None, 18, 'bold')).pack(pady=10)

        main_c = ttk.Frame(self.cierre_history_frame)
        main_c.pack(fill='both', expand=True)

        # Lista de cierres (Lado Izquierdo)
        left = ttk.Frame(main_c, width=300)
        left.pack(side='left', fill='y', padx=10)

        ttk.Label(left, text="Seleccione un Cierre:", font=(None, 11, 'bold')).pack(pady=5)

        self.cierre_list = ttk.Treeview(left, columns=('ID', 'Fecha', 'Total'), show='headings', height=15)
        self.cierre_list.heading('ID', text='ID')
        self.cierre_list.heading('Fecha', text='Fecha')
        self.cierre_list.heading('Total', text='Total')
        self.cierre_list.column('ID', width=50)
        self.cierre_list.column('Fecha', width=150)
        self.cierre_list.column('Total', width=80)
        self.cierre_list.pack(fill='both', expand=True)

        # Vista del Reporte (Lado Derecho)
        right = ttk.Frame(main_c)
        right.pack(side='right', fill='both', expand=True, padx=10)

        ttk.Label(right, text="Vista del Reporte:", font=(None, 11, 'bold')).pack(pady=5)
        self.cierre_view = tk.Text(right, font=("Courier", 11), bg="#f0f0f0", state='disabled')
        self.cierre_view.pack(fill='both', expand=True)

        def on_cierre_select(e):
            sel = self.cierre_list.selection()
            if not sel: return
            cid = self.cierre_list.item(sel[0])['values'][0]

            res = self.db.fetch_one("SELECT reporte_texto FROM caja_sesiones WHERE id = ?", (cid,))
            if res:
                self.cierre_view.config(state='normal')
                self.cierre_view.delete('1.0', 'end')
                self.cierre_view.insert('1.0', res[0] or "Sin texto de reporte")
                self.cierre_view.config(state='disabled')

        self.cierre_list.bind('<<TreeviewSelect>>', on_cierre_select)

        # Botones de Acci├│n
        btn_f = ttk.Frame(self.cierre_history_frame)
        btn_f.pack(fill='x', pady=10)

        ttk.Button(btn_f, text="­ƒöä ACTUALIZAR LISTA", command=self.refresh_cierres, bootstyle="info").pack(side='left', padx=10)

        def print_historical():
            txt = self.cierre_view.get('1.0', 'end-1c')
            if not txt.strip():
                messagebox.showwarning("Aviso", "Seleccione un cierre primero.")
                return
            
            temp_dir = os.path.join(os.environ.get('TEMP', 'C:\\temp'), 'PiktaInvoices')
            if not os.path.exists(temp_dir): os.makedirs(temp_dir)
            
            base_name = f"cierre_historial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filename = os.path.join(temp_dir, base_name)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(txt)
            os.startfile(filename)
            messagebox.showinfo("Impresi├│n", "Reporte enviado a imprimir.")

        ttk.Button(btn_f, text="­ƒû¿ IMPRIMIR SELECCIONADO", command=print_historical, bootstyle="success").pack(side='left', padx=10)

        self.refresh_cierres()

    def refresh_cierres(self):
        """Actualiza la lista de cierres de caja."""
        if hasattr(self, 'cierre_list'):
            self.cierre_list.delete(*self.cierre_list.get_children())
            rows = self.db.fetch_all("SELECT id, cierre_at, cierre_total FROM caja_sesiones WHERE estado='CERRADO' ORDER BY id DESC")
            for r in rows:
                fecha = datetime.fromisoformat(r[1]).strftime('%d/%m/%Y %H:%M') if r[1] else "N/A"
                self.cierre_list.insert('', 'end', values=(r[0], fecha, f"${r[2]:.2f}"))

    def setup_admin_tools(self, parent):
        """Herramientas especiales para el administrador con un dise├▒o destacado."""
        tools_frame = ttk.Frame(parent, padding=(0, 40, 0, 0))
        tools_frame.pack(fill='x', side='bottom')

        # L├¡nea divisoria
        ttk.Separator(tools_frame, orient='horizontal').pack(fill='x', pady=20)

        ttk.Label(tools_frame, text="­ƒøá´©Å Herramientas de Mantenimiento Avanzado", font=(None, 14, 'bold'), bootstyle="secondary").pack(anchor='w', padx=10, pady=(0, 15))
        
        btn_container = ttk.Frame(tools_frame)
        btn_container.pack(fill='x')
        
        # Botones con iconos y estilos claros
        btn_clear = ttk.Button(btn_container, text="­ƒº╣ LIMPIAR PEDIDOS (REINICIAR COCINA)", 
                  command=self.clear_all_orders, bootstyle="danger", padding=12)
        btn_clear.pack(side='left', padx=10)
        
        btn_reset = ttk.Button(btn_container, text="­ƒôª REINICIAR INVENTARIO A CERO", 
                  command=self.reset_inventory, bootstyle="warning", padding=12)
        btn_reset.pack(side='left', padx=10)
        
        btn_backup = ttk.Button(btn_container, text="­ƒÆ¥ CREAR RESPALDO DE SEGURIDAD (BACKUP)", 
                  command=self.manual_backup, bootstyle="success", padding=12)
        btn_backup.pack(side='left', padx=10)

        ttk.Label(tools_frame, text="Nota: Estas acciones son irreversibles. Use con precauci├│n.", font=(None, 9, 'italic'), bootstyle="muted").pack(anchor='w', padx=15, pady=10)

    def clear_all_orders(self):
        """Elimina todos los pedidos de la base de datos para empezar de cero."""
        if messagebox.askyesno("Confirmar Limpieza", "┬┐Est├í seguro de eliminar TODOS los pedidos? Esta acci├│n no se puede deshacer."):
            try:
                with self.db.get_connection() as conn:
                    conn.execute("DELETE FROM pedidos")
                messagebox.showinfo("├ëxito", "Todos los pedidos han sido eliminados. La cocina est├í limpia.")
                # Si hay una instancia de KDS abierta, refrescarla si es posible
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo limpiar los pedidos: {e}")

    def reset_inventory(self):
        """Reinicia los valores de inventario a cero."""
        if messagebox.askyesno("Confirmar Reinicio", "┬┐Desea poner todas las existencias de inventario en cero?"):
            try:
                with self.db.get_connection() as conn:
                    conn.execute("UPDATE inventario SET cantidad = 0")
                messagebox.showinfo("├ëxito", "Inventario reiniciado correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo reiniciar el inventario: {e}")

    def open_section(self, index, title):
        """Abre una secci├│n espec├¡fica y actualiza la cabecera de forma instant├ínea."""
        # 1. Carga perezosa ultra-r├ípida
        if index == 1 and not hasattr(self, 'inv_tree'): self.setup_inventory()
        elif index == 2 and not hasattr(self, 'user_tree'): self.setup_users()
        elif index == 3 and not hasattr(self, 'audit_tree'): self.setup_security()
        elif index == 4 and not hasattr(self, 'menu_tree'): self.setup_menu()
        elif index == 5 and not hasattr(self, 'cierre_list'): self.setup_cierre_history()

        # 2. Cambiar de pesta├▒a inmediatamente
        self.notebook.select(index)
        self.title_lbl.config(text=f"­ƒôè {title}")
        self.btn_back_main.pack_forget()
        self.btn_back_admin.pack(side='right', padx=5)
        
        # 3. Refrescar SOLO los datos necesarios para evitar retrasos
        if index == 1: self.refresh_inventory()
        elif index == 2: self.refresh_users()
        elif index == 3: self.refresh_security()
        elif index == 4: self.refresh_menu()
        elif index == 5: self.refresh_cierres()
        
        # Forzar actualizaci├│n de interfaz para que se sienta instant├íneo
        self.update_idletasks()

    def show_admin_menu(self):
        """Vuelve al men├║ principal de administraci├│n."""
        self.notebook.select(0)
        self.title_lbl.config(text='­ƒôè PANEL DE ADMINISTRACI├ôN')
        self.btn_back_admin.pack_forget()
        self.btn_back_main.pack(side='right', padx=5)

    def refresh(self):
        """Refresca la secci├│n activa detectando autom├íticamente cu├íl es."""
        try:
            idx = self.notebook.index('current')
            if idx == 1: self.refresh_inventory()
            elif idx == 2: self.refresh_users()
            elif idx == 3: self.refresh_security()
            elif idx == 4: self.refresh_menu()
            elif idx == 5: self.refresh_cierres()
        except: pass

    def setup_inventory(self):
        """Prepara la estructura visual de la secci├│n de inventario con una tabla moderna."""
        # Contenedor superior para controles
        controls = ttk.Frame(self.inv_frame, padding=(0, 0, 0, 20))
        controls.pack(fill='x')
        
        ttk.Label(controls, text="Control de Materia Prima e Ingredientes", font=(None, 16, 'bold')).pack(side='left')
        ttk.Button(controls, text='Actualizar Lista', command=self.refresh_inventory, bootstyle="success", padding=10).pack(side='right')

        # Tabla de Inventario (Treeview)
        cols = ('ID', 'Ingrediente', 'Stock Actual', 'Unidad', 'M├¡nimo')
        self.inv_tree = ttk.Treeview(self.inv_frame, columns=cols, show='headings', bootstyle="success", height=15)
        
        # Configurar cabeceras y anchos de columna
        for c in cols:
            self.inv_tree.heading(c, text=c)
            self.inv_tree.column(c, anchor='center', width=150)
        
        self.inv_tree.column('Ingrediente', anchor='w', width=300)
        self.inv_tree.pack(fill='both', expand=True)

        # Panel de acciones r├ípidas (Ajuste de stock)
        actions = ttk.LabelFrame(self.inv_frame, text="Acciones de Ajuste R├ípido")
        actions.pack(fill='x', pady=(20, 0), padx=10)
        
        ttk.Label(actions, text="Seleccione un ingrediente de la tabla y use los botones para ajustar:", font=(None, 11)).pack(side='left', padx=10)
        
        btn_add = ttk.Button(actions, text="A├▒adir +1", command=lambda: self.adjust_selected_stock(1), bootstyle="success-outline", padding=10, width=15)
        btn_add.pack(side='left', padx=5)
        
        btn_rem = ttk.Button(actions, text="Quitar -1", command=lambda: self.adjust_selected_stock(-1), bootstyle="warning-outline", padding=10, width=15)
        btn_rem.pack(side='left', padx=5)

    def adjust_selected_stock(self, amount):
        """Ajusta el stock del elemento seleccionado en la tabla."""
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Por favor, seleccione un ingrediente de la tabla.")
            return
        
        item_id = self.inv_tree.item(sel[0])['values'][0]
        self.add_stock(item_id, amount)

    def setup_users(self):
        """Prepara la estructura visual de la secci├│n de usuarios con tabla profesional."""
        ttk.Label(self.users_frame, text="Gesti├│n de Personal y Accesos", font=(None, 16, 'bold')).pack(anchor='w', pady=(0, 10))
        
        cols = ('id', 'username', 'rol', 'nombre')
        # Tabla para mostrar usuarios existentes
        self.user_tree = ttk.Treeview(self.users_frame, columns=cols, show='headings', bootstyle="success", height=10)
        for c in cols:
            self.user_tree.heading(c, text=c.capitalize())
            self.user_tree.column(c, anchor='center', width=100)
        
        self.user_tree.column('nombre', anchor='w', width=250)
        self.user_tree.pack(fill='both', expand=True, pady=10)
        
        # Formulario para agregar nuevos usuarios
        form = ttk.LabelFrame(self.users_frame, text='Registrar Nuevo Usuario')
        form.pack(fill='x', pady=10, padx=10)
        
        inputs = ttk.Frame(form)
        inputs.pack(fill='x')
        
        ttk.Label(inputs, text='Usuario:').grid(row=0, column=0, padx=5, pady=5)
        self.e_user = ttk.Entry(inputs)
        self.e_user.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(inputs, text='Clave:').grid(row=0, column=2, padx=5, pady=5)
        self.e_pass = ttk.Entry(inputs, show='*')
        self.e_pass.grid(row=0, column=3, padx=5, pady=5, sticky='ew')
        
        ttk.Label(inputs, text='Rol:').grid(row=1, column=0, padx=5, pady=5)
        self.e_rol = ttk.Combobox(inputs, values=['Admin', 'Cajera', 'Cocina', 'Mesero'])
        self.e_rol.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(inputs, text='Nombre:').grid(row=1, column=2, padx=5, pady=5)
        self.e_nombre = ttk.Entry(inputs)
        self.e_nombre.grid(row=1, column=3, padx=5, pady=5, sticky='ew')
        
        inputs.columnconfigure((1, 3), weight=1)
        
        ttk.Button(form, text='CREAR USUARIO', command=self.create_user, bootstyle="success").pack(pady=10)

    def setup_security(self):
        """Configura el panel de seguridad y m├®tricas con un dise├▒o limpio."""
        # --- M├®tricas de Seguridad ---
        metrics_frame = ttk.LabelFrame(self.security_frame, text="Estado de Seguridad del Sistema")
        metrics_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Grid para m├®tricas
        m_inner = ttk.Frame(metrics_frame)
        m_inner.pack(fill='x')
        
        self.lbl_failed = ttk.Label(m_inner, text="­ƒÜ¿ Intentos fallidos hoy: 0", font=(None, 14), bootstyle="danger")
        self.lbl_failed.grid(row=0, column=0, padx=30)
        
        self.lbl_sessions = ttk.Label(m_inner, text="­ƒæÑ Sesiones activas: 0", font=(None, 14), bootstyle="info")
        self.lbl_sessions.grid(row=0, column=1, padx=30)
        
        info = verify_license()
        if info['status'] == 'activated':
            lic_name = LICENSE_TYPES.get(info['type'], {}).get('name', 'Lifetime') if info['type'] else 'Lifetime'
            days_msg = f" ({info['days_left']} d├¡as)" if info['days_left'] else ""
            self.lbl_license = ttk.Label(m_inner, text=f"Ô£ô {lic_name}{days_msg}", font=(None, 14), bootstyle="success")
        elif info['status'] == 'trial':
            self.lbl_license = ttk.Label(m_inner, text=f"­ƒôà Prueba: {info['days_left']} d├¡as", font=(None, 14), bootstyle="info")
        else:
            self.lbl_license = ttk.Label(m_inner, text="ÔÜá BLOQUEADO", font=(None, 14, 'bold'), bootstyle="danger")
        self.lbl_license.grid(row=0, column=2, padx=30)
        
        btn_backup = ttk.Button(m_inner, text="­ƒÆ¥ Generar Respaldo DB", command=self.manual_backup, bootstyle="success", padding=10)
        btn_backup.grid(row=0, column=3, padx=30)
        
        btn_activate = ttk.Button(m_inner, text="­ƒöÉ Activar Sistema", command=self.open_license_window, bootstyle="warning", padding=10)
        btn_activate.grid(row=0, column=4, padx=30)
        
        btn_test_print = ttk.Button(m_inner, text="­ƒû¿ Probar Impresora/Caj├│n", command=self.test_printer, bootstyle="info", padding=10)
        btn_test_print.grid(row=0, column=5, padx=30)

        # --- Tabla de Auditor├¡a ---
        ttk.Label(self.security_frame, text="Historial de Auditor├¡a (├Ültimas Actividades)", font=(None, 16, 'bold')).pack(anchor='w', pady=15)
        
        cols = ('Fecha', 'Usuario', 'Acci├│n', 'Tabla', 'Detalles')
        self.audit_tree = ttk.Treeview(self.security_frame, columns=cols, show='headings', bootstyle="info", height=12)
        for c in cols:
            self.audit_tree.heading(c, text=c)
            self.audit_tree.column(c, anchor='center', width=120)
        
        self.audit_tree.column('Fecha', width=180)
        self.audit_tree.column('Detalles', anchor='w', width=400)
        self.audit_tree.pack(fill='both', expand=True)

    def manual_backup(self):
        """Ejecuta un backup manual desde la interfaz."""
        path = self.db.create_backup()
        if path:
            messagebox.showinfo("Backup Exitoso", f"Copia de seguridad creada en:\n{path}")
        else:
            messagebox.showerror("Error", "No se pudo crear la copia de seguridad")

    def test_printer(self):
        """Realiza una prueba de impresi├│n y apertura de caj├│n."""
        printer_name = find_pos_printer()
        if not printer_name:
            messagebox.showerror("Error", "No se detect├│ ninguna impresora t├®rmica POS instalada.")
            return
            
        confirm = messagebox.askyesno("Prueba", f"┬┐Desea probar la impresora:\n{printer_name}?\n\nSe enviar├í un ticket de prueba y se abrir├í el caj├│n.")
        if not confirm: return
        
        test_text = """
    ====================================
    *       PRUEBA DE IMPRESION        *
    *         PIK'TA SOFT              *
    ====================================
    FECHA:       {}
    ESTADO:      CORRECTO
    ------------------------------------
    SISTEMA OPERATIVO: {}
    IMPRESORA DETECTADA:
    {}
    ------------------------------------
    ┬íPRUEBA EXITOSA!
    ====================================
    
    
    
    """.format(datetime.now().strftime('%d/%m/%Y %H:%M:%S'), sys.platform, printer_name)
        
        # 1. Abrir Caj├│n
        try:
            hPrinter = win32print.OpenPrinter(printer_name)
            raw_data = b'\x1b\x70\x00\x19\xfa'
            win32print.StartDocPrinter(hPrinter, 1, ("Prueba Cajon", None, "RAW"))
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, raw_data)
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
            win32print.ClosePrinter(hPrinter)
        except Exception as e:
            messagebox.showerror("Error Caj├│n", f"No se pudo abrir el caj├│n: {e}")
            
        # 2. Imprimir Ticket (PIL)
        from PIL import Image, ImageDraw, ImageFont
        img_width = 380
        lines = test_text.split('\n')
        img_height = 100 + (len(lines) * 25)
        img = Image.new('RGB', (img_width, img_height), 'white')
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arialbd.ttf", 14)
        except:
            font = ImageFont.load_default()
            
        y = 20
        for line in lines:
            draw.text((10, y), line, fill='black', font=font)
            y += 25
            
        filename = "test_print.png"
        img.save(filename)
        try:
            win32api.ShellExecute(0, "printto", filename, f'"{printer_name}"', ".", 0)
            messagebox.showinfo("├ëxito", "Prueba de impresi├│n enviada y caj├│n abierto.")
        except Exception as e:
            os.startfile(filename, "print")
            messagebox.showinfo("Prueba", f"Enviado a imprimir por defecto (ShellExecute fall├│: {e})")

    def open_license_window(self):
        """Abre la ventana de activaci├│n del sistema."""
        LicenseWindow(self, self.db)
        info = verify_license()
        if info['status'] == 'activated':
            lic_name = LICENSE_TYPES.get(info['type'], {}).get('name', 'Lifetime') if info['type'] else 'Lifetime'
            days_msg = f" ({info['days_left']} d├¡as)" if info['days_left'] else ""
            self.lbl_license.config(text=f"Ô£ô {lic_name}{days_msg}", bootstyle="success")
        elif info['status'] == 'trial':
            self.lbl_license.config(text=f"­ƒôà Prueba: {info['days_left']} d├¡as", bootstyle="info")
        else:
            self.lbl_license.config(text="ÔÜá BLOQUEADO", bootstyle="danger")

    def refresh_security(self):
        """Actualiza las m├®tricas y logs de seguridad."""
        try:
            # Intentos fallidos hoy
            today = datetime.now().strftime('%Y-%m-%d')
            failed = self.db.fetch_one("SELECT COUNT(*) FROM access_logs WHERE action='failed_login' AND created_at LIKE ?", (f"{today}%",))
            self.lbl_failed.config(text=f"Intentos fallidos hoy: {failed[0] if failed else 0}")
            
            # Sesiones activas (del SessionManager global)
            active = len(session_manager.sessions)
            self.lbl_sessions.config(text=f"Sesiones activas: {active}")
            
            # Logs de auditor├¡a
            for r in self.audit_tree.get_children(): self.audit_tree.delete(r)
            logs = self.db.fetch_all("SELECT fecha, usuario, accion, tabla, detalles FROM auditoria ORDER BY fecha DESC LIMIT 50")
            for log in logs: self.audit_tree.insert('', 'end', values=log)
        except Exception as e:
            logging.error(f"Error al refrescar seguridad: {e}")

    def refresh_inventory(self):
        """Consulta y actualiza la tabla de inventario con formato limpio."""
        # Limpiar tabla actual
        for r in self.inv_tree.get_children():
            self.inv_tree.delete(r)
            
        rows = self.db.fetch_all('SELECT id, ingrediente, cantidad, unidad, stock_minimo FROM inventario')
        
        for r in rows:
            # Formatear el stock a 2 decimales para que no se vea como 2.1999999999
            stock_fmt = f"{r[2]:.2f}"
            
            # Insertar en la tabla
            item_id = self.inv_tree.insert('', 'end', values=(r[0], r[1], stock_fmt, r[3], r[4]))
            
            # Aplicar color si el stock est├í bajo el m├¡nimo
            if r[2] <= r[4]:
                self.inv_tree.tag_configure('low_stock', foreground='#ef4444') # Rojo
                self.inv_tree.item(item_id, tags=('low_stock',))
            else:
                self.inv_tree.tag_configure('normal_stock', foreground='#10b981') # Verde
                self.inv_tree.item(item_id, tags=('normal_stock',))

    def refresh_users(self):
        """Actualiza la tabla de usuarios registrados."""
        for r in self.user_tree.get_children(): self.user_tree.delete(r)
        rows = self.db.fetch_all('SELECT id, username, rol, nombre_completo FROM usuarios')
        for row in rows: self.user_tree.insert('', 'end', values=row)

    def create_user(self):
        """Valida e inserta un nuevo usuario en la base de datos."""
        u, p, r, n = self.e_user.get().strip(), self.e_pass.get().strip(), self.e_rol.get().strip(), self.e_nombre.get().strip()
        if not u or not p:
            messagebox.showwarning('Error', 'El usuario y la contrase├▒a son obligatorios')
            return
        try:
            hashed_p = hash_password(p)
            self.db.execute('INSERT INTO usuarios (username, password, rol, nombre_completo) VALUES (?,?,?,?)', (u, hashed_p, r or 'Cajera', n or u))
            
            # Registrar en auditor├¡a
            self.db.audit_log('usuarios', 'INSERT', 'Admin', f'Usuario creado: {u}')
            
            messagebox.showinfo('├ëxito', 'Usuario creado correctamente')
            # Limpiar campos despu├®s de crear
            for e in (self.e_user, self.e_pass, self.e_nombre): e.delete(0, 'end')
            self.refresh_users()
        except Exception as e:
            messagebox.showerror('Error', f"No se pudo crear el usuario: {e}")

    def add_stock(self, id, amount):
        """Incrementa o decrementa la cantidad de un ingrediente espec├¡fico."""
        try:
            # Obtener datos previos para auditor├¡a
            prev = self.db.fetch_one("SELECT ingrediente, cantidad FROM inventario WHERE id=?", (id,))
            
            self.db.execute('UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?', (amount, id))
            
            # Registrar en auditor├¡a
            self.db.audit_log('inventario', 'UPDATE', 'Admin', f'Stock ajustado: {prev[0]} ({amount})', prev={'cantidad': prev[1]}, new={'cantidad': prev[1]+amount})
            
            self.refresh_inventory()
        except Exception as e:
            messagebox.showerror('Error', 'No se pudo actualizar el stock')

    def setup_menu(self):
        """Prepara la interfaz para gestionar los productos del men├║."""
        ttk.Label(self.products_frame, text="Gesti├│n de Men├║ y Productos", font=(None, 16, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Tabla de productos
        cols = ('ID', 'Nombre', 'Categor├¡a', 'Precio', 'Emoji', 'Disponible')
        self.menu_tree = ttk.Treeview(self.products_frame, columns=cols, show='headings', bootstyle="info", height=10)
        for c in cols:
            self.menu_tree.heading(c, text=c)
            self.menu_tree.column(c, anchor='center', width=100)
        
        self.menu_tree.column('Nombre', anchor='w', width=200)
        self.menu_tree.pack(fill='both', expand=True, pady=10)

        # Formulario para nuevo producto
        form = ttk.LabelFrame(self.products_frame, text='A├▒adir Nuevo Producto')
        form.pack(fill='x', pady=10, padx=10)
        
        inputs = ttk.Frame(form)
        inputs.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(inputs, text='Nombre:').grid(row=0, column=0, padx=5, pady=5)
        self.e_prod_name = ttk.Entry(inputs)
        self.e_prod_name.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(inputs, text='Precio:').grid(row=0, column=2, padx=5, pady=5)
        self.e_prod_price = ttk.Entry(inputs)
        self.e_prod_price.grid(row=0, column=3, padx=5, pady=5, sticky='ew')
        
        ttk.Label(inputs, text='Categor├¡a:').grid(row=1, column=0, padx=5, pady=5)
        self.e_prod_cat = ttk.Combobox(inputs, values=['­ƒìö Combos', '­ƒìƒ Extras', '­ƒÑñ Bebidas'])
        self.e_prod_cat.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(inputs, text='Emoji:').grid(row=1, column=2, padx=5, pady=5)
        self.e_prod_emoji = ttk.Entry(inputs)
        self.e_prod_emoji.grid(row=1, column=3, padx=5, pady=5, sticky='ew')
        
        inputs.columnconfigure((1, 3), weight=1)
        
        btn_frame = ttk.Frame(form)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text='CREAR PRODUCTO', command=self.create_product, bootstyle="info").pack(side='left', padx=5)
        ttk.Button(btn_frame, text='ELIMINAR SELECCIONADO', command=self.delete_product, bootstyle="danger-outline").pack(side='left', padx=5)

    def refresh_menu(self):
        """Actualiza la tabla de productos del men├║."""
        for r in self.menu_tree.get_children(): self.menu_tree.delete(r)
        rows = self.db.fetch_all('SELECT id, nombre, categoria, precio, emoji, disponible FROM productos_menu')
        for r in rows:
            disp = "S├ì" if r[5] else "NO"
            self.menu_tree.insert('', 'end', values=(r[0], r[1], r[2], f"${r[3]:.2f}", r[4], disp))

    def create_product(self):
        """Inserta un nuevo producto en el men├║."""
        n, p, c, e = self.e_prod_name.get().strip(), self.e_prod_price.get().strip(), self.e_prod_cat.get().strip(), self.e_prod_emoji.get().strip()
        if not n or not p:
            messagebox.showwarning('Error', 'Nombre y precio son obligatorios')
            return
        try:
            self.db.execute('INSERT INTO productos_menu (nombre, precio, categoria, emoji) VALUES (?,?,?,?)', (n, float(p), c, e or '­ƒì¢'))
            messagebox.showinfo('├ëxito', 'Producto a├▒adido al men├║')
            for entry in (self.e_prod_name, self.e_prod_price, self.e_prod_emoji): entry.delete(0, 'end')
            self.refresh_menu()
        except Exception as err:
            logging.error(f"Error al crear el producto: {err}")
            play_sound_error()
            messagebox.showerror('Error', f"No se pudo crear el producto: {err}")

    def delete_product(self):
        """Elimina el producto seleccionado."""
        sel = self.menu_tree.selection()
        if not sel: return
        item_id = self.menu_tree.item(sel[0])['values'][0]
        if messagebox.askyesno('Confirmar', '┬┐Eliminar este producto del men├║?'):
            try:
                self.db.execute('DELETE FROM productos_menu WHERE id = ?', (item_id,))
                self.refresh_menu()
            except Exception as e:
                messagebox.showerror('Error', f"No se pudo eliminar: {e}")


class LoginWindow(ttk.Toplevel):
    """
    Ventana de Inicio de Sesi├│n.
    Controla el acceso al sistema mediante credenciales.
    """
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.user = None # Guardar├í los datos del usuario si el login es exitoso
        self.title('Login - SISTEMA POS PIK\'TA')
        self.resizable(False, False)
        # Aumentar tama├▒o de la ventana de login para que se aprecie mejor
        center_window(self, 500, 700)
        self.grab_set() # Bloquea interacci├│n con la ventana principal hasta que se cierre esta

        container = ttk.Frame(self, padding=30)
        container.pack(fill='both', expand=True)

        # Logo de la empresa en el login - Aumentado para mejor visualizaci├│n
        logo_path = os.path.join('Imagenes', 'pikta2.png')
        self.logo_img = load_image(logo_path, size=(200, 200))
        if self.logo_img:
            logo_lbl = ttk.Label(container, image=self.logo_img)
            logo_lbl.pack(pady=(0, 20))
        
        ttk.Label(container, text='Bienvenido', font=(None, 28, 'bold')).pack(pady=10)
        ttk.Label(container, text='Ingrese sus credenciales', font=(None, 16)).pack(pady=(0, 30))

        # Campo de Usuario con fuente m├ís grande
        self.username = ttk.Entry(container, font=(None, 16), bootstyle="info")
        self.username.pack(fill='x', pady=10)
        self.username.insert(0, 'Usuario')
        self.username.bind('<FocusIn>', lambda e: self.username.delete(0, 'end') if self.username.get() == 'Usuario' else None)

        # Campo de Contrase├▒a con fuente m├ís grande
        self.password = ttk.Entry(container, show='*', font=(None, 16), bootstyle="info")
        self.password.pack(fill='x', pady=10)

        # Botones de login y cancelaci├│n m├ís grandes
        self.btn_login = ttk.Button(container, text='INICIAR SESI├ôN', bootstyle="info", command=self.try_login, cursor="hand2", padding=15)
        self.btn_login.pack(fill='x', pady=(25, 10))
        ttk.Button(container, text='Cancelar', bootstyle="secondary-outline", command=self.cancel, cursor="hand2", padding=10).pack(fill='x')
        
        # Atajos de teclado para login
        self.bind('<Return>', lambda e: self.try_login())
        self.bind('<Tab>', lambda e: "continue") # Asegurar que Tab funcione para saltar campos

        # Pie de p├ígina con Derechos de Autor
        ttk.Label(container, text='┬® YAFA SOLUTIONS', font=(None, 10, 'bold'), bootstyle="secondary").pack(pady=(20, 0))

        # Configuraci├│n de foco inicial y atajos de teclado
        self.username.focus_set()
        self.bind('<Return>', lambda e: self.try_login()) # Enter para loguear
        self.bind('<Escape>', lambda e: self.cancel())    # Escape para cerrar
        
        # Manejar el cierre por la "X" de la ventana
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def try_login(self):
        """Verifica el usuario y contrase├▒a contra la base de datos."""
        u = self.username.get().strip()
        p = self.password.get().strip()
        if not u or not p or u == 'Usuario':
            messagebox.showwarning('Aviso', 'Por favor, ingrese su usuario y contrase├▒a')
            return
        
        # Consulta de validaci├│n
        row = self.db.fetch_one('SELECT id, username, password, rol, nombre_completo FROM usuarios WHERE username = ?', (u,))
        if not row:
            # Registrar intento fallido
            self.db.log_access(None, u, 'failed_login', 'Usuario no encontrado')
            messagebox.showerror('Error', 'Usuario o contrase├▒a incorrectos')
            return
        
        stored_password = row[2]
        if verify_password(stored_password, p):
            # Login exitoso
            user_data = {'id': row[0], 'username': row[1], 'rol': row[3], 'nombre_completo': row[4]}
            
            # Guardar en el master antes de destruir la ventana
            self.master.user = user_data
            self.master.session_token = session_manager.create_session(user_data)
            
            try:
                self.db.log_access(user_data['id'], user_data['username'], 'login')
            except Exception:
                logging.exception('Error registrando login')
            self.destroy()
        else:
            # Registrar intento fallido
            self.db.log_access(row[0], u, 'failed_login', 'Contrase├▒a incorrecta')
            messagebox.showerror('Error', 'Usuario o contrase├▒a incorrectos')

    def cancel(self):
        """Cierra el login sin autenticar."""
        self.user = None
        self.destroy()


class App(ttk.Window):
    """
    Clase Principal de la Aplicaci├│n.
    Gestiona el ciclo de vida del programa, el login persistente y el dashboard principal.
    """
    def __init__(self):
        super().__init__(themename="superhero")
        self.withdraw()
        
        self.title('SISTEMA POS PIK\'TA - Gesti├│n de Restaurante')
        self.db = DatabaseManager()
        self.user = None
        self.session_token = None

        self._check_and_show_license()

        self.run_login_loop()

        self.build()
        
        self.bind_all('<Return>', self._on_global_return)
        
        self.after(60000, self._check_session_periodically)
        
        self.geometry("1280x800")
        center_window(self, 1280, 800)
        self.state('zoomed')
        self.deiconify()
        
        footer = ttk.Frame(self, bootstyle="secondary", padding=5)
        footer.pack(fill='x', side='bottom')
        ttk.Label(footer, text='SISTEMA POS PIK\'TA | Desarrollado por YAFA SOLUTIONS ┬® 2026', 
                  font=(None, 10, 'bold'), bootstyle="inverse-secondary").pack()

    def _check_and_show_license(self):
        """Muestra ventana de licencia si es necesario."""
        info = verify_license()
        if info['status'] == 'trial':
            messagebox.showinfo("Bienvenida", f"Per├¡odo de prueba: {info['days_left']} d├¡as restantes.\nAdquiera una licencia para uso sin l├¡mites.")
        elif info['status'] == 'expired':
            self.withdraw()
            lic_win = LicenseWindow(self, self.db)
            self.wait_window(lic_win.top)
            info = verify_license()
            if info['status'] == 'expired':
                messagebox.showerror("Bloqueado", "Debe activar el sistema para continuar.")
                self.destroy()
                sys.exit(0)
            else:
                self.deiconify()
        else:
            lic_name = LICENSE_TYPES.get(info['type'], {}).get('name', 'Lifetime') if info['type'] else 'Lifetime'
            messagebox.showinfo("Sistema Activado", f"Licencia {lic_name} activa.")

    def _on_tab_changed(self, event):
        """Asegura que al cambiar de pesta├▒a, el widget principal reciba el foco."""
        try:
            tab_id = self.notebook.select()
            if not tab_id: return
            frame = self.nametowidget(tab_id)
            
            # Si el frame tiene un listbox (como KDS), darle foco directamente
            if hasattr(frame, 'listbox'):
                # Esperar un momento a que el frame se renderice completamente
                self.after(200, lambda: self._focus_kds_list(frame))
            # Para otros casos, buscar el primer widget que acepte foco
            else:
                frame.focus_set()
        except:
            pass

    def _focus_kds_list(self, frame):
        """Asistente para dar foco al listbox de KDS con selecci├│n inicial."""
        try:
            frame.listbox.focus_set()
            if frame.listbox.size() > 0:
                if not frame.listbox.curselection():
                    frame.listbox.selection_set(0)
                    frame.listbox.activate(0)
        except:
            pass

    def run_login_loop(self):
        """Maneja el proceso de inicio de sesi├│n hasta que sea exitoso o se cierre la ventana."""
        while not self.user:
            login = LoginWindow(self, self.db)
            self.wait_window(login)
            if not self.user:
                # Si el usuario es None, significa que cerr├│ la ventana o cancel├│
                self.destroy()
                sys.exit(0) # Salida total inmediata
                return

    def _check_session_periodically(self):
        """Verifica si la sesi├│n sigue siendo v├ílida."""
        if self.session_token and not session_manager.validate_session(self.session_token):
            messagebox.showwarning("Sesi├│n Expirada", "Su sesi├│n ha expirado por inactividad. Por favor, inicie sesi├│n de nuevo.")
            self.logout()
        else:
            # Seguir verificando cada minuto
            self.after(60000, self._check_session_periodically)

    def _on_global_return(self, event):
        """Manejador global para la tecla ENTER para mejorar accesibilidad."""
        w = self.focus_get()
        if not w: return
        
        # 1. Si es un bot├│n, ejecutarlo
        if isinstance(w, (ttk.Button, tk.Button)):
            w.invoke()
            return

        # 2. Otros widgets interactivos
        if isinstance(w, (ttk.Radiobutton, tk.Radiobutton)):
            w.invoke()
        elif hasattr(w, '_card_cmd'):
            w._card_cmd()
        elif isinstance(w, tk.Listbox):
            # Comportamiento por defecto para listbox si no se manej├│ antes
            w.event_generate('<Return>')

    def build(self):
        """Crea el dise├▒o general."""
        # --- Cabecera Superior (M├ís grande y clara) ---
        header = ttk.Frame(self, padding=(30, 20), bootstyle="secondary")
        header.pack(fill='x')
        
        user_info = ttk.Frame(header, bootstyle="secondary")
        user_info.pack(side='left')
        ttk.Label(user_info, text=f"Bienvenido(a), {self.user.get('nombre_completo')}", font=(None, 14), bootstyle="inverse-secondary").pack(anchor='w')
        ttk.Label(user_info, text='SISTEMA POS PIK\'TA', font=(None, 26, 'bold'), bootstyle="inverse-secondary").pack(anchor='w')

        # Bot├│n para salir (m├ís grande)
        self.btn_logout = ttk.Button(header, text='Cerrar Sesi├│n', command=self.logout, bootstyle="danger", cursor="hand2", padding=12)
        self.btn_logout.pack(side='right', pady=10)
        # self.btn_logout.bind('<Return>', lambda e: self.logout()) # Redundante con global handler

        # --- Contenedor de Pesta├▒as (Navegaci├│n Principal) ---
        style = ttk.Style()
        # Definir Large.TButton heredando de los estilos base de ttkbootstrap
        style.configure("Large.TButton", font=(None, 18, 'bold'))
        style.configure("Light.Large.TButton", font=(None, 18, 'bold'), background="#f8f9fa", foreground="#212529")
        style.map("Light.Large.TButton", background=[('active', '#e2e6ea')])
        
        style.layout('Hidden.TNotebook.Tab', []) 
        # Configurar el Notebook para que no tenga bordes ni fondos que tapen el logo
        style.configure('Hidden.TNotebook', borderwidth=0, highlightthickness=0, background=BG)
        style.configure('Hidden.TNotebook.Tab', background=BG)
        
        # Usamos un Frame maestro para el fondo que contenga el Notebook
        self.master_bg = tk.Frame(self, bg=BG)
        self.master_bg.pack(fill='both', expand=True)

        # IMPORTANTE: Para transparencia, los frames deben heredar el fondo del Label o ser transparentes
        # Como Tkinter no tiene transparencia real de widgets, cada m├│dulo dibuja su propio logo.
        self.notebook = ttk.Notebook(self.master_bg, style='Hidden.TNotebook')
        self.notebook.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Vincular evento de cambio de pesta├▒a para asegurar el foco correcto
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        role = self.user.get('rol', '').lower()
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')

        # --- Dashboard (Pesta├▒a Inicial) ---
        # Usamos un Canvas como base para permitir el logo de fondo real
        home = tk.Canvas(self.notebook, bg=BG, highlightthickness=0)
        self.notebook.add(home, text='Inicio')
        self.notebook.select(home)

        # Variables para control de renderizado y cach├®
        self.last_dash_w, self.last_dash_h = 0, 0
        self.dash_icons_cache = {}
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            self.bg_image_raw = Image.open(bg_logo_path)
        else:
            self.bg_image_raw = None

        def render_dashboard(e=None):
            cw = home.winfo_width()
            ch = home.winfo_height()
            if cw < 50 or ch < 50: # Esperar a tener dimensiones reales
                home.after(100, render_dashboard)
                return
            
            if cw == self.last_dash_w and ch == self.last_dash_h: return
            
            self.last_dash_w, self.last_dash_h = cw, ch
            home.delete("all")

            # 1. Dibujar el logo de fondo (si est├í disponible)
            if self.bg_image_raw:
                img_res = self.bg_image_raw.resize((cw, ch), Image.LANCZOS)
                home.bg_img = ImageTk.PhotoImage(img_res)
                home.create_image(cw//2, ch//2, image=home.bg_img, tags="bg")

            # 2. Dibujar las tarjetas (Simuladas en el Canvas para transparencia real)
            cards_data = [
                ('WhatsApp.jpg', 'WhatsApp Web', 'Gesti├│n de clientes.', self.open_whatsapp, SUCCESS, ('administrador', 'admin', 'supervisor', 'rommel')),
                ('pos.png', 'Caja / POS', 'Ventas y cobros.', self.open_pos, INFO, ('administrador', 'admin', 'cajera', 'supervisor', 'rommel')),
                ('user.png', 'Mesero', 'Pedidos a mesa.', self.open_mesero, WARNING, ('administrador', 'admin', 'mesero', 'supervisor', 'rommel')),
                ('cocina.jpeg', 'Cocina (KDS)', 'Gesti├│n de ├│rdenes.', self.open_kds, DANGER, ('administrador', 'admin', 'cocina', 'rommel')),
                ('admin.jpeg', 'Admin', 'Configuraci├│n.', self.open_admin, PRIMARY, ('administrador', 'admin', 'supervisor'))
            ]
            
            # Filtrar tarjetas seg├║n el rol del usuario
            cards_data = [c for c in cards_data if role in c[5]]

            # Mapeo de bootstyles a colores reales para el canvas (Superhero Theme)
            color_map = {
                SUCCESS: ("#5cb85c", "#1e3d23"), # (Borde, Fondo hover muy tenue)
                INFO: ("#5bc0de", "#1b3a42"),
                WARNING: ("#f0ad4e", "#42321b"),
                DANGER: ("#d9534f", "#3d1e1e"),
                PRIMARY: ("#df691a", "#42241b")
            }

            n_cards = len(cards_data)
            card_w, card_h = 220, 260
            gap = 30
            total_w = (card_w * n_cards) + (gap * (n_cards - 1))
            start_x = (cw - total_w) // 2
            start_y = (ch - card_h) // 2

            # Color de borde por defecto
            DEFAULT_OUTLINE = "#7975A0"

            # Contenedor para botones invisibles que permiten navegaci├│n TAB en el Canvas
            if not hasattr(home, 'tab_focus_frame'):
                home.tab_focus_frame = ttk.Frame(home, width=0, height=0)
            else:
                for w in home.tab_focus_frame.winfo_children(): w.destroy()
            
            home.tab_focus_frame.place(x=-100, y=-100) # Fuera de vista
            focus_buttons = []

            for i, (img_name, title, desc, cmd, bootstyle_name, roles) in enumerate(cards_data):
                x = start_x + (card_w + gap) * i
                y = start_y
                
                # Colores reales desde el mapeo
                hover_color, hover_bg = color_map.get(bootstyle_name, ("#ffffff", "#333333"))
                
                # Tags ├║nicos para cada tarjeta y sus elementos
                tag = f"card_{i}"
                bg_tag = f"bg_{i}"
                rect_tag = f"rect_{i}"

                # Crear un bot├│n invisible para capturar el foco TAB
                btn_focus = ttk.Button(home.tab_focus_frame, command=cmd)
                btn_focus.pack()
                focus_buttons.append(btn_focus)
                
                # Eventos de foco para navegaci├│n por teclado
                def on_focus(e, rt=rect_tag, bt=bg_tag, col=hover_color, bg=hover_bg):
                    home.itemconfig(rt, outline=col, width=6)
                    home.itemconfig(bt, fill=bg)
                
                def on_blur(e, rt=rect_tag, bt=bg_tag):
                    home.itemconfig(rt, outline=DEFAULT_OUTLINE, width=2)
                    home.itemconfig(bt, fill="")

                btn_focus.bind("<FocusIn>", on_focus)
                btn_focus.bind("<FocusOut>", on_blur)
                
                # Navegaci├│n por flechas entre botones de foco
                def make_arrow_nav(idx):
                    def nav(e):
                        if e.keysym == 'Left' and idx > 0:
                            focus_buttons[idx-1].focus_set()
                        elif e.keysym == 'Right' and idx < len(focus_buttons)-1:
                            focus_buttons[idx+1].focus_set()
                    return nav
                
                btn_focus.bind("<Left>", make_arrow_nav(i))
                btn_focus.bind("<Right>", make_arrow_nav(i))
                
                # 1. Rect├íngulo de fondo para el hover (inicialmente transparente/oculto)
                home.create_rectangle(x, y, x + card_w, y + card_h, 
                                    fill="", outline="", width=0, tags=(tag, bg_tag))
                
                # 2. Dibujar borde de la tarjeta
                home.create_rectangle(x, y, x + card_w, y + card_h, 
                                    outline=DEFAULT_OUTLINE, width=2, 
                                    tags=(tag, rect_tag, "card_rect"))
                
                # Cargar e insertar imagen (usando cach├®)
                img_path = os.path.join('Imagenes', img_name)
                if img_path not in self.dash_icons_cache:
                    self.dash_icons_cache[img_path] = load_image(img_path, size=(90, 90))
                
                card_icon = self.dash_icons_cache[img_path]
                if card_icon:
                    # Guardar referencia para que no se pierda
                    if not hasattr(home, 'icons'): home.icons = {}
                    home.icons[tag] = card_icon
                    home.create_image(x + card_w//2, y + 60, image=card_icon, tags=(tag, "icon"))
                
                # T├¡tulo
                home.create_text(x + card_w//2, y + 140, text=title, fill="#287F1E",
                               font=(None, 18, 'bold'), width=200, justify='center', tags=(tag, "title"))
                
                # Descripci├│n
                home.create_text(x + card_w//2, y + 200, text=desc, fill="#287F1E",
                               font=(None, 14), width=180, justify='center', tags=(tag, "desc"))

                # Hacer que toda la zona sea interactiva
                home.tag_bind(tag, "<Button-1>", lambda e, c=cmd: c())
                home.tag_bind(tag, "<Return>", lambda e, c=cmd: c())
                # Hover: cambia borde y el fondo completo para que se parezca al admin
                home.tag_bind(tag, "<Enter>", lambda e, rt=rect_tag, bt=bg_tag, col=hover_color, bg=hover_bg: (
                    home.itemconfig(rt, outline=col, width=6), 
                    home.itemconfig(bt, fill=bg),
                    home.config(cursor="hand2")
                ))
                home.tag_bind(tag, "<Leave>", lambda e, rt=rect_tag, bt=bg_tag: (
                    home.itemconfig(rt, outline=DEFAULT_OUTLINE, width=2), 
                    home.itemconfig(bt, fill=""),
                    home.config(cursor="")
                ))

        home.bind("<Configure>", lambda e: render_dashboard())
        # Llamada inicial proactiva
        home.after(100, render_dashboard)

        # --- Carga Din├ímica de Pesta├▒as seg├║n Rol ---
        # Solo se a├▒aden las pesta├▒as a las que el usuario tiene permiso de acceder.
        self.available_tabs = {}
        
        # WhatsApp Web: Admin, Supervisor, Rommel
        if role in ('administrador', 'admin', 'supervisor', 'rommel'):
            self.available_tabs['WhatsApp Web'] = {'class': WhatsAppFrame, 'text': 'WhatsApp Web'}
            self.notebook.add(ttk.Frame(self.notebook), text='WhatsApp Web')

        # Caja / POS: Admin, Cajera, Supervisor, Rommel
        if role in ('administrador', 'admin', 'cajera', 'supervisor', 'rommel'):
            self.available_tabs['Caja / POS'] = {'class': POSFrame, 'text': 'Caja / POS'}
            self.notebook.add(ttk.Frame(self.notebook), text='Caja / POS')

        # Mesero: Admin, Mesero, Supervisor, Rommel
        if role in ('administrador', 'admin', 'mesero', 'supervisor', 'rommel'):
            self.available_tabs['Mesero'] = {'class': MeseroFrame, 'text': 'Mesero'}
            self.notebook.add(ttk.Frame(self.notebook), text='Mesero')

        # Cocina: Admin, Cocina, Rommel
        if role in ('administrador', 'admin', 'cocina', 'rommel'):
            self.available_tabs['Cocina (KDS)'] = {'class': KDSFrame, 'text': 'Cocina (KDS)'}
            self.notebook.add(ttk.Frame(self.notebook), text='Cocina (KDS)')

        # Admin: EXCLUSIVO para Administrador y Supervisor
        if role in ('administrador', 'admin', 'supervisor'):
            self.available_tabs['Admin'] = {'class': AdminFrame, 'text': 'Admin'}
            self.notebook.add(ttk.Frame(self.notebook), text='Admin')

        # --- Atajos de Teclado Globales ---
        # CTRL + W para WhatsApp, CTRL + P para POS, CTRL + M para Mesero, CTRL + K para KDS, CTRL + A para Admin
        self.bind_all('<Control-w>', lambda e: self.open_whatsapp() if role in ('administrador','admin','supervisor','rommel') else None)
        self.bind_all('<Control-p>', lambda e: self.open_pos() if role in ('administrador','admin','cajera','supervisor','rommel') else None)
        self.bind_all('<Control-m>', lambda e: self.open_mesero() if role in ('administrador','admin','mesero','supervisor','rommel') else None)
        self.bind_all('<Control-k>', lambda e: self.open_kds() if role in ('administrador','admin','cocina','rommel') else None)
        self.bind_all('<Control-a>', lambda e: self.open_admin() if role in ('administrador','admin','supervisor') else None)
        self.bind_all('<Escape>', lambda e: self.notebook.select(0)) # Escape para volver al Home

    def get_or_create_frame(self, tab_text):
        """Retorna el frame de una pesta├▒a, cre├índolo si es necesario (Lazy Loading)."""
        tabs = self.notebook.tabs()
        for i, tab_id in enumerate(tabs):
            try:
                if self.notebook.tab(i, 'text') == tab_text:
                    widget = self.notebook.nametowidget(tab_id)
                    # Si el widget es un Frame gen├®rico (placeholder), reemplazarlo
                    if isinstance(widget, ttk.Frame) and not isinstance(widget, (WhatsAppFrame, POSFrame, MeseroFrame, KDSFrame, AdminFrame)):
                        tab_info = self.available_tabs.get(tab_text)
                        if tab_info:
                            # Crear el frame real
                            real_frame = tab_info['class'](self.notebook, self.db, user=self.user)
                            # Reemplazar el placeholder de forma segura: insertar antes de borrar
                            self.notebook.insert(i, real_frame, text=tab_text)
                            self.notebook.forget(i + 1)
                            return real_frame
                    return widget
            except:
                continue
        return None

    def open_whatsapp(self):
        """Cambia a la pesta├▒a de WhatsApp Web y lanza autom├íticamente la ventana integrada."""
        frame = self.get_or_create_frame('WhatsApp Web')
        if frame:
            self.notebook.select(frame)
            if hasattr(frame, 'connect_wa'):
                frame.connect_wa()

    def open_pos(self):
        """Cambia a la pesta├▒a del Punto de Venta."""
        frame = self.get_or_create_frame('Caja / POS')
        if frame:
            self.notebook.select(frame)
            if hasattr(frame, 'products_frame') and not frame.products_frame.winfo_children():
                if hasattr(frame, 'render_products'): frame.render_products()
            if hasattr(frame, 'refresh_unpaid_orders'): frame.refresh_unpaid_orders()

    def open_mesero(self):
        """Cambia a la pesta├▒a de Mesero."""
        frame = self.get_or_create_frame('Mesero')
        if frame:
            self.notebook.select(frame)
            if hasattr(frame, 'products_frame') and not frame.products_frame.winfo_children():
                if hasattr(frame, 'render_products'): frame.render_products()

    def open_kds(self):
        """Cambia a la pesta├▒a de Cocina."""
        frame = self.get_or_create_frame('Cocina (KDS)')
        if frame:
            self.notebook.select(frame)
            if hasattr(frame, 'refresh'): frame.refresh()
            if hasattr(frame, 'btn_back'): frame.btn_back.focus_set()

    def open_admin(self):
        """Cambia a la pesta├▒a de Administraci├│n."""
        frame = self.get_or_create_frame('Admin')
        if frame:
            self.notebook.select(frame)
            if hasattr(frame, 'refresh'): frame.refresh()

    def logout(self):
        """Cierra la sesi├│n del usuario y regresa a la pantalla de login."""
        try:
            if self.session_token:
                session_manager.close_session(self.session_token)
            
            if getattr(self, 'user', None):
                # Registrar el evento de salida en los logs
                self.db.log_access(self.user.get('id'), self.user.get('username'), 'logout')
        except Exception:
            logging.exception('Error al registrar logout')
        
        # Ocultar ventana y resetear estado
        self.withdraw()
        self.user = None
        self.session_token = None
        
        # Eliminar todos los widgets actuales para reconstruir desde cero al re-loguear
        for widget in self.winfo_children():
            widget.destroy()
            
        # Reiniciar el bucle de login
        self.run_login_loop()
        
        # Si el login fue exitoso, reconstruir y mostrar de nuevo
        self.build()
        self.deiconify()
        self.state('zoomed')
        
        # Re-iniciar el pie de p├ígina
        footer = ttk.Frame(self, bootstyle="secondary", padding=5)
        footer.pack(fill='x', side='bottom')
        ttk.Label(footer, text='SISTEMA POS PIK\'TA | Desarrollado por YAFA SOLUTIONS ┬® 2026', 
                  font=(None, 10, 'bold'), bootstyle="inverse-secondary").pack()


# =============================================================================
# PUNTO DE ENTRADA DEL PROGRAMA
# =============================================================================
if __name__ == '__main__':
    multiprocessing.freeze_support()
    # Crear e iniciar la aplicaci├│n principal
    app = App()
    app.mainloop()
