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
import shutil

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

sys.excepthook = _log_uncaught_exceptions

# Manejador específico para errores en los callbacks de Tkinter.
def _tk_report_callback_exception(self, exc, val, tb):
    logging.error('Excepción en callback de Tkinter', exc_info=(exc, val, tb))

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
            self._ensure_column('pedidos', 'canal', 'TEXT')
            self._ensure_column('pedidos', 'usuario_id', 'INTEGER')
            self._ensure_column('pedidos', 'sesion_id', 'INTEGER')
            self._ensure_column('pedidos', 'created_at', 'TEXT')

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


class POSFrame(ttk.Frame):
    """
    Interfaz del Punto de Venta (POS).
    Permite seleccionar productos, gestionar el carrito y realizar ventas.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(parent, padding=10, *args, **kwargs)
        self.db = db
        self.user = user
        self.session_id = None
        self.cart = [] # Lista de productos en la orden actual
        
        # Logo de Fondo (Marca de Agua) en POS - Usamos tk.Label para transparencia
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        self.bg_img_pos = load_image(bg_logo_path, size=(500, 500))
        if self.bg_img_pos:
            bg_lbl = tk.Label(self, image=self.bg_img_pos, bg=BG)
            bg_lbl.place(relx=0.5, rely=0.5, anchor='center')
            bg_lbl.lower()

        # --- Cabecera del POS con Resaltado ---
        header = ttk.Frame(self, bootstyle="info", padding=15)
        header.pack(fill='x')
        
        # Icono decorativo del POS
        pos_img = load_image(os.path.join('Imagenes', 'pos.png'), size=(60, 60))
        if pos_img:
            lbl = ttk.Label(header, image=pos_img, bootstyle="inverse-info")
            lbl.image = pos_img
            lbl.pack(side='left', padx=10)
        
        ttk.Label(header, text='🛒 PUNTO DE VENTA (Caja)', font=(None, 24, 'bold'), bootstyle="inverse-info").pack(side='left', padx=10)
        
        # Botones de acción rápida en la cabecera (más grandes)
        ttk.Button(header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10).pack(side='right', padx=5)

        self.btn_open_caja = ttk.Button(header, text='Abrir Caja', command=self.open_caja, bootstyle="success", cursor="hand2", padding=10)
        self.btn_open_caja.pack(side='right', padx=5)
        self.btn_close_caja = ttk.Button(header, text='Cerrar Caja', command=self.cerrar_caja, bootstyle="danger", cursor="hand2", padding=10)
        self.btn_close_caja.pack(side='right', padx=5)

        # --- Contenedor de Pestañas Internas (Venta vs Cobros) ---
        self.pos_notebook = ttk.Notebook(self)
        self.pos_notebook.pack(fill='both', expand=True, pady=10)

        # Pestaña 1: Venta Directa
        self.tab_venta = ttk.Frame(self.pos_notebook, padding=10)
        self.pos_notebook.add(self.tab_venta, text='🛒 Venta Directa')

        # Logo de Fondo en Venta Directa
        if self.bg_img_pos:
            bg_lbl = tk.Label(self.tab_venta, image=self.bg_img_pos, bg=BG)
            bg_lbl.place(relx=0.5, rely=0.5, anchor='center')
            bg_lbl.lower()

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

        ttk.Button(right_v, text='Quitar Item', command=self.remove_selected, bootstyle="danger", cursor="hand2").pack(fill='x', padx=10, pady=5)
        ttk.Button(right_v, text='CONFIRMAR PEDIDO', command=self.process_order, bootstyle="success", cursor="hand2", padding=10).pack(fill='x', padx=10, pady=10)

        # Pestaña 2: Cobrar Mesas
        self.tab_cobros = ttk.Frame(self.pos_notebook, padding=10)
        self.pos_notebook.add(self.tab_cobros, text='📋 Cobrar Mesas')
        
        # Logo de Fondo en Cobrar Mesas
        if self.bg_img_pos:
            bg_lbl_c = tk.Label(self.tab_cobros, image=self.bg_img_pos, bg=BG)
            bg_lbl_c.place(relx=0.5, rely=0.5, anchor='center')
            bg_lbl_c.lower()
        
        self.build_cobros_tab()

        # Cargar productos inicialmente
        self.render_products()

    def build_cobros_tab(self):
        """Construye la interfaz para cobrar pedidos de meseros."""
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
        
        # Lado derecho: Detalles y Cobro
        right_c = ttk.Frame(self.tab_cobros, width=400, bootstyle="secondary")
        right_c.pack(side='right', fill='y')
        right_c.pack_propagate(False)
        
        ttk.Label(right_c, text='DETALLE DE CUENTA', font=(None, 12, 'bold'), bootstyle="inverse-secondary", padding=10).pack(fill='x')
        self.detail_text = tk.Text(right_c, bg=PANEL, fg=FG, font=(None, 11), height=15)
        self.detail_text.pack(fill='x', padx=10, pady=10)
        self.detail_text.config(state='disabled')
        
        self.total_cobro_label = ttk.Label(right_c, text='Total a Cobrar: $0.00', font=(None, 16, 'bold'), bootstyle="inverse-secondary", padding=10)
        self.total_cobro_label.pack(fill='x')
        
        ttk.Button(right_c, text='PROCESAR PAGO', command=self.pay_order, bootstyle="success", cursor="hand2", padding=15).pack(fill='x', padx=10, pady=20)
        
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
            for it in items:
                self.detail_text.insert('end', f"{it['nombre']:<25} ${it['precio']:>6.2f}\n")
            self.detail_text.config(state='disabled')
            self.total_cobro_label.config(text=f"Total a Cobrar: ${order[1]:.2f}")

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
        
        if messagebox.askyesno('Confirmar Pago', '¿Confirmar el pago de esta cuenta?'):
            try:
                self.db.execute('UPDATE pedidos SET pagado = 1, sesion_id = ?, metodo_pago = ? WHERE id = ?', 
                                (self.session_id, 'EFECTIVO', order_id))
                messagebox.showinfo('Éxito', 'Pago procesado correctamente')
                self.refresh_unpaid_orders()
                self.detail_text.config(state='normal')
                self.detail_text.delete('1.0', 'end')
                self.detail_text.config(state='disabled')
                self.total_cobro_label.config(text="Total a Cobrar: $0.00")
            except Exception as e:
                logging.error(f"Error al procesar pago: {e}")
                messagebox.showerror('Error', 'No se pudo procesar el pago')

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
            numero = f"POS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            created_at = datetime.now().isoformat()
            usuario_id = self.user.get('id') if self.user else None
            sesion_id = self.session_id
            
            # Insertar en la base de datos
            self.db.execute('INSERT INTO pedidos (numero, items, subtotal, total, estado, canal, usuario_id, sesion_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                            (numero, items, subtotal, total, 'RECIBIDO', 'CAJA', usuario_id, sesion_id, created_at))
            
            # Registrar en auditoría
            self.db.audit_log('pedidos', 'INSERT', self.user.get('username'), f'Pedido creado: {numero}', new=items_list)
            
            messagebox.showinfo('Éxito', 'Pedido procesado correctamente')
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


class MeseroFrame(ttk.Frame):
    """
    Interfaz para Meseros.
    Permite realizar pedidos asignados a mesas o para llevar.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(parent, padding=10, *args, **kwargs)
        self.db = db
        self.user = user
        self.cart = []
        self.selected_mesa = tk.StringVar(value="Mesa 1")
        
        # Logo de Fondo (Marca de Agua) en Mesero - Usamos tk.Label para transparencia
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        self.bg_img_mes = load_image(bg_logo_path, size=(500, 500))
        if self.bg_img_mes:
            bg_lbl = tk.Label(self, image=self.bg_img_mes, bg=BG)
            bg_lbl.place(relx=0.5, rely=0.5, anchor='center')
            bg_lbl.lower()

        # --- Cabecera ---
        header = ttk.Frame(self, bootstyle="warning", padding=15)
        header.pack(fill='x')
        
        mesero_img = load_image(os.path.join('Imagenes', 'user.png'), size=(60, 60))
        if mesero_img:
            lbl = ttk.Label(header, image=mesero_img, bootstyle="inverse-warning")
            lbl.image = mesero_img
            lbl.pack(side='left', padx=10)
        
        ttk.Label(header, text='🍽️ MÓDULO DE MESERO', font=(None, 24, 'bold'), bootstyle="inverse-warning").pack(side='left', padx=10)
        ttk.Button(header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10).pack(side='right', padx=5)

        # --- Cuerpo ---
        body = ttk.Frame(self)
        body.pack(fill='both', expand=True, pady=10)

        # Lado izquierdo: Mesas y Productos
        left = ttk.Frame(body)
        left.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Logo de Fondo en Mesero (Colocado en left para visibilidad)
        if self.bg_img_mes:
            bg_lbl = tk.Label(left, image=self.bg_img_mes, bg=BG)
            bg_lbl.place(relx=0.5, rely=0.5, anchor='center')
            bg_lbl.lower()

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
        right = ttk.Frame(body, width=350, bootstyle="secondary")
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
        for idx, p in enumerate(filtered):
            r, c = divmod(idx, cols)
            card = ttk.Frame(self.products_frame, bootstyle="light", padding=15)
            card.grid(row=r, column=c, padx=12, pady=12, sticky='nsew')
            ttk.Label(card, text=p[4] or '🍽', font=(None, 40), bootstyle="inverse-light").pack(pady=5)
            ttk.Label(card, text=p[1], font=(None, 14, 'bold'), bootstyle="inverse-light", wraplength=140, justify='center').pack()
            ttk.Label(card, text=f"${p[2]:.2f}", font=(None, 16), bootstyle="warning").pack(pady=5)
            btn = ttk.Button(card, text='Añadir', command=lambda pid=p: self.add_product(pid), bootstyle="warning", cursor="hand2", padding=8)
            btn.pack(fill='x')
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


class KDSFrame(ttk.Frame):
    """
    Monitor de Cocina (KDS).
    Visualiza los pedidos pendientes y permite marcarlos como listos.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(parent, padding=20, *args, **kwargs)
        self.db = db
        self.user = user
        
        # --- Cabecera del KDS con Resaltado ---
        header = ttk.Frame(self, bootstyle="warning", padding=15)
        header.pack(fill='x', pady=(0, 20))
        
        kds_img = load_image(os.path.join('Imagenes', 'cocina.jpeg'), size=(60,60))
        if kds_img:
            lbl = ttk.Label(header, image=kds_img, bootstyle="inverse-warning")
            lbl.image = kds_img
            lbl.pack(side='left', padx=10)
            
        ttk.Label(header, text='🍳 MONITOR DE COCINA (KDS)', font=(None, 24, 'bold'), bootstyle="inverse-warning").pack(side='left', padx=10)
        
        # Botones de control (más grandes)
        ttk.Button(header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10).pack(side='right', padx=5)
        ttk.Button(header, text='Refrescar', command=self.refresh, bootstyle="light-outline", cursor="hand2", padding=10).pack(side='right', padx=5)
        
        # --- Lista de Pedidos ---
        # Listbox para ver las órdenes que aún no están 'listas' (letra más grande)
        self.listbox = tk.Listbox(self, bg=PANEL, fg=FG, font=(None, 14), bd=0, highlightthickness=0, selectbackground=ACCENT, takefocus=True)
        self.listbox.pack(fill='both', expand=True, pady=10)
        self.listbox.bind('<Return>', lambda e: self.mark_ready()) # Tecla ENTER para marcar listo
        
        footer = ttk.Frame(self)
        footer.pack(fill='x', pady=10)
        
        # Botón grande para confirmar preparación
        ttk.Button(footer, text='MARCAR COMO LISTO', command=self.mark_ready, bootstyle="success", padding=20, cursor="hand2").pack(fill='x')
        
        # Cargar datos iniciales
        self.refresh()

    def refresh(self):
        """Consulta la base de datos y actualiza la lista de pedidos activos."""
        self.listbox.delete(0, 'end')
        # Traer pedidos que NO tengan estado 'listo'
        rows = self.db.fetch_all("SELECT id, numero, items, estado, mesa FROM pedidos WHERE estado!='listo' ORDER BY id DESC LIMIT 50")
        for r in rows:
            try:
                # Parsear el JSON de items para mostrar nombres legibles
                items_obj = json.loads(r[2]) if r[2] else []
                item_names = ', '.join([f"{it.get('qty', 1)}x {it.get('nombre')}" for it in items_obj])
            except:
                item_names = r[2] or ""
            
            mesa_info = f"[{r[4]}]" if r[4] else "[CAJA]"
            self.listbox.insert('end', f" #{r[0]:<5} | {mesa_info:<10} | {r[3]:<12} | {item_names}")

    def mark_ready(self):
        """Cambia el estado de un pedido seleccionado a 'listo'."""
        sel = self.listbox.curselection()
        if not sel: return
        text = self.listbox.get(sel[0])
        # Extraer el ID del pedido desde el texto de la fila
        pid = int(text.split('|')[0].strip().lstrip('#'))
        self.db.execute('UPDATE pedidos SET estado=? WHERE id=?', ('listo', pid))
        self.refresh() # Refrescar la lista inmediatamente


class WhatsAppFrame(ttk.Frame):
    """
    Módulo de WhatsApp Web.
    Permite la conexión y gestión de mensajes con clientes.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        super().__init__(parent, padding=10, *args, **kwargs)
        self.db = db
        
        # Logo de Fondo (Marca de Agua) en WhatsApp - Usamos tk.Label para transparencia
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        self.bg_img_wa = load_image(bg_logo_path, size=(500, 500))
        if self.bg_img_wa:
            bg_lbl = tk.Label(self, image=self.bg_img_wa, bg=BG)
            bg_lbl.place(relx=0.5, rely=0.5, anchor='center')
            bg_lbl.lower()

        # --- Cabecera ---
        header = ttk.Frame(self, bootstyle="success", padding=15)
        header.pack(fill='x')
        
        wa_img = load_image(os.path.join('Imagenes', 'yappy.png'), size=(60, 60))
        if wa_img:
            lbl = ttk.Label(header, image=wa_img, bootstyle="inverse-success")
            lbl.image = wa_img
            lbl.pack(side='left', padx=10)
        
        ttk.Label(header, text='💬 WHATSAPP WEB PIK\'TA', font=(None, 24, 'bold'), bootstyle="inverse-success").pack(side='left', padx=10)
        ttk.Button(header, text='Regresar', command=lambda: self.master.select(0), bootstyle="secondary-outline", cursor="hand2", padding=10).pack(side='right', padx=5)

        # --- Cuerpo ---
        body = ttk.Frame(self)
        body.pack(fill='both', expand=True, pady=10)

        # Lado izquierdo: Lista de Chats
        left = ttk.Frame(body, width=300, bootstyle="light")
        left.pack(side='left', fill='y', padx=(0, 10))
        left.pack_propagate(False)
        
        ttk.Label(left, text='CHATS RECIENTES', font=(None, 12, 'bold'), padding=10).pack(fill='x')
        self.chat_list = tk.Listbox(left, bg="#ffffff", fg="#333333", font=(None, 11), bd=0, highlightthickness=0)
        self.chat_list.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Simulación de chats
        sample_chats = ["+507 6677-8899 (Cliente 1)", "+507 6123-4567 (Cliente 2)", "+507 6987-6543 (Cliente 3)"]
        for chat in sample_chats:
            self.chat_list.insert('end', chat)

        # Lado derecho: Área de Mensajes
        right = ttk.Frame(body, bootstyle="secondary")
        right.pack(side='right', fill='both', expand=True)
        
        # Área de chat
        self.chat_display = tk.Text(right, bg="#e5ddd5", state='disabled', font=(None, 12), padx=10, pady=10)
        self.chat_display.pack(fill='both', expand=True, padx=10, pady=(10, 0))
        
        # Logo de Fondo en WhatsApp (Dentro del display si es posible, o detrás)
        if self.bg_img_wa:
            bg_lbl = tk.Label(self.chat_display, image=self.bg_img_wa, bg="#e5ddd5")
            bg_lbl.place(relx=0.5, rely=0.5, anchor='center')
            bg_lbl.lower()
        
        # Entrada de mensaje
        input_frame = ttk.Frame(right, padding=10)
        input_frame.pack(fill='x')
        
        self.msg_entry = ttk.Entry(input_frame, font=(None, 12))
        self.msg_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        ttk.Button(input_frame, text='Enviar', bootstyle="success", command=self.send_message).pack(side='right')

        # Botón de conexión (Real)
        ttk.Button(left, text='ABRIR WHATSAPP WEB', bootstyle="success", command=self.connect_wa, padding=10).pack(fill='x', padx=10, pady=10)
        
        ttk.Label(left, text="Nota: Se abrirá en su navegador\npara mayor seguridad.", font=(None, 9), bootstyle="secondary", justify='center').pack(pady=5)

    def connect_wa(self):
        """Abre WhatsApp Web de forma integrada y silenciosa."""
        try:
            script_path = os.path.join(os.getcwd(), 'whatsapp_launcher.py')
            if os.path.exists(script_path):
                import subprocess
                # Usamos CREATE_NO_WINDOW para que no aparezca el CMD negro
                # Usamos DETACHED_PROCESS para que sea independiente
                DETACHED_PROCESS = 0x00000008
                CREATE_NO_WINDOW = 0x08000000
                
                subprocess.Popen([sys.executable, script_path], 
                               creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                               close_fds=True)
            else:
                webbrowser.open("https://web.whatsapp.com/")
        except Exception as e:
            logging.error(f"Error al lanzar WhatsApp silencioso: {e}")
            webbrowser.open("https://web.whatsapp.com/")

    def send_message(self):
        msg = self.msg_entry.get().strip()
        if msg:
            self.chat_display.config(state='normal')
            self.chat_display.insert('end', f"Tú: {msg}\n", "sent")
            self.chat_display.config(state='disabled')
            self.msg_entry.delete(0, 'end')

class AdminFrame(ttk.Frame):
    """
    Panel de Administración con sistema de tarjetas similar al principal.
    Permite gestionar el inventario, usuarios y seguridad.
    """
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        super().__init__(parent, padding=20, *args, **kwargs)
        self.db = db
        
        # --- Cabecera del Panel Admin ---
        self.header = ttk.Frame(self, bootstyle="success", padding=15)
        self.header.pack(fill='x', pady=(0, 20))
        
        img = load_image(os.path.join('Imagenes', 'admin.jpeg'), size=(60,60))
        if img:
            lbl = ttk.Label(self.header, image=img, bootstyle="inverse-success")
            lbl.image = img
            lbl.pack(side='left', padx=10)

        self.title_lbl = ttk.Label(self.header, text='📊 PANEL DE ADMINISTRACIÓN', font=(None, 24, 'bold'), bootstyle="inverse-success")
        self.title_lbl.pack(side='left', padx=10)
        
        # Botón para regresar al dashboard principal
        self.btn_back_main = ttk.Button(self.header, text='Regresar', command=lambda: self.master.select(0), bootstyle="light-outline", cursor="hand2", padding=10)
        self.btn_back_main.pack(side='right', padx=5)
        
        # Botón para regresar al "menú de cuadritos" del admin (inicialmente oculto)
        self.btn_back_admin = ttk.Button(self.header, text='Volver al Admin', command=self.show_admin_menu, bootstyle="light-outline", cursor="hand2", padding=10)

        # --- Contenedor Principal con Notebook Oculto ---
        self.notebook = ttk.Notebook(self, style='Hidden.TNotebook')
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
            inner.bind("<Button-1>", lambda e: cmd())
            return card

        # Tarjetas del Admin con sus imágenes correspondientes
        c1 = make_admin_card(cards_wrap, 'inventario.jpg', 'Inventario', 'Control de stock y materia prima.', lambda: self.open_section(1, "GESTIÓN DE INVENTARIO"))
        c1.grid(row=0, column=0, padx=20, pady=20)

        c2 = make_admin_card(cards_wrap, 'user.png', 'Usuarios', 'Gestión de personal y accesos.', lambda: self.open_section(2, "GESTIÓN DE USUARIOS"))
        c2.grid(row=0, column=1, padx=20, pady=20)

        c3 = make_admin_card(cards_wrap, 'seguridad.png', 'Seguridad', 'Auditoría y respaldos de DB.', lambda: self.open_section(3, "SEGURIDAD Y AUDITORÍA"))
        c3.grid(row=0, column=2, padx=20, pady=20)

        c4 = make_admin_card(cards_wrap, 'pos.png', 'Menú / Productos', 'Gestión de productos y precios.', lambda: self.open_section(4, "GESTIÓN DE MENÚ"))
        c4.grid(row=0, column=3, padx=20, pady=20)

        for i in range(4): cards_wrap.columnconfigure(i, weight=1)

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
        ttk.Button(container, text='INICIAR SESIÓN', bootstyle="info", command=self.try_login, cursor="hand2", padding=15).pack(fill='x', pady=(25, 10))
        ttk.Button(container, text='Cancelar', bootstyle="secondary-outline", command=self.cancel, cursor="hand2", padding=10).pack(fill='x')

        # Pie de página con Derechos de Autor
        ttk.Label(container, text='© YAFA SOLUTIONS', font=(None, 10, 'bold'), bootstyle="secondary").pack(pady=(20, 0))

        # Configuración de foco inicial y atajos de teclado
        self.username.focus_set()
        self.bind('<Return>', lambda e: self.try_login()) # Enter para loguear
        self.bind('<Escape>', lambda e: self.cancel())    # Escape para cerrar

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
        while not self.user:
            login = LoginWindow(self, self.db)
            self.wait_window(login)
            if not self.user:
                if not messagebox.askretrycancel("Login Requerido", "¿Desea intentar iniciar sesión nuevamente?"):
                    self.destroy()
                    return

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

    def _check_session_periodically(self):
        """Verifica si la sesión sigue siendo válida."""
        if self.session_token and not session_manager.validate_session(self.session_token):
            messagebox.showwarning("Sesión Expirada", "Su sesión ha expirado por inactividad. Por favor, inicie sesión de nuevo.")
            self.logout()
        else:
            # Seguir verificando cada minuto
            self.after(60000, self._check_session_periodically)

    def _on_global_return(self, event):
        """Manejador global para la tecla ENTER."""
        w = self.focus_get()
        if not w: return
        if isinstance(w, (ttk.Button, tk.Button)):
            w.invoke()
        elif hasattr(w, '_card_cmd'):
            w._card_cmd()

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
        ttk.Button(header, text='Cerrar Sesión', command=self.logout, bootstyle="danger", cursor="hand2", padding=12).pack(side='right', pady=10)

        # --- Contenedor de Pestañas (Navegación Principal) ---
        # Usamos un estilo personalizado 'Hidden.TNotebook' para ocultar las pestañas superiores
        # Esto nos permite simular una aplicación de una sola página (SPA) en el menú principal
        style = ttk.Style()
        style.layout('Hidden.TNotebook.Tab', []) 
        style.configure('Hidden.TNotebook', borderwidth=0, highlightthickness=0)
        
        self.notebook = ttk.Notebook(self, style='Hidden.TNotebook')
        self.notebook.pack(fill='both', expand=True, padx=20, pady=20)

        role = self.user.get('rol', '').lower()

        # --- Dashboard (Pestaña Inicial) ---
        home = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(home, text='Inicio')
        self.notebook.select(home)

        # Usamos un Canvas que ocupe TODO el espacio disponible
        self.dash_canvas = tk.Canvas(home, bg=BG, highlightthickness=0)
        self.dash_canvas.pack(fill='both', expand=True)

        # Cargar logo de fondo (Agua)
        bg_logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(bg_logo_path) and PIL_AVAILABLE:
            # Guardamos la imagen original para redimensionar sin perder calidad
            self.bg_image_raw = Image.open(bg_logo_path)
            self.bg_photo = None # Se generará dinámicamente
            
            def update_background(e):
                # Redimensionar para cubrir todo el canvas (STRETCH)
                cw, ch = self.dash_canvas.winfo_width(), self.dash_canvas.winfo_height()
                if cw < 10 or ch < 10: return
                
                # Redimensionar imagen al tamaño actual del canvas
                img_resized = self.bg_image_raw.resize((cw, ch), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(img_resized)
                
                self.dash_canvas.delete("bg_img")
                # Dibujamos la imagen centrada cubriendo todo el canvas
                self.dash_canvas.create_image(cw//2, ch//2, image=self.bg_photo, tags="bg_img")
                # Aseguramos que el logo esté detrás de todo lo que se ponga en el canvas
                self.dash_canvas.tag_lower("bg_img")
            
            # El evento Configure se dispara al cambiar el tamaño de la ventana
            self.dash_canvas.bind("<Configure>", update_background)

        # Contenedor para las tarjetas (dentro del canvas como una ventana)
        # IMPORTANTE: El fondo de cards_content debe ser el mismo que el del canvas para "transparencia"
        cards_content = tk.Frame(self.dash_canvas, bg=BG)
        # Colocamos el contenedor de tarjetas centrado sobre el canvas
        self.dash_canvas.create_window(0, 0, window=cards_content, anchor="nw", tags="cards_win")
        
        def resize_cards_layer(e):
            # Hacer que el layer de tarjetas ocupe todo el canvas
            self.dash_canvas.itemconfig("cards_win", width=e.width, height=e.height)
        
        self.dash_canvas.bind("<Configure>", lambda e: (update_background(e), resize_cards_layer(e)), add="+")

        # El contenido real de las tarjetas se centra dentro de cards_content
        # Usamos un Frame interno para agrupar las tarjetas y centrarlo
        cards_inner = tk.Frame(cards_content, bg=BG)
        cards_inner.place(relx=0.5, rely=0.5, anchor='center')

        def make_card(parent, img_name, title, desc, cmd=None, style_color="info"):
            """Crea una tarjeta interactiva para el dashboard principal (más grande y atractiva)."""
            # El contenedor principal 'card' tiene un padding que simula el borde
            card = ttk.Frame(parent, bootstyle="secondary", padding=2, cursor="hand2", takefocus=True, width=220, height=260)
            card.pack_propagate(False)
            card._card_cmd = cmd
            
            # El contenedor interno 'inner' para el contenido real
            inner = ttk.Frame(card, padding=10) 
            inner.pack(fill='both', expand=True)

            img = None
            if img_name:
                path = os.path.join('Imagenes', img_name)
                img = load_image(path, size=(90, 90)) # Imagen un poco más grande
            
            if img:
                lbl = ttk.Label(inner, image=img)
                lbl.image = img
                lbl.pack(pady=10)
                lbl.bind("<Button-1>", lambda e: cmd() if cmd else None)
            else:
                lbl = ttk.Label(inner, text='📦', font=(None, 45))
                lbl.pack(pady=10)
                lbl.bind("<Button-1>", lambda e: cmd() if cmd else None)

            # Título llamativo
            t_lbl = ttk.Label(inner, text=title, font=(None, 24, 'bold'), wraplength=200, justify='center') 
            t_lbl.pack(pady=5)
            t_lbl.bind("<Button-1>", lambda e: cmd() if cmd else None)

            # Descripción legible
            d_lbl = ttk.Label(inner, text=desc, wraplength=180, justify='center', font=(None, 12))
            d_lbl.pack(pady=5, fill='both', expand=True)
            d_lbl.bind("<Button-1>", lambda e: cmd() if cmd else None)

            # --- Efecto 3D / Pop-out ---
            # Al pasar el mouse, el borde se vuelve más grueso y brillante (simulando que sale hacia el frente)
            def on_enter(e):
                card.configure(bootstyle=style_color, padding=5) # Borde grueso (Pop-out)
                inner.configure(bootstyle="light") # Fondo más claro para resaltar
                t_lbl.configure(bootstyle=f"inverse-light")
                d_lbl.configure(bootstyle=f"inverse-light")
            
            def on_leave(e):
                card.configure(bootstyle="secondary", padding=2) # Vuelve a la normalidad
                inner.configure(bootstyle="default")
                t_lbl.configure(bootstyle="default")
                d_lbl.configure(bootstyle="default")

            def on_focus_in(e): on_enter(None)
            def on_focus_out(e): on_leave(None)

            # Vincular eventos
            card.bind("<Enter>", on_enter); card.bind("<Leave>", on_leave)
            card.bind("<FocusIn>", on_focus_in); card.bind("<FocusOut>", on_focus_out)
            
            # Clic en cualquier parte activa el comando
            card.bind("<Button-1>", lambda e: cmd() if cmd else None)
            inner.bind("<Button-1>", lambda e: cmd() if cmd else None)
            
            return card

        # Generación de tarjetas en el grid
        c1 = make_card(cards_inner, 'WhatsApp.jpg', 'WhatsApp Web', 'Gestión de clientes y pedidos.', cmd=self.open_whatsapp, style_color="success")
        c1.grid(row=0, column=0, padx=20, pady=20)
        
        c2 = make_card(cards_inner, 'pos.png', 'Caja / POS', 'Ventas, cobros y pedidos.', cmd=self.open_pos, style_color="info")
        c2.grid(row=0, column=1, padx=20, pady=20)
        
        c3 = make_card(cards_inner, 'user.png', 'Mesero', 'Pedidos a mesa y llevar.', cmd=self.open_mesero, style_color="warning")
        c3.grid(row=0, column=2, padx=20, pady=20)
        
        c4 = make_card(cards_inner, 'cocina.jpeg', 'Cocina (KDS)', 'Gestión de órdenes en cocina.', cmd=self.open_kds, style_color="danger")
        c4.grid(row=0, column=3, padx=20, pady=20)
        
        c5 = make_card(cards_inner, 'admin.jpeg', 'Admin', 'Inventario y configuración.', cmd=self.open_admin, style_color="primary")
        c5.grid(row=0, column=4, padx=20, pady=20)

        # Configurar el grid para que las tarjetas se distribuyan uniformemente
        for i in range(5):
            cards_inner.columnconfigure(i, weight=1)
            cards_inner.rowconfigure(0, weight=1)

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
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                self.notebook.select(i)
                # Lanzar WhatsApp automáticamente al entrar
                if hasattr(frame, 'connect_wa'):
                    frame.connect_wa()
                return

    def open_pos(self):
        """Cambia a la pestaña del Punto de Venta."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Caja / POS':
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                if hasattr(frame, 'render_products'): frame.render_products()
                if hasattr(frame, 'refresh_unpaid_orders'): frame.refresh_unpaid_orders()
                self.notebook.select(i); return

    def open_mesero(self):
        """Cambia a la pestaña de Mesero."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Mesero':
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                if hasattr(frame, 'render_products'): frame.render_products()
                self.notebook.select(i); return

    def open_kds(self):
        """Cambia a la pestaña de Cocina."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Cocina (KDS)':
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                if hasattr(frame, 'refresh'): frame.refresh()
                self.notebook.select(i); return

    def open_admin(self):
        """Cambia a la pestaña de Administración."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Admin':
                frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                if hasattr(frame, 'refresh'): frame.refresh()
                self.notebook.select(i); return

    def logout(self):
        """Cierra la sesión del usuario y termina la aplicación."""
        try:
            if self.session_token:
                session_manager.close_session(self.session_token)
            
            if getattr(self, 'user', None):
                # Registrar el evento de salida en los logs
                self.db.log_access(self.user.get('id'), self.user.get('username'), 'logout')
        except Exception:
            logging.exception('Error al registrar logout')
        self.destroy() # Cierra todas las ventanas y termina el proceso


# =============================================================================
# PUNTO DE ENTRADA DEL PROGRAMA
# =============================================================================
if __name__ == '__main__':
    multiprocessing.freeze_support()
    # Crear e iniciar la aplicación principal
    app = App()
    app.mainloop()
