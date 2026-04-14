"""
main_app.py - Interfaz de escritorio estilo 'web' (Tkinter)

Este archivo contiene una versión de escritorio del panel del
restaurante (POS, KDS, Admin) adaptada desde la carpeta `web/`.

Componentes principales:
- `DatabaseManager`: Inicializa y gestiona la base de datos SQLite y migraciones.
- `LoginWindow`: Ventana modal para inicio de sesión con control de roles.
- `App`: Clase principal de la aplicación que gestiona el contenedor de pestañas (Notebook).
- `POSFrame`: Interfaz de Punto de Venta (Caja).
- `KDSFrame`: Monitor de Cocina para gestión de pedidos.
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

# =============================================================================
# FUNCIONES DE SONIDO Y NOTIFICACIÓN
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
    """Sonido fuerte de campanas para cuando un pedido está listo."""
    try:
        # Simulación de campana con frecuencias altas y decrecientes
        for _ in range(2):
            winsound.Beep(2500, 150)
            winsound.Beep(2000, 150)
            winsound.Beep(1500, 150)
            time.sleep(0.1)
    except:
        pass

# =============================================================================
# FUNCIONES DE SEGURIDAD (ENCRIPTACIÓN)
# =============================================================================

def hash_password(password):
    """Genera un hash seguro para la contraseña usando PBKDF2."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{hash_obj.hex()}"

def verify_password(stored_password, provided_password):
    """Verifica si la contraseña proporcionada coincide con el hash guardado."""
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
    """Gestiona las sesiones activas de los usuarios y su tiempo de expiración."""
    def __init__(self, timeout_seconds=1800): # 30 minutos por defecto
        self.sessions = {}
        self.session_timeout = timeout_seconds
    
    def create_session(self, user_data):
        """Crea una nueva sesión y devuelve el ID único."""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            'user': user_data,
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        return session_id
    
    def validate_session(self, session_id):
        """Verifica si la sesión es válida y no ha expirado."""
        if session_id not in self.sessions:
            return False
        session = self.sessions[session_id]
        # Verificar expiración por inactividad
        if (datetime.now() - session['last_activity']).total_seconds() > self.session_timeout:
            del self.sessions[session_id]
            return False
        # Actualizar última actividad
        session['last_activity'] = datetime.now()
        return True

    def get_user(self, session_id):
        """Retorna los datos del usuario de una sesión activa."""
        if self.validate_session(session_id):
            return self.sessions[session_id]['user']
        return None

    def close_session(self, session_id):
        """Elimina una sesión activa."""
        if session_id in self.sessions:
            del self.sessions[session_id]

# Instancia global del gestor de sesiones
session_manager = SessionManager()

# =============================================================================
# CONFIGURACIÓN DE REGISTRO DE ERRORES (LOGGING)
# =============================================================================
# Se registran todos los errores en 'error_log.txt' para facilitar el diagnóstico.
logging.basicConfig(filename='error_log.txt', filemode='a', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# Manejador global de excepciones: asegura que errores no capturados se guarden en el archivo log.
def _log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error('Excepción no capturada', exc_info=(exc_type, exc_value, exc_traceback))
    play_sound_error()

sys.excepthook = _log_uncaught_exceptions

# Manejador específico para errores en los callbacks de Tkinter.
def _tk_report_callback_exception(self, exc, val, tb):
    logging.error('Excepción en callback de Tkinter', exc_info=(exc, val, tb))
    play_sound_error()

tk.Tk.report_callback_exception = _tk_report_callback_exception

# =============================================================================
# CONFIGURACIÓN VISUAL Y CONSTANTES
# =============================================================================
DB_NAME = "PIk'TADB.db"  # Nombre del archivo de base de datos SQLite
BG = '#2b3e50'          # Color de fondo principal (Azul Petróleo Superhero)
PANEL = '#4e5d6c'       # Color de fondo para paneles y tarjetas
FG = '#ebebeb'          # Color de texto principal (blanco grisáceo)
ACCENT = '#df691a'      # Color de acento (Naranja Superhero)
INFO = '#5bc0de'        # Azul claro para información
OK = '#5cb85c'          # Color para acciones exitosas (verde)
WARN = '#f0ad4e'        # Color para advertencias (naranja)
ERR = '#d9534f'         # Color para errores críticos (rojo)
FONT_SIZE_L = 16        # Tamaño de fuente grande
FONT_SIZE_XL = 22       # Tamaño de fuente extra grande
FONT_SIZE_NORMAL = 12   # Tamaño de fuente normal

# Intentar importar Pillow para soporte avanzado de imágenes (JPEG, redimensionamiento)
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

def load_image(path, size=None):
    """
    Carga una imagen desde el disco.
    Si Pillow está instalado, permite cambiar el tamaño (redimensionar).
    Si no, usa el PhotoImage básico de Tkinter (solo PNG/GIF).
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
    """Calcula y aplica la posición central para una ventana en la pantalla."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 3 # Un poco más arriba del centro absoluto para mejor visibilidad
    win.geometry(f"{width}x{height}+{x}+{y}")


class DatabaseManager:
    """
    Controlador de la base de datos SQLite.
    Se encarga de crear las tablas, manejar las conexiones y realizar migraciones.
    """

    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        """Abre y retorna una conexión activa a la base de datos."""
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Inicializa las tablas base y asegura que existan los campos necesarios."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            # Creación de tabla de usuarios
            cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                rol TEXT NOT NULL,
                nombre_completo TEXT
            )''')

            # Creación de tabla de productos del menú
            cur.execute('''CREATE TABLE IF NOT EXISTS productos_menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                categoria TEXT,
                emoji TEXT,
                disponible BOOLEAN DEFAULT 1
            )''')

            # Creación de tabla de pedidos
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
                created_at TEXT
            )''')

            # Creación de tabla de inventario
            cur.execute('''CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingrediente TEXT NOT NULL UNIQUE,
                cantidad REAL NOT NULL DEFAULT 0,
                unidad TEXT NOT NULL,
                stock_minimo REAL NOT NULL DEFAULT 0
            )''')

            # Creación de tabla de auditoría (Registro de cambios en datos)
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

            # Migración de contraseñas a formato hash si es necesario
            cur.execute("SELECT id, username, password FROM usuarios")
            users = cur.fetchall()
            for uid, uname, pwd in users:
                # Si la contraseña no tiene el formato de hash (no contiene ':'), encriptarla
                if ':' not in pwd:
                    new_pwd = hash_password(pwd)
                    cur.execute("UPDATE usuarios SET password = ? WHERE id = ?", (new_pwd, uid))
                    logging.info(f"Contraseña migrada a hash para usuario: {uname}")

            # Usuarios por defecto (con contraseñas ya encriptadas)
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

            # --- PRODUCTOS DE PRUEBA (CATEGORÍAS POR DEFECTO) ---
            test_products = [
                ("Hamburguesa Clásica", 8.50, "🍔 Combos", "🍔"),
                ("Pizza Pepperoni", 12.00, "🍔 Combos", "🍕"),
                ("Papas Fritas XL", 4.50, "🍟 Extras", "🍟"),
                ("Alitas BBQ (6 unidades)", 7.25, "🍟 Extras", "🍗"),
                ("Coca Cola 600ml", 2.00, "🥤 Bebidas", "🥤"),
                ("Jugo de Naranja Natural", 3.50, "🥤 Bebidas", "🍊")
            ]
            for n, p, c, e in test_products:
                try:
                    cur.execute('SELECT id FROM productos_menu WHERE nombre = ?', (n,))
                    if not cur.fetchone():
                        cur.execute('INSERT INTO productos_menu (nombre, precio, categoria, emoji) VALUES (?,?,?,?)', (n, p, c, e))
                except Exception as e:
                    logging.error(f"Error al insertar producto de prueba: {e}")

            # Registro de logs de acceso (quién entra y sale del sistema)
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
                cierre_at TEXT
            )''')

            conn.commit()

    def audit_log(self, tabla, accion, usuario=None, detalles='', prev=None, new=None):
        """Registra un evento en la tabla de auditoría."""
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
            logging.error(f"Error en log de auditoría: {e}")

    def create_backup(self):
        """Crea una copia de seguridad de la base de datos actual."""
        if not os.path.exists('Backups'):
            os.makedirs('Backups')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join('Backups', f'PIkTA_DB_backup_{timestamp}.db')
        
        try:
            shutil.copy2(self.db_name, backup_path)
            # Limpiar backups antiguos (mantener solo los últimos 30 días)
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
        """Función auxiliar para añadir columnas si no existen (idempotente)."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(f"PRAGMA table_info({table})")
                cols = [r[1] for r in cur.fetchall()]
                if column not in cols:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                    conn.commit()
            except Exception as e:
                logging.error(f"Error al añadir columna {column} a {table}: {e}")

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
            logging.exception(f'Error de ejecución DB: {e} - Query: {query}')
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
                if cw == self.last_bg_w and ch == self.last_bg_h: return
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
        
        # Cuerpo - Pestañas de POS
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
        
        ttk.Label(self.header, text='🛒 PUNTO DE VENTA (Caja)', font=(None, 24, 'bold'), bootstyle="inverse-info").pack(side='left', padx=10)
        
        # Botones de acción rápida en la cabecera (más grandes)
        ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10).pack(side='right', padx=5)

        self.btn_open_caja = ttk.Button(self.header, text='Abrir Caja', command=self.open_caja, bootstyle="success", cursor="hand2", padding=10)
        self.btn_open_caja.pack(side='right', padx=5)
        self.btn_close_caja = ttk.Button(self.header, text='Cerrar Caja', command=self.cerrar_caja, bootstyle="danger", cursor="hand2", padding=10)
        self.btn_close_caja.pack(side='right', padx=5)

        # --- Contenedor de Pestañas Internas ---
        self.pos_notebook = ttk.Notebook(self.body)
        self.pos_notebook.pack(fill='both', expand=True, pady=10)

        # Pestaña 1: Venta Directa
        self.tab_venta = ttk.Frame(self.pos_notebook, padding=10)
        self.pos_notebook.add(self.tab_venta, text='🛒 Venta Directa')

        # Lado izquierdo de Venta Directa: Catálogo
        left_v = ttk.Frame(self.tab_venta)
        left_v.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Filtro de categorías
        self.categories = ['🍔 Combos', '🍟 Extras', '🥤 Bebidas']
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

        # Lado derecho de Venta Directa: Carrito
        right_v = ttk.Frame(self.tab_venta, width=350, bootstyle="secondary")
        right_v.pack(side='right', fill='y')
        right_v.pack_propagate(False)
        
        ttk.Label(right_v, text='ORDEN ACTUAL', font=(None, 12, 'bold'), bootstyle="inverse-secondary", padding=10).pack(fill='x')
        self.cart_list = tk.Listbox(right_v, bg=PANEL, fg=FG, font=(None, 11), bd=0, highlightthickness=0, selectbackground=ACCENT)
        self.cart_list.pack(fill='both', expand=True, padx=10, pady=10)
        self.total_label = ttk.Label(right_v, text='Total: $0.00', font=(None, 14, 'bold'), bootstyle="inverse-secondary", padding=10)
        self.total_label.pack(fill='x')

        # Selector de canal en Caja (Para llevar o Consumo Local)
        chan_frame = ttk.Frame(right_v, bootstyle="secondary", padding=5)
        chan_frame.pack(fill='x')
        ttk.Label(chan_frame, text="Tipo de Pedido:", bootstyle="inverse-secondary").pack(side='left', padx=5)
        self.order_channel = tk.StringVar(value="CAJA") # Por defecto Caja
        ttk.Radiobutton(chan_frame, text="Llevar", variable=self.order_channel, value="LLEVAR", bootstyle="info-toolbutton").pack(side='left', padx=2)
        ttk.Radiobutton(chan_frame, text="Local", variable=self.order_channel, value="CAJA", bootstyle="info-toolbutton").pack(side='left', padx=2)

        ttk.Button(right_v, text='Quitar Item', command=self.remove_selected, bootstyle="danger", cursor="hand2").pack(fill='x', padx=10, pady=5)
        ttk.Button(right_v, text='CONFIRMAR PEDIDO', command=self.process_order, bootstyle="success", cursor="hand2", padding=10).pack(fill='x', padx=10, pady=10)

        # Pestaña 2: Cobrar Mesas
        self.tab_cobros = ttk.Frame(self.pos_notebook, padding=10)
        self.pos_notebook.add(self.tab_cobros, text='📋 Cobrar Mesas')
        
        self.build_cobros_tab()

        # Cargar productos inicialmente
        self.render_products()

    def build_cobros_tab(self):
        """Construye la interfaz para cobrar pedidos de meseros con teclado numérico y métodos de pago."""
        # Lado izquierdo: Lista de pedidos pendientes
        left_c = ttk.Frame(self.tab_cobros)
        left_c.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        ttk.Label(left_c, text='PEDIDOS PENDIENTES DE COBRO', font=(None, 14, 'bold')).pack(pady=10)
        
        # Tabla de pedidos pendientes
        cols = ('ID', 'Número', 'Mesa', 'Total', 'Fecha')
        self.unpaid_tree = ttk.Treeview(left_c, columns=cols, show='headings', bootstyle="info")
        for col in cols:
            self.unpaid_tree.heading(col, text=col)
            self.unpaid_tree.column(col, width=100)
        
        self.unpaid_tree.pack(fill='both', expand=True)
        
        ttk.Button(left_c, text='Actualizar Lista', command=self.refresh_unpaid_orders, bootstyle="info-outline").pack(pady=10)
        
        # Lado derecho: Detalles y Cobro (Más ancho para el teclado y detalle)
        right_c = ttk.Frame(self.tab_cobros, width=650, bootstyle="secondary")
        right_c.pack(side='right', fill='y')
        right_c.pack_propagate(False)
        
        ttk.Label(right_c, text='DETALLE DE CUENTA', font=(None, 14, 'bold'), bootstyle="inverse-secondary", padding=10).pack(fill='x')
        # Detalle más grande y ancho
        self.detail_text = tk.Text(right_c, bg=PANEL, fg=FG, font=(None, 14), height=8)
        self.detail_text.pack(fill='x', padx=10, pady=5)
        self.detail_text.config(state='disabled')
        
        self.total_cobro_label = ttk.Label(right_c, text='Total a Cobrar: $0.00', font=(None, 24, 'bold'), bootstyle="inverse-secondary", padding=10)
        self.total_cobro_label.pack(fill='x')

        # Botón para Agregar más productos a la mesa seleccionada
        ttk.Button(right_c, text='✚ AGREGAR PRODUCTOS A ESTA MESA', 
                  command=self.add_more_to_table, bootstyle="warning", cursor="hand2", padding=10).pack(fill='x', padx=10, pady=5)

        # --- Teclado Numérico y Métodos de Pago ---
        pay_frame = ttk.Frame(right_c, bootstyle="secondary", padding=10)
        pay_frame.pack(fill='both', expand=True)

        # Entrada de "Paga con"
        ttk.Label(pay_frame, text="Paga con $:", font=(None, 12), bootstyle="inverse-secondary").grid(row=0, column=0, columnspan=2, sticky='w')
        self.pay_amount_var = tk.StringVar(value="0.00")
        self.pay_entry = ttk.Entry(pay_frame, textvariable=self.pay_amount_var, font=(None, 18, 'bold'), justify='right')
        self.pay_entry.grid(row=1, column=0, columnspan=3, sticky='ew', pady=5)

        # Teclado Numérico
        numpad = ttk.Frame(pay_frame, bootstyle="secondary")
        numpad.grid(row=2, column=0, rowspan=4, columnspan=2, pady=10)

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
            btn = ttk.Button(numpad, text=b, width=5, bootstyle="light", 
                            command=lambda x=b: press_key(x))
            btn.grid(row=i//3, column=i%3, padx=2, pady=2, sticky='nsew')

        # Métodos de Pago con Imágenes
        methods_frame = ttk.Frame(pay_frame, bootstyle="secondary")
        methods_frame.grid(row=2, column=2, rowspan=4, padx=(10, 0), sticky='n')

        self.payment_method = tk.StringVar(value="EFECTIVO")
        
        methods = [
            ('EFECTIVO', 'efectivo.jpeg'),
            ('YAPPY', 'yappy.png'),
            ('TARJETA', 'visa.png')
        ]

        for i, (name, img_file) in enumerate(methods):
            m_btn = ttk.Frame(methods_frame, bootstyle="secondary", cursor="hand2")
            m_btn.pack(fill='x', pady=2)
            
            img = load_image(os.path.join('Imagenes', img_file), size=(40, 40))
            if img:
                lbl_img = ttk.Label(m_btn, image=img, bootstyle="inverse-secondary")
                lbl_img.image = img
                lbl_img.pack(side='left', padx=5)
            
            # Usar Radiobutton estilizado como botón
            rb = ttk.Radiobutton(m_btn, text=name, variable=self.payment_method, value=name, bootstyle="toolbutton")
            rb.pack(side='left', fill='x', expand=True)

        # Cambio
        self.change_label = ttk.Label(right_c, text='Cambio: $0.00', font=(None, 16), bootstyle="inverse-secondary", padding=5)
        self.change_label.pack(fill='x')
        
        def update_change(*args):
            try:
                total = float(self.total_cobro_label.cget("text").split('$')[1])
                paid = float(self.pay_amount_var.get())
                change = paid - total
                self.change_label.config(text=f"Cambio: ${max(0, change):.2f}")
            except: pass
        
        self.pay_amount_var.trace_add("write", update_change)

        ttk.Button(right_c, text='PROCESAR PAGO', command=self.pay_order, bootstyle="success", cursor="hand2", padding=15).pack(fill='x', padx=10, pady=10)
        
        self.unpaid_tree.bind('<<TreeviewSelect>>', self.on_unpaid_select)
        self.refresh_unpaid_orders()

    def refresh_unpaid_orders(self):
        """Consulta pedidos de meseros que aún no han sido pagados."""
        for r in self.unpaid_tree.get_children(): self.unpaid_tree.delete(r)
        
        query = "SELECT id, numero, mesa, total, created_at FROM pedidos WHERE pagado = 0 AND canal = 'MESERO' ORDER BY created_at DESC"
        rows = self.db.fetch_all(query)
        for r in rows:
            self.unpaid_tree.insert('', 'end', values=r)

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
            # Detalle con fuente más legible
            self.detail_text.insert('end', f"{'PRODUCTO':<20} {'PRECIO':>10}\n")
            self.detail_text.insert('end', "-"*35 + "\n")
            for it in items:
                self.detail_text.insert('end', f"{it['nombre']:<20} ${it['precio']:>10.2f}\n")
            self.detail_text.config(state='disabled')
            self.total_cobro_label.config(text=f"Total a Cobrar: ${order[1]:.2f}")
            self.pay_amount_var.set(f"{order[1]:.2f}")

    def pay_order(self):
        """Registra el pago del pedido seleccionado."""
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
        
        if messagebox.askyesno('Confirmar Pago', f'¿Confirmar el pago de ${self.total_cobro_label.cget("text").split("$")[1]} con {method}?'):
            try:
                self.db.execute('UPDATE pedidos SET pagado = 1, sesion_id = ?, metodo_pago = ? WHERE id = ?', 
                                (self.session_id, method, order_id))
                messagebox.showinfo('Éxito', 'Pago procesado correctamente')
                self.refresh_unpaid_orders()
                self.detail_text.config(state='normal')
                self.detail_text.delete('1.0', 'end')
                self.detail_text.config(state='disabled')
                self.total_cobro_label.config(text="Total a Cobrar: $0.00")
                self.pay_amount_var.set("0.00")
            except Exception as e:
                logging.error(f"Error al procesar pago: {e}")
                messagebox.showerror('Error', 'No se pudo procesar el pago')

    def add_more_to_table(self):
        """Permite al cajero agregar más productos a un pedido de mesa ya existente."""
        sel = self.unpaid_tree.selection()
        if not sel:
            messagebox.showwarning('Aviso', 'Seleccione una mesa primero')
            return
            
        item = self.unpaid_tree.item(sel[0])
        order_id = item['values'][0]
        mesa = item['values'][2]
        
        # Cambiar a la pestaña de Venta Directa
        self.pos_notebook.select(0)
        
        # Guardar en memoria que estamos editando una mesa
        self.editing_table_id = order_id
        messagebox.showinfo("Modo Edición", f"Agregue los productos adicionales para la {mesa} y presione 'Confirmar Pedido'.")
        
        # Modificar temporalmente el comportamiento de process_order
        self._original_process_order = self.process_order
        def update_existing_order():
            if not self.cart: return
            
            # Obtener items actuales
            res = self.db.fetch_one("SELECT items FROM pedidos WHERE id=?", (self.editing_table_id,))
            current_items = json.loads(res[0]) if res else []
            
            # Añadir nuevos
            new_items = [{'id': p[0], 'nombre': p[1], 'precio': p[2]} for p in self.cart]
            updated_items = current_items + new_items
            new_total = sum(p['precio'] for p in updated_items)
            
            try:
                self.db.execute("UPDATE pedidos SET items=?, subtotal=?, total=? WHERE id=?", 
                                (json.dumps(updated_items, ensure_ascii=False), new_total, new_total, self.editing_table_id))
                messagebox.showinfo("Éxito", f"Mesa {mesa} actualizada correctamente.")
                self.cart.clear()
                self.update_cart_display()
                # Restaurar comportamiento y volver a pestaña de cobros
                self.process_order = self._original_process_order
                self.editing_table_id = None
                self.pos_notebook.select(1)
                self.refresh_unpaid_orders()
            except Exception as e:
                logging.error(f"Error al actualizar mesa: {e}")
                messagebox.showerror("Error", "No se pudo actualizar la mesa.")

        self.process_order = update_existing_order

    def render_products(self):
        """Genera dinámicamente las tarjetas de productos según la categoría."""
        # Limpiar productos anteriores
        for w in self.products_frame.winfo_children():
            w.destroy()
        
        # Obtener productos de la base de datos
        products = self.db.fetch_all('SELECT id, nombre, precio, categoria, emoji FROM productos_menu')
        filtered = [p for p in products if (p[3] or '').strip() == self.selected_category.get()]
        
        if not filtered:
            ttk.Label(self.products_frame, text="No hay productos en esta categoría", padding=20).pack()
            return

        # Dibujar productos en un grid de 3 columnas (Más grandes)
        cols = 3
        product_btns = []
        for idx, p in enumerate(filtered):
            r, c = divmod(idx, cols)
            card = ttk.Frame(self.products_frame, bootstyle="light", padding=15)
            card.grid(row=r, column=c, padx=12, pady=12, sticky='nsew')
            
            ttk.Label(card, text=p[4] or '🍽', font=(None, 40), bootstyle="inverse-light").pack(pady=5)
            ttk.Label(card, text=p[1], font=(None, 14, 'bold'), bootstyle="inverse-light", wraplength=140, justify='center').pack()
            ttk.Label(card, text=f"${p[2]:.2f}", font=(None, 16), bootstyle="info").pack(pady=5)
            
            # Botón para añadir al carrito (más grande)
            btn = ttk.Button(card, text='Añadir', command=lambda pid=p: self.add_product(pid), bootstyle="info", cursor="hand2", takefocus=True, padding=8)
            btn.pack(fill='x')
            # btn.bind('<Return>', lambda e, pid=p: self.add_product(pid)) # Redundante con global handler
            product_btns.append(btn)
            
            # Navegación por flechas entre botones de productos
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
        """Agrega un producto a la lista del carrito."""
        self.cart.append(product)
        self.update_cart_display()

    def remove_selected(self):
        """Elimina el producto seleccionado en la lista del carrito."""
        sel = self.cart_list.curselection()
        if not sel: return
        idx = sel[0]
        del self.cart[idx]
        self.update_cart_display()

    def update_cart_display(self):
        """Refresca la visualización de la lista del carrito y calcula el total."""
        self.cart_list.delete(0, 'end')
        total = 0
        for p in self.cart:
            self.cart_list.insert('end', f"{p[1]:<20} ${p[2]:>6.2f}")
            total += p[2]
        self.total_label.config(text=f'Total: ${total:.2f}')

    def process_order(self):
        """Guarda el pedido en la base de datos y lo envía a cocina."""
        if not self.cart:
            messagebox.showinfo('Aviso', 'El carrito está vacío')
            return
        
        # Preparar datos del pedido
        items_list = [{'id': p[0], 'nombre': p[1], 'precio': p[2]} for p in self.cart]
        items = json.dumps(items_list, ensure_ascii=False)
        subtotal = sum((p.get('precio') or 0) for p in items_list)
        total = subtotal
        
        try:
            # Generar número de pedido único basado en fecha/hora
            canal = self.order_channel.get()
            numero = f"{canal}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            created_at = datetime.now().isoformat()
            usuario_id = self.user.get('id') if self.user else None
            sesion_id = self.session_id
            
            # Insertar en la base de datos
            self.db.execute('INSERT INTO pedidos (numero, items, subtotal, total, estado, canal, usuario_id, sesion_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                            (numero, items, subtotal, total, 'RECIBIDO', canal, usuario_id, sesion_id, created_at))
            
            # Registrar en auditoría
            self.db.audit_log('pedidos', 'INSERT', self.user.get('username'), f'Pedido {canal} creado: {numero}', new=items_list)
            
            messagebox.showinfo('Éxito', f'Pedido {canal} procesado correctamente')
        except Exception as e:
            logging.error(f'Error al procesar pedido POS: {e}')
            messagebox.showerror('Error', 'No se pudo crear el pedido')
        
        # Limpiar carrito después de la venta
        self.cart.clear()
        self.update_cart_display()

    def open_caja(self):
        """Inicia una nueva sesión de caja con un monto inicial."""
        if self.session_id:
            messagebox.showinfo('Caja', 'Ya hay una sesión de caja abierta')
            return
        inicial = simpledialog.askfloat('Abrir Caja', 'Monto inicial en caja:', minvalue=0.0)
        if inicial is None: return # El usuario canceló el diálogo
        
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
        """Finaliza la sesión de caja, calcula totales y muestra reporte."""
        if not self.session_id:
            messagebox.showwarning('Caja', 'No hay sesión de caja abierta')
            return
        
        cierre_at = datetime.now().isoformat()
        # Obtener todas las ventas realizadas en esta sesión
        rows = self.db.fetch_all('SELECT id, numero, total, items FROM pedidos WHERE sesion_id = ? AND canal = ?', (self.session_id, 'CAJA'))
        sum_total = sum(float(r[2] or 0) for r in rows)

        # Obtener monto inicial
        caja_row = self.db.fetch_one('SELECT inicial FROM caja_sesiones WHERE id = ?', (self.session_id,)) or (0.0,)
        inicial = float(caja_row[0] or 0)
        
        try:
            # Actualizar estado de la sesión a CERRADO
            self.db.execute('UPDATE caja_sesiones SET estado = ?, cierre_total = ?, cierre_at = ? WHERE id = ?', 
                            ('CERRADO', sum_total, cierre_at, self.session_id))
            messagebox.showinfo('Caja', 'Caja cerrada exitosamente')
        except Exception:
            logging.exception('Error al cerrar caja')

        # Mostrar reporte de cierre en la interfaz
        reporte = f"CIERRE DE CAJA ID: {self.session_id}\n"
        reporte += f"Total Ventas: ${sum_total:.2f}\n"
        reporte += f"Monto Inicial: ${inicial:.2f}\n"
        reporte += f"Total en Caja: ${sum_total + inicial:.2f}"
        
        self.show_report(reporte)
        self.session_id = None
        # Eliminar llamada duplicada a show_report

    def show_report(self, text):
        """Muestra una pantalla con el resumen del cierre de caja."""
        for w in self.products_frame.winfo_children():
            w.destroy()
        frm = ttk.Frame(self.products_frame, padding=20)
        frm.pack(fill='both', expand=True)
        ttk.Label(frm, text="REPORTE DE CIERRE", font=(None, 14, 'bold')).pack(pady=10)
        t = tk.Text(frm, height=15, width=50)
        t.insert('1.0', text)
        t.config(state='disabled')
        t.pack(pady=10)
        ttk.Button(frm, text='Regresar al Menú', command=self.render_products, bootstyle="info").pack(pady=10)


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
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            self.bg_raw = Image.open(bg_logo_path)
            def draw_mes_bg(e):
                self.delete("bg")
                cw, ch = e.width, e.height
                if cw < 10 or ch < 10: return
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
        
        ttk.Label(self.header, text='🍽️ MÓDULO DE MESERO', font=(None, 24, 'bold'), bootstyle="inverse-warning").pack(side='left', padx=10)
        ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10).pack(side='right', padx=5)

        # --- Cuerpo ---
        # Lado izquierdo: Mesas y Productos
        left = ttk.Frame(self.body)
        left.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Selección de Mesa / Para Llevar
        mesa_frame = ttk.LabelFrame(left, text="Seleccionar Mesa / Destino")
        mesa_frame.pack(fill='x', pady=(0, 15), padx=10)
        
        mesas = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Mesa 5", "Mesa 6", "Para Llevar"]
        for m in mesas:
            ttk.Radiobutton(mesa_frame, text=m, variable=self.selected_mesa, value=m, 
                           bootstyle="warning-toolbutton", padding=8).pack(side='left', padx=5)

        # Filtro de categorías
        self.categories = ['🍔 Combos', '🍟 Extras', '🥤 Bebidas']
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
            ttk.Label(card, text=p[4] or '🍽', font=(None, 40), bootstyle="inverse-light").pack(pady=5)
            ttk.Label(card, text=p[1], font=(None, 14, 'bold'), bootstyle="inverse-light", wraplength=140, justify='center').pack()
            ttk.Label(card, text=f"${p[2]:.2f}", font=(None, 16), bootstyle="warning").pack(pady=5)
            btn = ttk.Button(card, text='Añadir', command=lambda pid=p: self.add_product(pid), bootstyle="warning", cursor="hand2", padding=8, takefocus=True)
            btn.pack(fill='x')
            # btn.bind('<Return>', lambda e, pid=p: self.add_product(pid)) # Redundante con global handler
            product_btns.append(btn)

            # Navegación por flechas entre botones de productos
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
            messagebox.showinfo('Aviso', 'El pedido está vacío')
            return
        
        items_list = [{'id': p[0], 'nombre': p[1], 'precio': p[2]} for p in self.cart]
        items = json.dumps(items_list, ensure_ascii=False)
        total = sum(p[2] for p in self.cart)
        mesa = self.selected_mesa.get()
        
        try:
            numero = f"MES-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            created_at = datetime.now().isoformat()
            usuario_id = self.user.get('id') if self.user else None
            
            # Los pedidos de mesero se guardan como NO PAGADOS para que caja los cobre luego
            self.db.execute('INSERT INTO pedidos (numero, items, subtotal, total, estado, canal, usuario_id, created_at, mesa, pagado) VALUES (?,?,?,?,?,?,?,?,?,?)',
                            (numero, items, total, total, 'RECIBIDO', 'MESERO', usuario_id, created_at, mesa, 0))
            
            messagebox.showinfo('Éxito', f'Pedido de {mesa} enviado a cocina')
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
        
        # Logo de Fondo en KDS
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            self.bg_raw = Image.open(bg_logo_path)
            def draw_kds_bg(e):
                self.delete("bg")
                cw, ch = e.width, e.height
                if cw < 10 or ch < 10: return
                img_res = self.bg_raw.resize((cw, ch), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(img_res)
                self.create_image(cw//2, ch//2, image=self.bg_photo, tags="bg")
                self.tag_lower("bg")
            self.bind("<Configure>", draw_kds_bg)

        # --- Contenedores para Secciones ---
        self.header = ttk.Frame(self, bootstyle="warning", padding=15)
        self.header_win = self.create_window(0, 0, window=self.header, anchor='nw', tags="header")
        
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
            
        ttk.Label(self.header, text='🍳 MONITOR DE COCINA (KDS)', font=(None, 24, 'bold'), bootstyle="inverse-warning").pack(side='left', padx=10)
        ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10).pack(side='right', padx=5)
        ttk.Button(self.header, text='Refrescar', command=self.refresh, bootstyle="light-outline", cursor="hand2", padding=10).pack(side='right', padx=5)
        
        # --- Instrucciones ---
        instr = ttk.Label(self.header, text="TAB: Navegar / ENTER: Iniciar o Finalizar", font=(None, 12, 'italic'), bootstyle="inverse-warning")
        instr.pack(side='left', padx=20)

        # --- Área de Pedidos Scrolleable ---
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
        # Guardar qué ID tenía el foco antes de limpiar
        focused_widget = self.focus_get()
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
            
            # Determinar color según estado (estilo web)
            # RECIBIDO -> Azul (info)
            # PREPARANDO -> Naranja (warning)
            card_style = "info" if estado == 'RECIBIDO' else "warning"
            btn_text = "EMPEZAR PREPARACIÓN" if estado == 'RECIBIDO' else "MARCAR COMO LISTO"
            btn_style = "info" if estado == 'RECIBIDO' else "success"
            
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
                    ttk.Label(it_frame, text=f"• {it.get('nombre')}", font=(None, 13), bootstyle="inverse-light").pack(side='left')
                    ttk.Label(it_frame, text=f"x{it.get('qty', 1)}", font=(None, 13, 'bold'), bootstyle="info").pack(side='right')
            except:
                ttk.Label(body, text=items_json, font=(None, 11), wraplength=200).pack()
            
            # Footer con botón de acción (Focusable para TAB)
            footer = ttk.Frame(card, bootstyle="light", padding=10)
            footer.pack(fill='x')
            
            # El botón captura el foco TAB y ENTER (ya manejado globalmente por App._on_global_return)
            btn = ttk.Button(footer, text=btn_text, bootstyle=btn_style, cursor="hand2", 
                            command=lambda p=pid: self.advance_order_state_by_id(p))
            btn.pack(fill='x', ipady=10)
            btn._order_id = pid # Guardar ID para persistencia de foco
            
            # Forzar el foco si es el botón que buscamos
            if pid == last_focused_id: target_btn = btn
            if not first_btn: first_btn = btn
            
            # ELIMINADO: btn.bind('<Return>') para evitar doble ejecución con el manejador global
            
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
        if target_btn:
            target_btn.focus_set()
        elif first_btn:
            # Si el pedido que tenía el foco ya no está (porque se completó), ir al primero
            first_btn.focus_set()

        # Configurar peso de columnas del grid
        for i in range(cols):
            self.cards_container.columnconfigure(i, weight=1)

    def advance_order_state_by_id(self, pid):
        """Avanza el estado de un pedido específico por su ID: RECIBIDO -> PREPARANDO -> LISTO."""
        try:
            # Obtener estado actual
            with self.db.get_connection() as conn:
                res = conn.execute("SELECT estado FROM pedidos WHERE id=?", (pid,)).fetchone()
                if not res: return
                current_state = res[0].upper()

                if current_state == 'RECIBIDO':
                    new_state = 'PREPARANDO'
                    conn.execute('UPDATE pedidos SET estado=? WHERE id=?', (new_state, pid))
                elif current_state == 'PREPARANDO':
                    new_state = 'LISTO'
                    conn.execute('UPDATE pedidos SET estado=? WHERE id=?', (new_state, pid))
                    # El sonido se dispara aquí al finalizar
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
    Módulo de WhatsApp Business PIK'TA.
    Se abre automáticamente en una ventana profesional integrada.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        super().__init__(parent, bg=BG, highlightthickness=0, *args, **kwargs)
        self.db = db
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
        
        ttk.Label(self.header, text='💬 WHATSAPP BUSINESS PIK\'TA', font=(None, 24, 'bold'), bootstyle="inverse-success").pack(side='left', padx=10)
        ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10).pack(side='right', padx=5)

        # --- Cuerpo Informativo ---
        info_container = tk.Frame(self.body, bg=BG)
        info_container.place(relx=0.5, rely=0.5, anchor='center')
        
        ttk.Label(info_container, text="WhatsApp Business se está ejecutando de forma integrada.", 
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
        
        ttk.Button(inner_test, text="🔔 Probar Nuevo Pedido", command=play_sound_new_order, bootstyle="info-outline").pack(side='left', padx=5)
        ttk.Button(inner_test, text="📢 Probar Pedido Listo", command=play_sound_order_ready, bootstyle="warning-outline").pack(side='left', padx=5)
        ttk.Button(inner_test, text="❌ Probar Error", command=play_sound_error, bootstyle="danger-outline").pack(side='left', padx=5)

    def connect_wa(self):
        """Abre WhatsApp Web de forma integrada y silenciosa, evitando duplicados."""
        try:
            # Verificar si ya hay un proceso en ejecución
            if self.wa_process and self.wa_process.poll() is None:
                # El proceso sigue vivo, no lanzar otro
                logging.info("WhatsApp ya está abierto o conectando...")
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
    Panel de Administración con sistema de tarjetas similar al principal.
    Permite gestionar el inventario, usuarios y seguridad.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        super().__init__(parent, bg=BG, highlightthickness=0, *args, **kwargs)
        self.db = db
        
        # Logo de Fondo en Admin
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            self.bg_raw = Image.open(bg_logo_path)
            self.last_bg_w, self.last_bg_h = 0, 0
            def draw_adm_bg(e):
                cw, ch = e.width, e.height
                if cw < 10 or ch < 10: return
                if cw == self.last_bg_w and ch == self.last_bg_h: return
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

        self.title_lbl = ttk.Label(self.header, text='📊 PANEL DE ADMINISTRACIÓN', font=(None, 24, 'bold'), bootstyle="inverse-success")
        self.title_lbl.pack(side='left', padx=10)
        
        self.btn_back_main = ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="light-outline", cursor="hand2", padding=10)
        self.btn_back_main.pack(side='right', padx=5)
        # self.btn_back_main.bind('<Return>', lambda e: self.master.select(0)) # Redundante
        
        self.btn_back_admin = ttk.Button(self.header, text='Volver al Admin', command=self.show_admin_menu, bootstyle="light-outline", cursor="hand2", padding=10)
        # self.btn_back_admin.bind('<Return>', lambda e: self.show_admin_menu()) # Redundante

        # --- Contenedor Principal con Notebook Oculto en el cuerpo ---
        self.notebook = ttk.Notebook(self.body, style='Hidden.TNotebook')
        self.notebook.pack(fill='both', expand=True)

        # 1. Pestaña del Menú de Tarjetas (Cuadritos)
        self.menu_frame = ttk.Frame(self.notebook, padding=30)
        self.notebook.add(self.menu_frame, text='Menú Admin')
        self.setup_admin_menu()

        # 2. Pestaña de Inventario
        self.inv_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.inv_frame, text='Inventario')
        self.setup_inventory()

        # 3. Pestaña de Usuarios
        self.users_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.users_frame, text='Usuarios')
        self.setup_users()

        # 4. Pestaña de Seguridad
        self.security_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.security_frame, text='Seguridad')
        self.setup_security()

        # 5. Pestaña de Menú / Productos
        self.products_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.products_frame, text='Menú / Productos')
        self.setup_menu()

        # Herramientas de mantenimiento al final del menú principal del admin
        self.setup_admin_tools(self.menu_frame)

        self.show_admin_menu() # Mostrar el menú de cuadritos al inicio

    def setup_admin_menu(self):
        """Crea el dashboard interno de administración con cuadritos e imágenes."""
        cards_wrap = ttk.Frame(self.menu_frame)
        cards_wrap.pack(fill='both', expand=True)

        def make_admin_card(parent, img_name, title, desc, cmd, color="success"):
            # Reutilizamos el estilo de 'pop-out' del dashboard principal
            card = ttk.Frame(parent, bootstyle="secondary", padding=2, cursor="hand2", takefocus=True, width=220, height=260)
            card.pack_propagate(False)
            
            inner = ttk.Frame(card, padding=10) 
            inner.pack(fill='both', expand=True)

            # Carga de imagen o emoji por defecto
            img = None
            if img_name:
                path = os.path.join('Imagenes', img_name)
                img = load_image(path, size=(90, 90))
            
            if img:
                lbl = ttk.Label(inner, image=img)
                lbl.image = img
                lbl.pack(pady=10)
            else:
                # Si no hay imagen, usar un emoji genérico según el título
                emoji = '📦'
                if 'Usuarios' in title: emoji = '👥'
                if 'Seguridad' in title: emoji = '🛡️'
                ttk.Label(inner, text=emoji, font=(None, 45)).pack(pady=10)

            ttk.Label(inner, text=title, font=(None, 22, 'bold'), wraplength=200, justify='center').pack(pady=5)
            ttk.Label(inner, text=desc, wraplength=180, justify='center', font=(None, 12)).pack(pady=5, fill='both', expand=True)

            def on_enter(e):
                card.configure(bootstyle=color, padding=5)
                inner.configure(bootstyle="light")
            def on_leave(e):
                card.configure(bootstyle="secondary", padding=2)
                inner.configure(bootstyle="default")

            card.bind("<Enter>", on_enter); card.bind("<Leave>", on_leave)
            card.bind("<FocusIn>", lambda e: on_enter(None)); card.bind("<FocusOut>", lambda e: on_leave(None))
            card.bind("<Button-1>", lambda e: cmd())
            card.bind("<Return>", lambda e: cmd())
            inner.bind("<Button-1>", lambda e: cmd())
            inner.bind("<Return>", lambda e: cmd())
            return card

        # Tarjetas del Admin con sus imágenes correspondientes
        admin_cards = []
        c1 = make_admin_card(cards_wrap, 'inventario.jpg', 'Inventario', 'Control de stock y materia prima.', lambda: self.open_section(1, "GESTIÓN DE INVENTARIO"))
        c1.grid(row=0, column=0, padx=20, pady=20)
        admin_cards.append(c1)

        c2 = make_admin_card(cards_wrap, 'user.png', 'Usuarios', 'Gestión de personal y accesos.', lambda: self.open_section(2, "GESTIÓN DE USUARIOS"))
        c2.grid(row=0, column=1, padx=20, pady=20)
        admin_cards.append(c2)

        c3 = make_admin_card(cards_wrap, 'seguridad.png', 'Seguridad', 'Auditoría y respaldos de DB.', lambda: self.open_section(3, "SEGURIDAD Y AUDITORÍA"))
        c3.grid(row=0, column=2, padx=20, pady=20)
        admin_cards.append(c3)

        c4 = make_admin_card(cards_wrap, 'pos.png', 'Menú / Productos', 'Gestión de productos y precios.', lambda: self.open_section(4, "GESTIÓN DE MENÚ"))
        c4.grid(row=0, column=3, padx=20, pady=20)
        admin_cards.append(c4)

        # Navegación por flechas para las tarjetas de Admin (Fila de 4)
        def nav_admin(idx, e):
            if e.keysym == 'Left' and idx > 0: admin_cards[idx-1].focus_set()
            elif e.keysym == 'Right' and idx < len(admin_cards)-1: admin_cards[idx+1].focus_set()

        for i, card in enumerate(admin_cards):
            card.bind("<Left>", lambda e, idx=i: nav_admin(idx, e))
            card.bind("<Right>", lambda e, idx=i: nav_admin(idx, e))

        for i in range(4): cards_wrap.columnconfigure(i, weight=1)

    def setup_admin_tools(self, parent):
        """Herramientas especiales para el administrador."""
        tools = ttk.LabelFrame(parent, text="Herramientas de Mantenimiento")
        tools.pack(fill='x', pady=20)
        
        # Frame interno para el padding, ya que LabelFrame no soporta el parámetro padding en algunas versiones
        inner_tools = ttk.Frame(tools, padding=15)
        inner_tools.pack(fill='x')
        
        btn_frame = ttk.Frame(inner_tools)
        btn_frame.pack(fill='x')
        
        ttk.Button(btn_frame, text="🧹 LIMPIAR PEDIDOS (REINICIAR COCINA)", 
                  command=self.clear_all_orders, bootstyle="danger-outline").pack(side='left', padx=10)
        
        ttk.Button(btn_frame, text="📦 REINICIAR INVENTARIO", 
                  command=self.reset_inventory, bootstyle="warning-outline").pack(side='left', padx=10)

    def clear_all_orders(self):
        """Elimina todos los pedidos de la base de datos para empezar de cero."""
        if messagebox.askyesno("Confirmar Limpieza", "¿Está seguro de eliminar TODOS los pedidos? Esta acción no se puede deshacer."):
            try:
                with self.db.get_connection() as conn:
                    conn.execute("DELETE FROM pedidos")
                messagebox.showinfo("Éxito", "Todos los pedidos han sido eliminados. La cocina está limpia.")
                # Si hay una instancia de KDS abierta, refrescarla si es posible
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo limpiar los pedidos: {e}")

    def reset_inventory(self):
        """Reinicia los valores de inventario a cero."""
        if messagebox.askyesno("Confirmar Reinicio", "¿Desea poner todas las existencias de inventario en cero?"):
            try:
                with self.db.get_connection() as conn:
                    conn.execute("UPDATE inventario SET cantidad = 0")
                messagebox.showinfo("Éxito", "Inventario reiniciado correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo reiniciar el inventario: {e}")

    def open_section(self, index, title):
        """Abre una sección específica y actualiza la cabecera."""
        self.notebook.select(index)
        self.title_lbl.config(text=f"📊 {title}")
        self.btn_back_main.pack_forget() # Ocultar botón principal
        self.btn_back_admin.pack(side='right', padx=5) # Mostrar botón volver al admin
        self.refresh()

    def show_admin_menu(self):
        """Vuelve al menú de cuadritos del admin."""
        self.notebook.select(0)
        self.title_lbl.config(text='📊 PANEL DE ADMINISTRACIÓN')
        self.btn_back_admin.pack_forget()
        self.btn_back_main.pack(side='right', padx=5)

    def refresh(self):
        """Refresca la sección activa."""
        try:
            idx = self.notebook.index('current')
            if idx == 1: self.refresh_inventory()
            elif idx == 2: self.refresh_users()
            elif idx == 3: self.refresh_security()
            elif idx == 4: self.refresh_menu()
        except: pass

    def setup_inventory(self):
        """Prepara la estructura visual de la sección de inventario con una tabla moderna."""
        # Contenedor superior para controles
        controls = ttk.Frame(self.inv_frame, padding=(0, 0, 0, 20))
        controls.pack(fill='x')
        
        ttk.Label(controls, text="Control de Materia Prima e Ingredientes", font=(None, 16, 'bold')).pack(side='left')
        ttk.Button(controls, text='Actualizar Lista', command=self.refresh_inventory, bootstyle="success", padding=10).pack(side='right')

        # Tabla de Inventario (Treeview)
        cols = ('ID', 'Ingrediente', 'Stock Actual', 'Unidad', 'Mínimo')
        self.inv_tree = ttk.Treeview(self.inv_frame, columns=cols, show='headings', bootstyle="success", height=15)
        
        # Configurar cabeceras y anchos de columna
        for c in cols:
            self.inv_tree.heading(c, text=c)
            self.inv_tree.column(c, anchor='center', width=150)
        
        self.inv_tree.column('Ingrediente', anchor='w', width=300)
        self.inv_tree.pack(fill='both', expand=True)

        # Panel de acciones rápidas (Ajuste de stock)
        actions = ttk.LabelFrame(self.inv_frame, text="Acciones de Ajuste Rápido")
        actions.pack(fill='x', pady=(20, 0), padx=10)
        
        ttk.Label(actions, text="Seleccione un ingrediente de la tabla y use los botones para ajustar:", font=(None, 11)).pack(side='left', padx=10)
        
        btn_add = ttk.Button(actions, text="Añadir +1", command=lambda: self.adjust_selected_stock(1), bootstyle="success-outline", padding=10, width=15)
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
        """Prepara la estructura visual de la sección de usuarios con tabla profesional."""
        ttk.Label(self.users_frame, text="Gestión de Personal y Accesos", font=(None, 16, 'bold')).pack(anchor='w', pady=(0, 10))
        
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

    def refresh(self):
        """Refresca todas las sub-secciones del panel admin."""
        self.refresh_inventory()
        self.refresh_users()
        self.refresh_security()

    def setup_security(self):
        """Configura el panel de seguridad y métricas con un diseño limpio."""
        # --- Métricas de Seguridad ---
        metrics_frame = ttk.LabelFrame(self.security_frame, text="Estado de Seguridad del Sistema")
        metrics_frame.pack(fill='x', pady=(0, 20), padx=10)
        
        # Grid para métricas
        m_inner = ttk.Frame(metrics_frame)
        m_inner.pack(fill='x')
        
        self.lbl_failed = ttk.Label(m_inner, text="🚨 Intentos fallidos hoy: 0", font=(None, 14), bootstyle="danger")
        self.lbl_failed.grid(row=0, column=0, padx=30)
        
        self.lbl_sessions = ttk.Label(m_inner, text="👥 Sesiones activas: 0", font=(None, 14), bootstyle="info")
        self.lbl_sessions.grid(row=0, column=1, padx=30)
        
        btn_backup = ttk.Button(m_inner, text="💾 Generar Respaldo DB", command=self.manual_backup, bootstyle="success", padding=10)
        btn_backup.grid(row=0, column=2, padx=30)

        # --- Tabla de Auditoría ---
        ttk.Label(self.security_frame, text="Historial de Auditoría (Últimas Actividades)", font=(None, 16, 'bold')).pack(anchor='w', pady=15)
        
        cols = ('Fecha', 'Usuario', 'Acción', 'Tabla', 'Detalles')
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

    def refresh_security(self):
        """Actualiza las métricas y logs de seguridad."""
        try:
            # Intentos fallidos hoy
            today = datetime.now().strftime('%Y-%m-%d')
            failed = self.db.fetch_one("SELECT COUNT(*) FROM access_logs WHERE action='failed_login' AND created_at LIKE ?", (f"{today}%",))
            self.lbl_failed.config(text=f"Intentos fallidos hoy: {failed[0] if failed else 0}")
            
            # Sesiones activas (del SessionManager global)
            active = len(session_manager.sessions)
            self.lbl_sessions.config(text=f"Sesiones activas: {active}")
            
            # Logs de auditoría
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
            
            # Aplicar color si el stock está bajo el mínimo
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
            messagebox.showwarning('Error', 'El usuario y la contraseña son obligatorios')
            return
        try:
            hashed_p = hash_password(p)
            self.db.execute('INSERT INTO usuarios (username, password, rol, nombre_completo) VALUES (?,?,?,?)', (u, hashed_p, r or 'Cajera', n or u))
            
            # Registrar en auditoría
            self.db.audit_log('usuarios', 'INSERT', 'Admin', f'Usuario creado: {u}')
            
            messagebox.showinfo('Éxito', 'Usuario creado correctamente')
            # Limpiar campos después de crear
            for e in (self.e_user, self.e_pass, self.e_nombre): e.delete(0, 'end')
            self.refresh_users()
        except Exception as e:
            messagebox.showerror('Error', f"No se pudo crear el usuario: {e}")

    def add_stock(self, id, amount):
        """Incrementa o decrementa la cantidad de un ingrediente específico."""
        try:
            # Obtener datos previos para auditoría
            prev = self.db.fetch_one("SELECT ingrediente, cantidad FROM inventario WHERE id=?", (id,))
            
            self.db.execute('UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?', (amount, id))
            
            # Registrar en auditoría
            self.db.audit_log('inventario', 'UPDATE', 'Admin', f'Stock ajustado: {prev[0]} ({amount})', prev={'cantidad': prev[1]}, new={'cantidad': prev[1]+amount})
            
            self.refresh_inventory()
        except Exception as e:
            messagebox.showerror('Error', 'No se pudo actualizar el stock')

    def setup_menu(self):
        """Prepara la interfaz para gestionar los productos del menú."""
        ttk.Label(self.products_frame, text="Gestión de Menú y Productos", font=(None, 16, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Tabla de productos
        cols = ('ID', 'Nombre', 'Categoría', 'Precio', 'Emoji', 'Disponible')
        self.menu_tree = ttk.Treeview(self.products_frame, columns=cols, show='headings', bootstyle="info", height=10)
        for c in cols:
            self.menu_tree.heading(c, text=c)
            self.menu_tree.column(c, anchor='center', width=100)
        
        self.menu_tree.column('Nombre', anchor='w', width=200)
        self.menu_tree.pack(fill='both', expand=True, pady=10)

        # Formulario para nuevo producto
        form = ttk.LabelFrame(self.products_frame, text='Añadir Nuevo Producto')
        form.pack(fill='x', pady=10, padx=10)
        
        inputs = ttk.Frame(form)
        inputs.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(inputs, text='Nombre:').grid(row=0, column=0, padx=5, pady=5)
        self.e_prod_name = ttk.Entry(inputs)
        self.e_prod_name.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(inputs, text='Precio:').grid(row=0, column=2, padx=5, pady=5)
        self.e_prod_price = ttk.Entry(inputs)
        self.e_prod_price.grid(row=0, column=3, padx=5, pady=5, sticky='ew')
        
        ttk.Label(inputs, text='Categoría:').grid(row=1, column=0, padx=5, pady=5)
        self.e_prod_cat = ttk.Combobox(inputs, values=['🍔 Combos', '🍟 Extras', '🥤 Bebidas'])
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
        """Actualiza la tabla de productos del menú."""
        for r in self.menu_tree.get_children(): self.menu_tree.delete(r)
        rows = self.db.fetch_all('SELECT id, nombre, categoria, precio, emoji, disponible FROM productos_menu')
        for r in rows:
            disp = "SÍ" if r[5] else "NO"
            self.menu_tree.insert('', 'end', values=(r[0], r[1], r[2], f"${r[3]:.2f}", r[4], disp))

    def create_product(self):
        """Inserta un nuevo producto en el menú."""
        n, p, c, e = self.e_prod_name.get().strip(), self.e_prod_price.get().strip(), self.e_prod_cat.get().strip(), self.e_prod_emoji.get().strip()
        if not n or not p:
            messagebox.showwarning('Error', 'Nombre y precio son obligatorios')
            return
        try:
            self.db.execute('INSERT INTO productos_menu (nombre, precio, categoria, emoji) VALUES (?,?,?,?)', (n, float(p), c, e or '🍽'))
            messagebox.showinfo('Éxito', 'Producto añadido al menú')
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
        if messagebox.askyesno('Confirmar', '¿Eliminar este producto del menú?'):
            try:
                self.db.execute('DELETE FROM productos_menu WHERE id = ?', (item_id,))
                self.refresh_menu()
            except Exception as e:
                messagebox.showerror('Error', f"No se pudo eliminar: {e}")


class LoginWindow(ttk.Toplevel):
    """
    Ventana de Inicio de Sesión.
    Controla el acceso al sistema mediante credenciales.
    """
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.user = None # Guardará los datos del usuario si el login es exitoso
        self.title('Login - SISTEMA POS PIK\'TA')
        self.resizable(False, False)
        # Aumentar tamaño de la ventana de login para que se aprecie mejor
        center_window(self, 500, 700)
        self.grab_set() # Bloquea interacción con la ventana principal hasta que se cierre esta

        container = ttk.Frame(self, padding=30)
        container.pack(fill='both', expand=True)

        # Logo de la empresa en el login - Aumentado para mejor visualización
        logo_path = os.path.join('Imagenes', 'pikta2.png')
        self.logo_img = load_image(logo_path, size=(200, 200))
        if self.logo_img:
            logo_lbl = ttk.Label(container, image=self.logo_img)
            logo_lbl.pack(pady=(0, 20))
        
        ttk.Label(container, text='Bienvenido', font=(None, 28, 'bold')).pack(pady=10)
        ttk.Label(container, text='Ingrese sus credenciales', font=(None, 16)).pack(pady=(0, 30))

        # Campo de Usuario con fuente más grande
        self.username = ttk.Entry(container, font=(None, 16), bootstyle="info")
        self.username.pack(fill='x', pady=10)
        self.username.insert(0, 'Usuario')
        self.username.bind('<FocusIn>', lambda e: self.username.delete(0, 'end') if self.username.get() == 'Usuario' else None)

        # Campo de Contraseña con fuente más grande
        self.password = ttk.Entry(container, show='*', font=(None, 16), bootstyle="info")
        self.password.pack(fill='x', pady=10)

        # Botones de login y cancelación más grandes
        self.btn_login = ttk.Button(container, text='INICIAR SESIÓN', bootstyle="info", command=self.try_login, cursor="hand2", padding=15)
        self.btn_login.pack(fill='x', pady=(25, 10))
        ttk.Button(container, text='Cancelar', bootstyle="secondary-outline", command=self.cancel, cursor="hand2", padding=10).pack(fill='x')
        
        # Atajos de teclado para login
        self.bind('<Return>', lambda e: self.try_login())
        self.bind('<Tab>', lambda e: "continue") # Asegurar que Tab funcione para saltar campos

        # Pie de página con Derechos de Autor
        ttk.Label(container, text='© YAFA SOLUTIONS', font=(None, 10, 'bold'), bootstyle="secondary").pack(pady=(20, 0))

        # Configuración de foco inicial y atajos de teclado
        self.username.focus_set()
        self.bind('<Return>', lambda e: self.try_login()) # Enter para loguear
        self.bind('<Escape>', lambda e: self.cancel())    # Escape para cerrar
        
        # Manejar el cierre por la "X" de la ventana
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def try_login(self):
        """Verifica el usuario y contraseña contra la base de datos."""
        u = self.username.get().strip()
        p = self.password.get().strip()
        if not u or not p or u == 'Usuario':
            messagebox.showwarning('Aviso', 'Por favor, ingrese su usuario y contraseña')
            return
        
        # Consulta de validación
        row = self.db.fetch_one('SELECT id, username, password, rol, nombre_completo FROM usuarios WHERE username = ?', (u,))
        if not row:
            # Registrar intento fallido
            self.db.log_access(None, u, 'failed_login', 'Usuario no encontrado')
            messagebox.showerror('Error', 'Usuario o contraseña incorrectos')
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
            self.db.log_access(row[0], u, 'failed_login', 'Contraseña incorrecta')
            messagebox.showerror('Error', 'Usuario o contraseña incorrectos')

    def cancel(self):
        """Cierra el login sin autenticar."""
        self.user = None
        self.destroy()


class App(ttk.Window):
    """
    Clase Principal de la Aplicación.
    Gestiona el ciclo de vida del programa, el login persistente y el dashboard principal.
    """
    def __init__(self):
        # Iniciar ventana con el tema 'superhero' que es más moderno y agradable
        super().__init__(themename="superhero")
        self.withdraw() # Ocultar ventana principal al inicio
        
        self.title('SISTEMA POS PIK\'TA - Gestión de Restaurante')
        self.db = DatabaseManager()
        self.user = None
        self.session_token = None

        # --- Bucle de Login Persistente ---
        self.run_login_loop()

        # Construir la interfaz mientras la ventana está oculta (withdraw)
        self.build()
        
        # Configurar navegación global por teclado
        self.bind_all('<Return>', self._on_global_return)
        
        # Iniciar verificación periódica de sesión (cada 1 minuto)
        self.after(60000, self._check_session_periodically)
        
        # Ahora que está construida, posicionar y mostrar
        self.geometry("1280x800")
        center_window(self, 1280, 800)
        self.state('zoomed')
        self.deiconify()
        
        # Pie de página global con Derechos de Autor
        footer = ttk.Frame(self, bootstyle="secondary", padding=5)
        footer.pack(fill='x', side='bottom')
        ttk.Label(footer, text='SISTEMA POS PIK\'TA | Desarrollado por YAFA SOLUTIONS © 2026', 
                  font=(None, 10, 'bold'), bootstyle="inverse-secondary").pack()

    def _on_tab_changed(self, event):
        """Asegura que al cambiar de pestaña, el widget principal reciba el foco."""
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
        """Asistente para dar foco al listbox de KDS con selección inicial."""
        try:
            frame.listbox.focus_set()
            if frame.listbox.size() > 0:
                if not frame.listbox.curselection():
                    frame.listbox.selection_set(0)
                    frame.listbox.activate(0)
        except:
            pass

    def run_login_loop(self):
        """Maneja el proceso de inicio de sesión hasta que sea exitoso o se cierre la ventana."""
        while not self.user:
            login = LoginWindow(self, self.db)
            self.wait_window(login)
            if not self.user:
                # Si el usuario es None, significa que cerró la ventana o canceló
                self.destroy()
                sys.exit(0) # Salida total inmediata
                return

    def _check_session_periodically(self):
        """Verifica si la sesión sigue siendo válida."""
        if self.session_token and not session_manager.validate_session(self.session_token):
            messagebox.showwarning("Sesión Expirada", "Su sesión ha expirado por inactividad. Por favor, inicie sesión de nuevo.")
            self.logout()
        else:
            # Seguir verificando cada minuto
            self.after(60000, self._check_session_periodically)

    def _on_global_return(self, event):
        """Manejador global para la tecla ENTER para mejorar accesibilidad."""
        w = self.focus_get()
        if not w: return
        
        # 1. Si es un botón, ejecutarlo
        if isinstance(w, (ttk.Button, tk.Button)):
            w.invoke()
            return

        # 2. Otros widgets interactivos
        if isinstance(w, (ttk.Radiobutton, tk.Radiobutton)):
            w.invoke()
        elif hasattr(w, '_card_cmd'):
            w._card_cmd()
        elif isinstance(w, tk.Listbox):
            # Comportamiento por defecto para listbox si no se manejó antes
            w.event_generate('<Return>')

    def build(self):
        """Crea el diseño general."""
        # --- Cabecera Superior (Más grande y clara) ---
        header = ttk.Frame(self, padding=(30, 20), bootstyle="secondary")
        header.pack(fill='x')
        
        user_info = ttk.Frame(header, bootstyle="secondary")
        user_info.pack(side='left')
        ttk.Label(user_info, text=f"Bienvenido(a), {self.user.get('nombre_completo')}", font=(None, 14), bootstyle="inverse-secondary").pack(anchor='w')
        ttk.Label(user_info, text='SISTEMA POS PIK\'TA', font=(None, 26, 'bold'), bootstyle="inverse-secondary").pack(anchor='w')

        # Botón para salir (más grande)
        self.btn_logout = ttk.Button(header, text='Cerrar Sesión', command=self.logout, bootstyle="danger", cursor="hand2", padding=12)
        self.btn_logout.pack(side='right', pady=10)
        # self.btn_logout.bind('<Return>', lambda e: self.logout()) # Redundante con global handler

        # --- Contenedor de Pestañas (Navegación Principal) ---
        style = ttk.Style()
        style.layout('Hidden.TNotebook.Tab', []) 
        # Configurar el Notebook para que no tenga bordes ni fondos que tapen el logo
        style.configure('Hidden.TNotebook', borderwidth=0, highlightthickness=0, background=BG)
        style.configure('Hidden.TNotebook.Tab', background=BG)
        
        # Usamos un Frame maestro para el fondo que contenga el Notebook
        self.master_bg = tk.Frame(self, bg=BG)
        self.master_bg.pack(fill='both', expand=True)

        # IMPORTANTE: Para transparencia, los frames deben heredar el fondo del Label o ser transparentes
        # Como Tkinter no tiene transparencia real de widgets, cada módulo dibuja su propio logo.
        self.notebook = ttk.Notebook(self.master_bg, style='Hidden.TNotebook')
        self.notebook.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Vincular evento de cambio de pestaña para asegurar el foco correcto
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        role = self.user.get('rol', '').lower()
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')

        # --- Dashboard (Pestaña Inicial) ---
        # Usamos un Canvas como base para permitir el logo de fondo real
        home = tk.Canvas(self.notebook, bg=BG, highlightthickness=0)
        self.notebook.add(home, text='Inicio')
        self.notebook.select(home)

        # Variables para control de renderizado y caché
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

            # 1. Dibujar el logo de fondo (si está disponible)
            if self.bg_image_raw:
                img_res = self.bg_image_raw.resize((cw, ch), Image.LANCZOS)
                home.bg_img = ImageTk.PhotoImage(img_res)
                home.create_image(cw//2, ch//2, image=home.bg_img, tags="bg")

            # 2. Dibujar las tarjetas (Simuladas en el Canvas para transparencia real)
            cards_data = [
                ('WhatsApp.jpg', 'WhatsApp Web', 'Gestión de clientes.', self.open_whatsapp, SUCCESS),
                ('pos.png', 'Caja / POS', 'Ventas y cobros.', self.open_pos, INFO),
                ('user.png', 'Mesero', 'Pedidos a mesa.', self.open_mesero, WARNING),
                ('cocina.jpeg', 'Cocina (KDS)', 'Gestión de órdenes.', self.open_kds, DANGER),
                ('admin.jpeg', 'Admin', 'Configuración.', self.open_admin, PRIMARY)
            ]

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

            # Contenedor para botones invisibles que permiten navegación TAB en el Canvas
            if not hasattr(home, 'tab_focus_frame'):
                home.tab_focus_frame = ttk.Frame(home, width=0, height=0)
            else:
                for w in home.tab_focus_frame.winfo_children(): w.destroy()
            
            home.tab_focus_frame.place(x=-100, y=-100) # Fuera de vista
            focus_buttons = []

            for i, (img_name, title, desc, cmd, bootstyle_name) in enumerate(cards_data):
                x = start_x + (card_w + gap) * i
                y = start_y
                
                # Colores reales desde el mapeo
                hover_color, hover_bg = color_map.get(bootstyle_name, ("#ffffff", "#333333"))
                
                # Tags únicos para cada tarjeta y sus elementos
                tag = f"card_{i}"
                bg_tag = f"bg_{i}"
                rect_tag = f"rect_{i}"

                # Crear un botón invisible para capturar el foco TAB
                btn_focus = ttk.Button(home.tab_focus_frame, command=cmd)
                btn_focus.pack()
                focus_buttons.append(btn_focus)
                
                # Eventos de foco para navegación por teclado
                def on_focus(e, rt=rect_tag, bt=bg_tag, col=hover_color, bg=hover_bg):
                    home.itemconfig(rt, outline=col, width=6)
                    home.itemconfig(bt, fill=bg)
                
                def on_blur(e, rt=rect_tag, bt=bg_tag):
                    home.itemconfig(rt, outline=DEFAULT_OUTLINE, width=2)
                    home.itemconfig(bt, fill="")

                btn_focus.bind("<FocusIn>", on_focus)
                btn_focus.bind("<FocusOut>", on_blur)
                
                # Navegación por flechas entre botones de foco
                def make_arrow_nav(idx):
                    def nav(e):
                        if e.keysym == 'Left' and idx > 0:
                            focus_buttons[idx-1].focus_set()
                        elif e.keysym == 'Right' and idx < len(focus_buttons)-1:
                            focus_buttons[idx+1].focus_set()
                    return nav
                
                btn_focus.bind("<Left>", make_arrow_nav(i))
                btn_focus.bind("<Right>", make_arrow_nav(i))
                
                # 1. Rectángulo de fondo para el hover (inicialmente transparente/oculto)
                home.create_rectangle(x, y, x + card_w, y + card_h, 
                                    fill="", outline="", width=0, tags=(tag, bg_tag))
                
                # 2. Dibujar borde de la tarjeta
                home.create_rectangle(x, y, x + card_w, y + card_h, 
                                    outline=DEFAULT_OUTLINE, width=2, 
                                    tags=(tag, rect_tag, "card_rect"))
                
                # Cargar e insertar imagen (usando caché)
                img_path = os.path.join('Imagenes', img_name)
                if img_path not in self.dash_icons_cache:
                    self.dash_icons_cache[img_path] = load_image(img_path, size=(90, 90))
                
                card_icon = self.dash_icons_cache[img_path]
                if card_icon:
                    # Guardar referencia para que no se pierda
                    if not hasattr(home, 'icons'): home.icons = {}
                    home.icons[tag] = card_icon
                    home.create_image(x + card_w//2, y + 60, image=card_icon, tags=(tag, "icon"))
                
                # Título
                home.create_text(x + card_w//2, y + 140, text=title, fill="#287F1E",
                               font=(None, 18, 'bold'), width=200, justify='center', tags=(tag, "title"))
                
                # Descripción
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

        # --- Carga Dinámica de Pestañas según Rol ---
        # Solo se añaden las pestañas a las que el usuario tiene permiso de acceder.
        # IMPORTANTE: Se añadió 'administrador' y 'admin' para asegurar el acceso total.
        if role in ('administrador', 'admin', 'supervisor'):
            whatsapp_tab = WhatsAppFrame(self.notebook, self.db)
            self.notebook.add(whatsapp_tab, text='WhatsApp Web')

        if role in ('administrador', 'admin', 'cajera', 'supervisor'):
            pos_tab = POSFrame(self.notebook, self.db, user=self.user)
            self.notebook.add(pos_tab, text='Caja / POS')

        if role in ('administrador', 'admin', 'mesero', 'supervisor'):
            mesero_tab = MeseroFrame(self.notebook, self.db, user=self.user)
            self.notebook.add(mesero_tab, text='Mesero')

        if role in ('administrador', 'admin', 'cocina'):
            kds_tab = KDSFrame(self.notebook, self.db, user=self.user)
            self.notebook.add(kds_tab, text='Cocina (KDS)')

        if role in ('administrador', 'admin', 'supervisor', 'super'):
            admin_tab = AdminFrame(self.notebook, self.db)
            self.notebook.add(admin_tab, text='Admin')

        # --- Atajos de Teclado Globales ---
        # CTRL + W para WhatsApp, CTRL + P para POS, CTRL + M para Mesero, CTRL + K para KDS, CTRL + A para Admin
        self.bind_all('<Control-w>', lambda e: self.open_whatsapp() if role in ('administrador','admin','supervisor') else None)
        self.bind_all('<Control-p>', lambda e: self.open_pos() if role in ('administrador','admin','cajera','supervisor') else None)
        self.bind_all('<Control-m>', lambda e: self.open_mesero() if role in ('administrador','admin','mesero','supervisor') else None)
        self.bind_all('<Control-k>', lambda e: self.open_kds() if role in ('administrador','admin','cocina') else None)
        self.bind_all('<Control-a>', lambda e: self.open_admin() if role in ('administrador','admin','supervisor') else None)

    def open_whatsapp(self):
        """Cambia a la pestaña de WhatsApp Web y lanza automáticamente la ventana integrada."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'WhatsApp Web':
                self.notebook.select(i)
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                # Lanzar WhatsApp automáticamente al entrar
                if hasattr(frame, 'connect_wa'):
                    frame.connect_wa()
                return

    def open_pos(self):
        """Cambia a la pestaña del Punto de Venta."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Caja / POS':
                self.notebook.select(i)
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                # Solo renderizar si no hay hijos o para refrescar datos importantes
                if hasattr(frame, 'products_frame') and not frame.products_frame.winfo_children():
                    if hasattr(frame, 'render_products'): frame.render_products()
                if hasattr(frame, 'refresh_unpaid_orders'): frame.refresh_unpaid_orders()
                return

    def open_mesero(self):
        """Cambia a la pestaña de Mesero."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Mesero':
                self.notebook.select(i)
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                if hasattr(frame, 'products_frame') and not frame.products_frame.winfo_children():
                    if hasattr(frame, 'render_products'): frame.render_products()
                return

    def open_kds(self):
        """Cambia a la pestaña de Cocina."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Cocina (KDS)':
                self.notebook.select(i)
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                if hasattr(frame, 'refresh'): frame.refresh()
                return

    def open_admin(self):
        """Cambia a la pestaña de Administración."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Admin':
                self.notebook.select(i)
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                if hasattr(frame, 'refresh'): frame.refresh()
                return

    def logout(self):
        """Cierra la sesión del usuario y regresa a la pantalla de login."""
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
        
        # Re-iniciar el pie de página
        footer = ttk.Frame(self, bootstyle="secondary", padding=5)
        footer.pack(fill='x', side='bottom')
        ttk.Label(footer, text='SISTEMA POS PIK\'TA | Desarrollado por YAFA SOLUTIONS © 2026', 
                  font=(None, 10, 'bold'), bootstyle="inverse-secondary").pack()


# =============================================================================
# PUNTO DE ENTRADA DEL PROGRAMA
# =============================================================================
if __name__ == '__main__':
    multiprocessing.freeze_support()
    # Crear e iniciar la aplicación principal
    app = App()
    app.mainloop()
