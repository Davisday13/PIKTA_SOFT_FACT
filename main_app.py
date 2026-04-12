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
from ttkbootstrap.constants import *
import sqlite3
import json
import os
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

        # --- Cuerpo Principal ---
        body = ttk.Frame(self)
        body.pack(fill='both', expand=True, pady=10)

        # Lado izquierdo: Catálogo de productos
        left = ttk.Frame(body)
        left.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Filtro de categorías (Combos, Extras, Bebidas) - Botones más grandes
        self.categories = ['🍔 Combos', '🍟 Extras', '🥤 Bebidas']
        self.selected_category = tk.StringVar(value=self.categories[0])
        cat_frame = ttk.Frame(left)
        cat_frame.pack(fill='x', pady=(0, 15))
        for c in self.categories:
            ttk.Radiobutton(cat_frame, text=c, variable=self.selected_category, value=c, 
                           command=self.render_products, bootstyle="info-toolbutton", padding=10).pack(side='left', padx=5)

        # Contenedor con scroll para los productos
        self.products_canvas = tk.Canvas(left, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(left, orient="vertical", command=self.products_canvas.yview)
        self.products_frame = ttk.Frame(self.products_canvas)

        self.products_frame.bind(
            "<Configure>",
            lambda e: self.products_canvas.configure(scrollregion=self.products_canvas.bbox("all"))
        )
        self.products_canvas.create_window((0, 0), window=self.products_frame, anchor="nw")
        self.products_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.products_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Lado derecho: Resumen de la orden (Carrito)
        right = ttk.Frame(body, width=350, bootstyle="secondary")
        right.pack(side='right', fill='y')
        right.pack_propagate(False) # Mantener ancho fijo
        
        ttk.Label(right, text='ORDEN ACTUAL', font=(None, 12, 'bold'), bootstyle="inverse-secondary", padding=10).pack(fill='x')
        
        # Lista visual de productos seleccionados
        self.cart_list = tk.Listbox(right, bg=PANEL, fg=FG, font=(None, 11), bd=0, highlightthickness=0, selectbackground=ACCENT)
        self.cart_list.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Etiqueta de total a pagar
        self.total_label = ttk.Label(right, text='Total: $0.00', font=(None, 14, 'bold'), bootstyle="inverse-secondary", padding=10)
        self.total_label.pack(fill='x')

        # Botones de gestión de carrito
        ttk.Button(right, text='Quitar Item', command=self.remove_selected, bootstyle="danger", cursor="hand2").pack(fill='x', padx=10, pady=5)
        ttk.Button(right, text='CONFIRMAR PEDIDO', command=self.process_order, bootstyle="success", cursor="hand2", padding=10).pack(fill='x', padx=10, pady=10)

        # Cargar productos inicialmente
        self.render_products()

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
        rows = self.db.fetch_all("SELECT id, numero, items, estado FROM pedidos WHERE estado!='listo' ORDER BY id DESC LIMIT 50")
        for r in rows:
            try:
                # Parsear el JSON de items para mostrar nombres legibles
                items_obj = json.loads(r[2]) if r[2] else []
                item_names = ', '.join([f"{it.get('qty', 1)}x {it.get('nombre')}" for it in items_obj])
            except:
                item_names = r[2] or ""
            
            self.listbox.insert('end', f" #{r[0]:<5} | {r[3]:<12} | {item_names}")

    def mark_ready(self):
        """Cambia el estado de un pedido seleccionado a 'listo'."""
        sel = self.listbox.curselection()
        if not sel: return
        text = self.listbox.get(sel[0])
        # Extraer el ID del pedido desde el texto de la fila
        pid = int(text.split('|')[0].strip().lstrip('#'))
        self.db.execute('UPDATE pedidos SET estado=? WHERE id=?', ('listo', pid))
        self.refresh() # Refrescar la lista inmediatamente


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

        for i in range(3): cards_wrap.columnconfigure(i, weight=1)

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
        actions = ttk.Labelframe(self.inv_frame, text="Acciones de Ajuste Rápido", padding=15, bootstyle="success")
        actions.pack(fill='x', pady=(20, 0))
        
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
        form = ttk.Labelframe(self.users_frame, text='Registrar Nuevo Usuario', bootstyle="success", padding=15)
        form.pack(fill='x', pady=10)
        
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
        metrics_frame = ttk.Labelframe(self.security_frame, text="Estado de Seguridad del Sistema", padding=20, bootstyle="info")
        metrics_frame.pack(fill='x', pady=(0, 20))
        
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


class LoginWindow(ttk.Toplevel):
    """
    Ventana de Inicio de Sesión.
    Controla el acceso al sistema mediante credenciales.
    """
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.user = None # Guardará los datos del usuario si el login es exitoso
        self.title('Login - PIK\'TA SOFT')
        self.resizable(False, False)
        center_window(self, 400, 450)
        self.grab_set() # Bloquea interacción con la ventana principal hasta que se cierre esta

        container = ttk.Frame(self, padding=30)
        container.pack(fill='both', expand=True)

        # Logo de la empresa en el login
        logo_path = os.path.join('Imagenes', 'pikata.png')
        self.logo_img = load_image(logo_path, size=(120, 120))
        if self.logo_img:
            logo_lbl = ttk.Label(container, image=self.logo_img)
            logo_lbl.pack(pady=(0, 20))
        
        ttk.Label(container, text='Bienvenido', font=(None, 24, 'bold')).pack(pady=10)
        ttk.Label(container, text='Ingrese sus credenciales', font=(None, 14)).pack(pady=(0, 30))

        # Campo de Usuario con fuente más grande
        self.username = ttk.Entry(container, font=(None, 14), bootstyle="info")
        self.username.pack(fill='x', pady=10)
        self.username.insert(0, 'Usuario')
        self.username.bind('<FocusIn>', lambda e: self.username.delete(0, 'end') if self.username.get() == 'Usuario' else None)

        # Campo de Contraseña con fuente más grande
        self.password = ttk.Entry(container, show='*', font=(None, 14), bootstyle="info")
        self.password.pack(fill='x', pady=10)

        # Botones de login y cancelación más grandes
        ttk.Button(container, text='INICIAR SESIÓN', bootstyle="info", command=self.try_login, cursor="hand2", padding=15).pack(fill='x', pady=(25, 10))
        ttk.Button(container, text='Cancelar', bootstyle="secondary-outline", command=self.cancel, cursor="hand2", padding=10).pack(fill='x')

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
            # Crear sesión en el gestor de sesiones
            self.session_token = session_manager.create_session(user_data)
            self.user = user_data # Para compatibilidad con el código existente
            try:
                self.db.log_access(self.user['id'], self.user['username'], 'login')
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
        self.title('PIK\'TA SOFT - Sistema de Restaurante')
        self.db = DatabaseManager()
        self.user = None
        self.session_token = None

        # --- Bucle de Login Persistente ---
        while not self.user:
            self.withdraw()
            login = LoginWindow(self, self.db)
            self.wait_window(login)
            if getattr(login, 'user', None):
                self.user = login.user
                self.session_token = getattr(login, 'session_token', None)
            else:
                if not messagebox.askretrycancel("Login Requerido", "¿Desea intentar iniciar sesión nuevamente?"):
                    self.destroy()
                    return

        self.deiconify()
        center_window(self, 1300, 900) # Ventana un poco más grande
        
        # Configurar navegación global por teclado
        self.bind_all('<Return>', self._on_global_return)
        
        # Iniciar verificación periódica de sesión (cada 1 minuto)
        self.after(60000, self._check_session_periodically)
        
        self.build()

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
        ttk.Label(user_info, text='SISTEMA PIK\'TA SOFT FACT', font=(None, 26, 'bold'), bootstyle="inverse-secondary").pack(anchor='w')

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
        home = ttk.Frame(self.notebook, padding=30)
        self.notebook.add(home, text='Inicio')
        # Aseguramos que el Dashboard sea la pestaña seleccionada al iniciar
        self.notebook.select(home)

        cards_wrap = ttk.Frame(home)
        cards_wrap.pack(fill='both', expand=True)

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

        # Generación de tarjetas en el grid (Sin sticky para que mantengan su tamaño fijo)
        # Se crean 4 tarjetas principales: Simulador, POS, KDS y Admin
        c1 = make_card(cards_wrap, 'avion.jpeg', 'Simulador', 'Vista de flujos y procesos.', cmd=lambda: self.notebook.select(0), style_color="secondary")
        c1.grid(row=0, column=0, padx=20, pady=20)
        
        c2 = make_card(cards_wrap, 'pos.png', 'Caja / POS', 'Ventas, cobros y pedidos.', cmd=self.open_pos, style_color="info")
        c2.grid(row=0, column=1, padx=20, pady=20)
        
        c3 = make_card(cards_wrap, 'cocina.jpeg', 'Cocina (KDS)', 'Gestión de órdenes en cocina.', cmd=self.open_kds, style_color="warning")
        c3.grid(row=0, column=2, padx=20, pady=20)
        
        c4 = make_card(cards_wrap, 'admin.jpeg', 'Admin', 'Inventario y configuración.', cmd=self.open_admin, style_color="success")
        c4.grid(row=0, column=3, padx=20, pady=20)

        # Configurar el grid para que las tarjetas se distribuyan uniformemente
        for i in range(4):
            cards_wrap.columnconfigure(i, weight=1)
            cards_wrap.rowconfigure(0, weight=1)

        # --- Carga Dinámica de Pestañas según Rol ---
        # Solo se añaden las pestañas a las que el usuario tiene permiso de acceder.
        # IMPORTANTE: Se añadió 'administrador' y 'admin' para asegurar el acceso total.
        if role in ('administrador', 'admin', 'mesero', 'cajera', 'supervisor'):
            pos_tab = POSFrame(self.notebook, self.db, user=self.user)
            self.notebook.add(pos_tab, text='Caja / POS')

        if role in ('administrador', 'admin', 'cocina'):
            kds_tab = KDSFrame(self.notebook, self.db, user=self.user)
            self.notebook.add(kds_tab, text='Cocina (KDS)')

        if role in ('administrador', 'admin', 'supervisor', 'super'):
            admin_tab = AdminFrame(self.notebook, self.db)
            self.notebook.add(admin_tab, text='Admin')

        # --- Atajos de Teclado Globales ---
        # CTRL + P para POS, CTRL + K para KDS, CTRL + A para Admin
        self.bind_all('<Control-p>', lambda e: self.open_pos() if role in ('administrador','admin','mesero','cajera','supervisor') else None)
        self.bind_all('<Control-k>', lambda e: self.open_kds() if role in ('administrador','admin','cocina') else None)
        self.bind_all('<Control-a>', lambda e: self.open_admin() if role in ('administrador','admin','supervisor') else None)

    def open_pos(self):
        """Cambia a la pestaña del Punto de Venta."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Caja / POS':
                self.notebook.select(i); return

    def open_kds(self):
        """Cambia a la pestaña de Cocina."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Cocina (KDS)':
                self.notebook.select(i); return

    def open_admin(self):
        """Cambia a la pestaña de Administración."""
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Admin':
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
    # Crear e iniciar la aplicación principal
    app = App()
    app.mainloop()
