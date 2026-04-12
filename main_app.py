"""
main_app.py - Interfaz de escritorio estilo 'web' (Tkinter)

Este archivo contiene una versión de escritorio del panel del
restaurante (POS, KDS, Admin) adaptada desde la carpeta `web/`.

- `DatabaseManager`: inicializa y gestiona la base de datos SQLite
- `LoginWindow`: diálogo de inicio de sesión y control de roles
- `App`: ventana principal / launcher que abre POS, KDS y Admin
- `POSWindow`, `KDSWindow`, `AdminWindow`: ventanas operativas

Notas:
- Se aplica un tema oscuro consistente en todas las ventanas
- Las migraciones de tablas son idempotentes para evitar errores
  por columnas ya añadidas.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import json
import os
from datetime import datetime
import logging
import sys
import tempfile

logging.basicConfig(filename='error_log.txt', filemode='a', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# Global exception handlers: ensure all uncaught exceptions end up in error_log.txt
def _log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = _log_uncaught_exceptions

def _tk_report_callback_exception(self, exc, val, tb):
    logging.error('Tkinter callback exception', exc_info=(exc, val, tb))

tk.Tk.report_callback_exception = _tk_report_callback_exception

# Nombre real de la base de datos en el repo
DB_NAME = "PIk'TADB.db"
# Tema de colores (oscuro, inspirado en el web mock)
BG = '#0F172A'
PANEL = '#1E293B'
FG = '#FFFFFF'
ACCENT = '#0ea5e9'
OK = '#10b981'
WARN = '#f59e0b'
ERR = '#ef4444'

# Image helper: prefer Pillow for JPEG support, fallback to tkinter.PhotoImage for PNG
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

def load_image(path, size=None):
    """Load image from `path`. If Pillow available can resize JPEG/PNG; otherwise use PhotoImage for PNG/GIF.

    Returns a Tk image object or None on failure.
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
            # tkinter.PhotoImage supports PNG/GIF
            img = tk.PhotoImage(file=path)
            # optional zoom/ subsample not applied here
            return img
    except Exception:
        return None


def center_window(win, width, height):
    """Center a Tk window on screen with given width and height."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 3
    win.geometry(f"{width}x{height}+{x}+{y}")


class DatabaseManager:
    """Manager mínimo para operaciones SQLite y migraciones seguras."""

    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Crea tablas necesarias y aplica alteraciones sólo si faltan columnas."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                rol TEXT NOT NULL,
                nombre_completo TEXT
            )''')

            cur.execute('''CREATE TABLE IF NOT EXISTS productos_menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                categoria TEXT,
                emoji TEXT,
                disponible BOOLEAN DEFAULT 1
            )''')

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
                usuario_id INTEGER
            )''')

            cur.execute('''CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingrediente TEXT NOT NULL UNIQUE,
                cantidad REAL NOT NULL DEFAULT 0,
                unidad TEXT NOT NULL,
                stock_minimo REAL NOT NULL DEFAULT 0
            )''')

            # Asegurar columnas adicionales (si el schema previo las creó de otra forma)
            self._ensure_column('productos_menu', 'categoria', 'TEXT')
            self._ensure_column('productos_menu', 'emoji', 'TEXT')
            self._ensure_column('pedidos', 'canal', 'TEXT')
            self._ensure_column('pedidos', 'usuario_id', 'INTEGER')
            self._ensure_column('pedidos', 'sesion_id', 'INTEGER')
            self._ensure_column('pedidos', 'created_at', 'TEXT')

            # Seed seguros (no duplicarán por UNIQUE)
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
                    cur.execute('INSERT OR IGNORE INTO usuarios (username, password, rol, nombre_completo) VALUES (?,?,?,?)', (u, p, r, n))
                except Exception as e:
                    logging.error(f"Seed usuarios error: {e}")

            # Tabla de registros de acceso (login/logout/acciones)
            cur.execute('''CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT,
                details TEXT,
                created_at TEXT
            )''')

            # Tabla sesiones de caja
            cur.execute('''CREATE TABLE IF NOT EXISTS caja_sesiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                inicio TEXT,
                inicial REAL DEFAULT 0,
                estado TEXT DEFAULT 'ABIERTO',
                cierre_total REAL,
                cierre_at TEXT
            )''')

            conn.commit()

    def _ensure_column(self, table, column, col_type):
        """Añade una columna sólo si no existe (para migraciones seguras)."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(f"PRAGMA table_info({table})")
                cols = [r[1] for r in cur.fetchall()]
                if column not in cols:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                    conn.commit()
            except Exception as e:
                logging.error(f"Error adding column {column} to {table}: {e}")

    def log_access(self, user_id, username, action, details=''):
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute('INSERT INTO access_logs (user_id, username, action, details, created_at) VALUES (?,?,?,?,?)',
                            (user_id, username, action, details, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            logging.exception(f'Error logging access: {e}')

    def fetch_all(self, query, params=()):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def fetch_one(self, query, params=()):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()

    def execute(self, query, params=()):
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                return cur
        except Exception as e:
            logging.exception(f'DB execute error: {e} - Query: {query} - Params: {params}')
            raise


class POSFrame(tk.Frame):
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        # accept user from kwargs
        user = kwargs.pop('user', None)
        super().__init__(parent, bg='#0B1220', *args, **kwargs)
        self.db = db
        self.user = user
        self.session_id = None
        self.cart = []
        header = tk.Frame(self, bg='#0B1220')
        header.pack(fill='x', padx=12, pady=8)
        pos_img = load_image(os.path.join('Imagenes', 'pos.png'), size=(48,48)) or load_image(os.path.join('Imagenes', 'pos.jpeg'), size=(48,48))
        if pos_img:
            tk.Label(header, image=pos_img, bg='#0B1220').pack(side='left', padx=6)
            self._pos_img = pos_img
        tk.Label(header, text='🛒 POS - Punto de Venta Intelligent', bg='#0B1220', fg='white', font=(None, 16, 'bold')).pack(side='left')
        # Caja controls
        tk.Button(header, text='Abrir Caja', command=self.open_caja, bg=ACCENT, fg='white').pack(side='right', padx=6)
        tk.Button(header, text='Cerrar Caja', command=self.cerrar_caja, bg=ERR, fg='white').pack(side='right', padx=6)

        body = tk.Frame(self, bg='#0B1220')
        body.pack(fill='both', expand=True, padx=12, pady=6)

        # Left: products area
        left = tk.Frame(body, bg='#0B1220')
        left.pack(side='left', fill='both', expand=True)

        # categories
        self.categories = ['🍔 Combos', '🍟 Extras', '🥤 Bebidas']
        self.selected_category = tk.StringVar(value=self.categories[0])
        cat_frame = tk.Frame(left, bg='#0B1220')
        cat_frame.pack(fill='x', pady=6)
        for c in self.categories:
            b = tk.Button(cat_frame, text=c, command=lambda cc=c: self.select_category(cc), bg=PANEL, fg=FG)
            b.pack(side='left', padx=6)

        self.products_frame = tk.Frame(left, bg='#0B1220')
        self.products_frame.pack(fill='both', expand=True, pady=6)

        # Right: sidebar carrito (fixed width ~400)
        self.cart_frame = tk.Frame(body, bg=PANEL, width=400)
        self.cart_frame.pack(side='right', fill='y')
        self.cart_frame.pack_propagate(False)
        tk.Label(self.cart_frame, text='Orden Actual', bg=PANEL, fg=FG, font=(None, 14, 'bold')).pack(pady=10)
        self.cart_list = tk.Listbox(self.cart_frame)
        self.cart_list.pack(fill='both', expand=True, padx=8, pady=6)
        tk.Button(self.cart_frame, text='Quitar seleccionado', command=self.remove_selected, bg=ERR, fg='white').pack(fill='x', padx=8, pady=4)
        tk.Button(self.cart_frame, text='Confirmar y Enviar', bg=ACCENT, fg='white', command=self.process_order).pack(fill='x', padx=8, pady=8)

        # initial render
        self.render_products()

    def render_products(self):
        for w in self.products_frame.winfo_children():
            w.destroy()
        products = self.db.fetch_all('SELECT id, nombre, precio, categoria, emoji FROM productos_menu')
        # filter by category
        filtered = [p for p in products if (p[3] or '').strip() == self.selected_category.get()] if products else []
        if not filtered:
            # fallback sample
            filtered = [(1, 'Combo Clásico', 5.5, '🍔 Combos', '🍔'), (4, 'Papas fritas', 1.5, '🍟 Extras', '🍟')]

        # grid layout
        cols = 3
        for idx, p in enumerate(filtered):
            r = idx // cols
            c = idx % cols
            card = tk.Frame(self.products_frame, bg='white', padx=12, pady=12)
            card.grid(row=r, column=c, padx=8, pady=8, sticky='n')
            tk.Label(card, text=p[4] or '🍽', font=(None, 28)).pack()
            tk.Label(card, text=p[1], font=(None, 10, 'bold')).pack()
            tk.Label(card, text=f"${p[2]:.2f}", fg=ACCENT, font=(None, 10, 'bold')).pack()
            tk.Button(card, text='Agregar', command=lambda pid=p: self.add_product(pid), bg=OK, fg='white').pack(pady=6)
        for i in range(cols):
            self.products_frame.columnconfigure(i, weight=1)

    def add_product(self, product):
        self.cart.append(product)
        self.cart_list.insert('end', f"{product[1]} - {product[2]}")

    def remove_selected(self):
        sel = self.cart_list.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            # remove by index from cart list and listbox
            del self.cart[idx]
        except Exception:
            pass
        self.cart_list.delete(idx)

    def process_order(self):
        if not self.cart:
            messagebox.showinfo('Aviso', 'El carrito está vacío')
            return
        # Inserta pedido con totales calculados y items estructurados
        items_list = [{'id': p[0], 'nombre': p[1], 'precio': p[2]} for p in self.cart]
        items = json.dumps(items_list, ensure_ascii=False)
        subtotal = sum((p.get('precio') or 0) for p in items_list)
        total = subtotal
        try:
            numero = f"POS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            created_at = datetime.now().isoformat()
            usuario_id = self.user.get('id') if self.user else None
            sesion_id = self.session_id
            self.db.execute('INSERT INTO pedidos (numero, items, subtotal, total, estado, canal, usuario_id, sesion_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                            (numero, items, subtotal, total, 'RECIBIDO', 'CAJA', usuario_id, sesion_id, created_at))
            messagebox.showinfo('OK', 'Pedido procesado')
        except Exception as e:
            logging.error(f'Error procesando pedido POS: {e}')
            messagebox.showerror('Error', 'No se pudo crear el pedido')
        self.cart.clear()
        self.cart_list.delete(0, 'end')

    def open_caja(self):
        if self.session_id:
            messagebox.showinfo('Caja', 'Ya hay una sesión de caja abierta')
            return
        inicial = simpledialog.askfloat('Abrir Caja', 'Monto inicial:', minvalue=0.0)
        if inicial is None:
            return
        usuario_id = self.user.get('id') if self.user else None
        inicio = datetime.now().isoformat()
        try:
            cur = self.db.execute('INSERT INTO caja_sesiones (usuario_id, inicio, inicial, estado) VALUES (?,?,?,?)', (usuario_id, inicio, inicial, 'ABIERTO'))
            self.session_id = cur.lastrowid
            messagebox.showinfo('Caja', f'Caja abierta (ID {self.session_id})')
        except Exception as e:
            logging.exception(f'Error abriendo caja: {e}')
            messagebox.showerror('Error', 'No se pudo abrir la caja')

    def cerrar_caja(self):
        if not self.session_id:
            messagebox.showwarning('Caja', 'No hay sesión de caja abierta')
            return
        # calcular totales de esta sesion y formatear reporte monoespaciado
        cierre_at = datetime.now().isoformat()
        rows = self.db.fetch_all('SELECT id, numero, total, items FROM pedidos WHERE sesion_id = ? AND canal = ?', (self.session_id, 'CAJA'))
        detalles = []
        sum_total = 0.0
        for r in rows:
            pid = r[0]
            numero = r[1]
            total_p = float(r[2] or 0)
            sum_total += total_p
            try:
                items_obj = json.loads(r[3]) if r[3] else []
                item_names = ', '.join([it.get('nombre') for it in items_obj])
            except Exception:
                item_names = (r[3] or '')[:60]
            detalles.append((pid, numero, total_p, item_names))

        # fetch inicio and inicial
        caja_row = self.db.fetch_one('SELECT inicial, inicio FROM caja_sesiones WHERE id = ?', (self.session_id,)) or (0.0, '')
        inicial = float(caja_row[0] or 0)
        inicio_ts = caja_row[1] or ''

        try:
            self.db.execute('UPDATE caja_sesiones SET estado = ?, cierre_total = ?, cierre_at = ? WHERE id = ?', ('CERRADO', sum_total, cierre_at, self.session_id))
        except Exception:
            logging.exception('Error cerrando caja')

        # Build monospaced report
        lines = []
        lines.append('***** CIERRE DE CAJA *****')
        lines.append(f'Caja ID: {self.session_id}    Usuario: {self.user.get("username") if self.user else ""}')
        lines.append(f'Inicio: {inicio_ts}')
        lines.append(f'Cierre: {cierre_at}')
        lines.append('')
        lines.append(f'Inicial: {inicial:0.2f}')
        lines.append('-' * 80)
        lines.append(f'{"Pedido":<6}{"Numero":<22}{"Total":>12}  Items')
        lines.append('-' * 80)
        for d in detalles:
            lines.append(f'{d[0]:<6}{d[1]:<22}{d[2]:>12.2f}  {d[3]}')
        lines.append('-' * 80)
        lines.append(f'TOTALES: {sum_total:0.2f}')
        report_text = '\n'.join(lines)
        # show report in products_frame (replace content temporarily)
        self.show_report(report_text)
        # attempt to print by saving to temp file and using os.startfile on Windows
        try:
            fd, path = tempfile.mkstemp(prefix='cierre_caja_', suffix='.txt')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(report_text)
            if os.name == 'nt':
                try:
                    os.startfile(path, 'print')
                except Exception:
                    logging.exception('Error sending to printer')
        except Exception:
            logging.exception('Error creando archivo de reporte')
        # clear session id
        self.session_id = None

    def show_report(self, text):
        # clear products_frame and show report with back button
        for w in self.products_frame.winfo_children():
            w.destroy()
        frm = tk.Frame(self.products_frame, bg='white')
        frm.pack(fill='both', expand=True)
        t = tk.Text(frm)
        t.insert('1.0', text)
        t.pack(fill='both', expand=True)
        tk.Button(frm, text='Volver', command=self.render_products, bg=ACCENT, fg='white').pack(pady=6)


class KDSFrame(tk.Frame):
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        # accept optional user kwarg to avoid passing unknown options to tk.Frame
        user = kwargs.pop('user', None)
        super().__init__(parent, bg='#071026', *args, **kwargs)
        self.db = db
        self.user = user
        tk.Label(self, text='KDS - Cocina', bg='#071026', fg='white', font=(None, 16, 'bold')).pack(anchor='w', padx=12, pady=8)
        kds_img = load_image(os.path.join('Imagenes', 'cocina.jpeg'), size=(40,40)) or load_image(os.path.join('Imagenes', 'cocina.png'), size=(40,40))
        if kds_img:
            tk.Label(self, image=kds_img, bg='#071026').pack(anchor='w', padx=12)
            self._kds_img = kds_img
        self.listbox = tk.Listbox(self, height=20, width=60)
        self.listbox.pack(padx=12, pady=8)
        btns = tk.Frame(self, bg='#071026')
        btns.pack()
        tk.Button(btns, text='Refrescar', command=self.refresh, bg='#60a5fa').pack(side='left', padx=6)
        tk.Button(btns, text='Marcar listo', command=self.mark_ready, bg='#34d399').pack(side='left', padx=6)
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, 'end')
        rows = self.db.fetch_all("SELECT id, numero, items, estado FROM pedidos WHERE estado!='listo' ORDER BY id DESC LIMIT 50")
        for r in rows:
            short = (r[2][:80] + '...') if r[2] and len(r[2]) > 80 else (r[2] or '')
            self.listbox.insert('end', f"#{r[0]} - {short} ({r[3]})")

    def mark_ready(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        text = self.listbox.get(sel[0])
        pid = int(text.split()[0].lstrip('#'))
        self.db.execute('UPDATE pedidos SET estado=? WHERE id=?', ('listo', pid))
        self.refresh()


class AdminFrame(tk.Frame):
    def __init__(self, parent, db: DatabaseManager, *args, **kwargs):
        super().__init__(parent, bg='#0b1220', *args, **kwargs)
        self.db = db
        # Top navigation (simple) + Back button
        top = tk.Frame(self, bg='#0b1220')
        top.pack(fill='x', padx=12, pady=8)

        # optional icon
        img = load_image(os.path.join('Imagenes', 'admin.jpeg'), size=(48,48)) or load_image(os.path.join('Imagenes', 'admin.png'), size=(48,48))
        if img:
            tk.Label(top, image=img, bg='#0b1220').pack(side='left', padx=6)
            # keep reference
            self._admin_img = img

        tk.Label(top, text='Admin - Panel', bg='#0b1220', fg=FG, font=(None, 16, 'bold')).pack(side='left', padx=6)
        tk.Button(top, text='Regresar', command=lambda: self.master.select(0), bg=ACCENT, fg='white').pack(side='right')

        nav = tk.Frame(self, bg='#0b1220')
        nav.pack(fill='x', padx=12)
        tk.Button(nav, text='Inventario', command=lambda: self.show_section('inventory'), bg=PANEL, fg=FG).pack(side='left', padx=6, pady=6)
        tk.Button(nav, text='Usuarios', command=lambda: self.show_section('users'), bg=PANEL, fg=FG).pack(side='left', padx=6, pady=6)
        tk.Button(nav, text='Dashboard', command=lambda: self.show_section('dashboard'), bg=PANEL, fg=FG).pack(side='left', padx=6, pady=6)

        # content area
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill='both', expand=True, padx=12, pady=12)

        self.frames = {}
        for key in ('dashboard', 'inventory', 'users'):
            f = tk.Frame(self.content, bg=BG)
            f.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.frames[key] = f

        # populate users frame
        uf = self.frames['users']
        tk.Label(uf, text='Usuarios', bg=BG, fg=FG, font=(None, 14, 'bold')).pack(anchor='w', padx=12, pady=6)
        self.user_tree = ttk.Treeview(uf, columns=('id', 'username', 'rol', 'nombre'), show='headings')
        for c, h in [('id','ID'),('username','Usuario'),('rol','Rol'),('nombre','Nombre')]:
            self.user_tree.heading(c, text=h)
        self.user_tree.pack(fill='both', expand=True, padx=12, pady=6)
        form = tk.Frame(uf, bg=BG)
        form.pack(padx=12, pady=6)
        tk.Label(form, text='Usuario', bg=BG, fg=FG).grid(row=0, column=0, sticky='w')
        self.e_user = tk.Entry(form)
        self.e_user.grid(row=0, column=1)
        tk.Label(form, text='Password', bg=BG, fg=FG).grid(row=1, column=0, sticky='w')
        self.e_pass = tk.Entry(form, show='*')
        self.e_pass.grid(row=1, column=1)
        tk.Label(form, text='Rol', bg=BG, fg=FG).grid(row=2, column=0, sticky='w')
        self.e_rol = tk.Entry(form)
        self.e_rol.grid(row=2, column=1)
        tk.Label(form, text='Nombre', bg=BG, fg=FG).grid(row=3, column=0, sticky='w')
        self.e_nombre = tk.Entry(form)
        self.e_nombre.grid(row=3, column=1)
        tk.Button(form, text='Crear', command=self.create_user, bg='#60a5fa').grid(row=4, column=0, columnspan=2, pady=8)

        # inventory frame
        invf = self.frames['inventory']
        tk.Label(invf, text='Inventario', bg=BG, fg=FG, font=(None, 14, 'bold')).pack(anchor='w', padx=12, pady=6)
        self.inv_list = tk.Frame(invf, bg=BG)
        self.inv_list.pack(fill='both', expand=True, padx=12, pady=6)

        # dashboard simple
        df = self.frames['dashboard']
        tk.Label(df, text='Dashboard', bg=BG, fg=FG, font=(None, 14, 'bold')).pack(anchor='w', padx=12, pady=6)

        # default
        self.show_section('inventory')
        self.refresh()

    def show_section(self, key):
        for k,f in self.frames.items():
            if k == key:
                f.lift()
        # refresh when showing
        self.refresh()

    def refresh(self):
        # refresh users list
        try:
            if hasattr(self, 'user_tree'):
                for r in self.user_tree.get_children():
                    self.user_tree.delete(r)
                rows = self.db.fetch_all('SELECT id, username, rol, nombre_completo FROM usuarios')
                for row in rows:
                    self.user_tree.insert('', 'end', values=row)
        except Exception:
            logging.exception('Error refreshing users in AdminFrame')

        # refresh inventory list
        try:
            for w in self.inv_list.winfo_children():
                w.destroy()
            rows = self.db.fetch_all('SELECT id, ingrediente, cantidad, unidad, stock_minimo FROM inventario')
            if not rows:
                tk.Label(self.inv_list, text='Inventario vacío', bg=BG, fg=FG).pack()
                return
            for r in rows:
                card = tk.Frame(self.inv_list, bg='white', bd=1, relief='solid', padx=8, pady=8)
                card.pack(fill='x', pady=6)
                left = tk.Frame(card, bg='white')
                left.pack(side='left')
                tk.Label(left, text=r[1], font=(None, 12, 'bold'), bg='white').pack()
                right = tk.Frame(card, bg='white')
                right.pack(side='right')
                tk.Label(right, text=f"{r[2]} {r[3]}", bg='white').pack()
                tk.Button(right, text='+1', command=lambda id=r[0]: self.add_stock(id, 1), bg=OK).pack()
        except Exception:
            logging.exception('Error refreshing inventory in AdminFrame')

    def create_user(self):
        username = self.e_user.get().strip()
        password = self.e_pass.get().strip()
        rol = self.e_rol.get().strip() or 'Cajera'
        nombre = self.e_nombre.get().strip() or username
        if not username or not password:
            messagebox.showwarning('Falta', 'Usuario y password son obligatorios')
            return
        try:
            self.db.execute('INSERT INTO usuarios (username, password, rol, nombre_completo) VALUES (?, ?, ?, ?)', (username, password, rol, nombre))
            messagebox.showinfo('OK', 'Usuario creado')
            self.e_user.delete(0, 'end')
            self.e_pass.delete(0, 'end')
            self.e_rol.delete(0, 'end')
            self.e_nombre.delete(0, 'end')
            self.refresh()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def add_stock(self, id, amount):
        try:
            self.db.execute('UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?', (amount, id))
            self.refresh()
        except Exception as e:
            logging.exception(f'Error updating stock from AdminFrame: {e}')
            messagebox.showerror('Error', 'No se pudo actualizar el inventario')

    def show_access_logs(self):
        rows = self.db.fetch_all('SELECT id, user_id, username, action, details, created_at FROM access_logs ORDER BY id DESC LIMIT 500')
        win = tk.Toplevel(self)
        win.title('Registros de acceso')
        cols = ('id', 'user_id', 'username', 'action', 'details', 'created_at')
        tree = ttk.Treeview(win, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c.upper())
        tree.pack(fill='both', expand=True)
        for r in rows:
            tree.insert('', 'end', values=r)


class LoginWindow(tk.Toplevel):
    """Diálogo modal de login que valida contra la tabla `usuarios`."""

    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.user = None
        self.title('Login')
        # ventana de login más grande y centrada
        self.resizable(False, False)
        self.configure(bg=BG)
        center_window(self, 520, 320)
        self.grab_set()

        # logo (pikata)
        logo_path = os.path.join('Imagenes', 'pikata.png')
        self.logo_img = load_image(logo_path, size=(96, 96))
        if self.logo_img:
            tk.Label(self, image=self.logo_img, bg=BG).pack(pady=6)
        tk.Label(self, text='Iniciar sesión', font=(None, 14, 'bold'), bg=BG, fg=FG).pack(pady=2)

        frm = tk.Frame(self, bg=BG)
        frm.pack(padx=12, pady=6, fill='x')
        tk.Label(frm, text='Usuario', bg=BG, fg=FG).grid(row=0, column=0, sticky='w')
        self.username = tk.Entry(frm, width=28)
        self.username.grid(row=0, column=1, sticky='ew')
        tk.Label(frm, text='Contraseña', bg=BG, fg=FG).grid(row=1, column=0, sticky='w')
        self.password = tk.Entry(frm, show='*', width=28)
        self.password.grid(row=1, column=1, sticky='ew')
        frm.columnconfigure(1, weight=1)

        btnf = tk.Frame(self, bg=BG)
        btnf.pack(pady=10)
        tk.Button(btnf, text='Entrar', bg=ACCENT, fg='white', command=self.try_login).pack(side='left', padx=6)
        tk.Button(btnf, text='Cancelar', command=self.cancel).pack(side='left', padx=6)

        # accesibilidad teclado: Enter = login, Escape = cancelar, Tab navegación natural
        self.username.focus_set()
        self.bind('<Return>', lambda e: self.try_login())
        self.bind('<Escape>', lambda e: self.cancel())

    def try_login(self):
        u = self.username.get().strip()
        p = self.password.get().strip()
        if not u or not p:
            messagebox.showwarning('Aviso', 'Ingrese usuario y contraseña')
            return
        row = self.db.fetch_one('SELECT id, username, rol, nombre_completo FROM usuarios WHERE username = ? AND password = ?', (u, p))
        if not row:
            messagebox.showerror('Error', 'Usuario o contraseña incorrectos')
            return
        self.user = {'id': row[0], 'username': row[1], 'rol': row[2], 'nombre_completo': row[3]}
        try:
            # Registrar acceso
            self.db.log_access(self.user['id'], self.user['username'], 'login')
        except Exception:
            logging.exception('Error registrando login')
        self.destroy()

    def cancel(self):
        self.user = None
        self.destroy()


class App(tk.Tk):
    """Ventana principal (launcher) que muestra botones según rol."""

    def __init__(self):
        super().__init__()
        self.title('Restaurante - Panel')
        self.configure(bg=BG)
        self.db = DatabaseManager()
        self.user = None

        # Forzar login antes de construir el launcher
        self.withdraw()
        login = LoginWindow(self, self.db)
        self.wait_window(login)
        if not getattr(login, 'user', None):
            self.destroy()
            return
        self.user = login.user
        self.deiconify()
        self.build()

    def build(self):
        # Cabecera con estilo y título grande (similar a la versión web)
        header = tk.Frame(self, bg=BG)
        header.pack(pady=8)
        tk.Label(header, text=f"Bienvenido {self.user.get('nombre_completo')}", bg=BG, fg=FG, font=(None, 12)).pack()
        tk.Label(header, text='Sistema Restaurante', bg=BG, fg=FG, font=(None, 22, 'bold')).pack()

        # En lugar de abrir nuevas ventanas, creamos un Notebook (usado internamente) y ocultamos pestañas.
        style = ttk.Style()
        try:
            style.layout('TNotebook.Tab', [])
        except Exception:
            pass
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=12, pady=12)

        # Navigation buttons (replace visible tab bar)
        nav = tk.Frame(self, bg=BG)
        nav.pack(fill='x')
        tk.Button(nav, text='Home', command=lambda: self.notebook.select(0), bg=PANEL, fg=FG).pack(side='left', padx=6, pady=6)
        tk.Button(nav, text='Caja / POS', command=self.open_pos, bg=PANEL, fg=FG).pack(side='left', padx=6, pady=6)
        tk.Button(nav, text='Cocina (KDS)', command=self.open_kds, bg=PANEL, fg=FG).pack(side='left', padx=6, pady=6)
        tk.Button(nav, text='Admin', command=self.open_admin, bg=PANEL, fg=FG).pack(side='left', padx=6, pady=6)

        role = self.user.get('rol', '').lower()

        # Home tab: 4 cards (simula web/index.html)
        home = tk.Frame(self.notebook, bg=BG)
        # Use the main header (above notebook) so avoid duplicating title here
        cards_wrap = tk.Frame(home, bg=BG)
        cards_wrap.pack(padx=24, pady=18, fill='both', expand=True)

        def make_card(parent, img_name, title, desc, cmd=None):
            card = tk.Frame(parent, bg=PANEL, bd=1, relief='flat', padx=24, pady=20)
            # load image if available
            img = None
            if img_name:
                path = os.path.join('Imagenes', img_name)
                img = load_image(path, size=(96,96))
            if img:
                lbl = tk.Label(card, image=img, bg=PANEL)
                lbl.image = img
                lbl.pack(pady=6)
            else:
                tk.Label(card, text='🔸', font=(None, 36), bg=PANEL).pack(pady=6)
            tk.Label(card, text=title, bg=PANEL, fg=FG, font=(None, 14, 'bold')).pack(pady=6)
            tk.Label(card, text=desc, bg=PANEL, fg='#9CA3AF', wraplength=260, justify='center').pack(pady=6)
            if cmd:
                btn = tk.Button(card, text='Abrir', command=cmd, bg=ACCENT, fg='white')
                btn.pack(pady=8)
            return card

        # Grid de 4 tarjetas
        cards = []
        cards.append(make_card(cards_wrap, 'avion.jpeg', 'Simulador', 'Control total de todos los flujos en una sola vista.', cmd=lambda: self.notebook.select(0)))
        cards.append(make_card(cards_wrap, 'pos.png', 'Caja / POS', 'Punto de venta para registro de pedidos presenciales.', cmd=self.open_pos))
        cards.append(make_card(cards_wrap, 'cocina.jpeg', 'Cocina (KDS)', 'Pantalla interactiva para preparación de pedidos.', cmd=self.open_kds))
        cards.append(make_card(cards_wrap, 'admin.jpeg', 'Admin', 'Métricas, ventas e inventario en tiempo real.', cmd=self.open_admin))

        # arrange cards in a 4-column grid
        for i, c in enumerate(cards):
            c.grid(row=0, column=i, padx=12, pady=12, sticky='nsew')
            cards_wrap.columnconfigure(i, weight=1)

        self.notebook.add(home, text='Home')

        # POS tab
        if role in ('administrador', 'admin') or role in ('mesero', 'cajera', 'supervisor'):
            pos_tab = POSFrame(self.notebook, self.db, user=self.user)
            self.notebook.add(pos_tab, text='Caja / POS')

        # KDS tab
        if role in ('administrador', 'admin') or role in ('cocina',):
            kds_tab = KDSFrame(self.notebook, self.db, user=self.user)
            self.notebook.add(kds_tab, text='Cocina (KDS)')

        # Admin tab
        if role in ('administrador', 'admin', 'supervisor'):
            admin_tab = AdminFrame(self.notebook, self.db)
            self.notebook.add(admin_tab, text='Admin')

        # Logout abajo
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill='x')
        tk.Button(btn_frame, text='Logout', width=12, command=self.logout, bg=ERR, fg='white').pack(pady=6)

        # Global keyboard shortcuts (accesibilidad): Ctrl+P POS, Ctrl+K KDS, Ctrl+A Admin, Ctrl+L Logs
        self.bind_all('<Control-p>', lambda e: self.open_pos() if role in ('administrador','admin','mesero','cajera','supervisor') else None)
        self.bind_all('<Control-k>', lambda e: self.open_kds() if role in ('administrador','admin','cocina') else None)
        self.bind_all('<Control-a>', lambda e: self.open_admin() if role in ('administrador','admin','supervisor') else None)

    def open_pos(self):
        # Selecciona la pestaña POS si existe
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Caja / POS':
                self.notebook.select(i)
                return

    def open_kds(self):
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Cocina (KDS)':
                self.notebook.select(i)
                return

    def open_admin(self):
        for i in range(self.notebook.index('end')):
            if self.notebook.tab(i, 'text') == 'Admin':
                self.notebook.select(i)
                return

    def logout(self):
        try:
            if getattr(self, 'user', None):
                self.db.log_access(self.user.get('id'), self.user.get('username'), 'logout')
        except Exception:
            logging.exception('Error registrando logout')
        self.destroy()


class POSWindow(tk.Toplevel):
    """Ventana POS: lista de productos por categoría y carrito lateral."""

    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.title('POS - Caja')
        self.geometry('1000x600')
        self.configure(bg=BG)
        self.cart = {}

        left = tk.Frame(self, bg=BG)
        left.pack(side='left', fill='both', expand=True)
        right = tk.Frame(self, bg=PANEL, width=320)
        right.pack(side='right', fill='y')

        # categorías
        cats = self.db.fetch_all('SELECT DISTINCT categoria FROM productos_menu WHERE categoria IS NOT NULL')
        self.categories = [c[0] for c in cats if c[0]] if cats else ['Combos', 'Extras', 'Bebidas']
        cat_frame = tk.Frame(left, bg=BG)
        cat_frame.pack(fill='x', padx=12, pady=8)
        self.selected_category = tk.StringVar(value=self.categories[0])
        for c in self.categories:
            b = tk.Button(cat_frame, text=c, command=lambda cc=c: self.select_category(cc), bg=PANEL, fg=FG)
            b.pack(side='left', padx=6)

        self.products_frame = tk.Frame(left, bg=BG)
        self.products_frame.pack(fill='both', expand=True, padx=12, pady=12)
        self.render_products()

        # sidebar carrito
        tk.Label(right, text='Orden Actual', bg=PANEL, fg=FG, font=(None, 14, 'bold')).pack(pady=10)
        self.cart_box = tk.Listbox(right)
        self.cart_box.pack(fill='both', expand=True, padx=8, pady=6)
        tk.Button(right, text='Quitar seleccionado', command=self.remove_selected, bg=ERR, fg='white').pack(fill='x', padx=8, pady=4)
        tk.Button(right, text='Confirmar y Enviar', bg=ACCENT, fg='white', command=self.process_order).pack(fill='x', padx=8, pady=8)

        # Key bindings for POS: Enter to confirm order, Delete to remove selected, Up/Down to move selection
        self.bind_all('<Return>', lambda e: self.process_order() if self.focus_get() and (self.focus_get() in (self.cart_box,)) else None)
        self.cart_box.bind('<Delete>', lambda e: self.remove_selected())
        self.cart_box.bind('<Return>', lambda e: None)

    def select_category(self, cat):
        self.selected_category.set(cat)
        self.render_products()

    def render_products(self):
        for w in self.products_frame.winfo_children():
            w.destroy()
        products = self.db.fetch_all('SELECT id, nombre, precio, categoria, emoji FROM productos_menu WHERE categoria = ? OR ? = ""', (self.selected_category.get(), self.selected_category.get()))
        if not products:
            products = [(1, 'Combo Clásico', 5.5, 'Combos', '🍔'), (4, 'Papas fritas', 1.5, 'Extras', '🍟')]
        for p in products:
            f = tk.Frame(self.products_frame, bd=0, relief='flat', padx=8, pady=8, bg='white')
            f.pack(side='left', padx=8, pady=8)
            tk.Label(f, text=p[4] or '🍽', font=(None, 24)).pack()
            tk.Label(f, text=p[1], font=(None, 10, 'bold')).pack()
            tk.Label(f, text=f"${p[2]:.2f}", fg=ACCENT, font=(None, 10, 'bold')).pack()
            tk.Button(f, text='Agregar', command=lambda pid=p: self.add_product(pid), bg=OK, fg='white').pack(pady=6)

    def add_product(self, p):
        pid, name, price = p[0], p[1], p[2]
        if pid in self.cart:
            self.cart[pid]['qty'] += 1
        else:
            self.cart[pid] = {'id': pid, 'name': name, 'price': price, 'qty': 1}
        self.refresh_cart()

    def refresh_cart(self):
        self.cart_box.delete(0, 'end')
        for item in self.cart.values():
            self.cart_box.insert('end', f"{item['name']} x{item['qty']}  - ${item['price']*item['qty']:.2f}")

    def remove_selected(self):
        sel = self.cart_box.curselection()
        if not sel:
            return
        idx = sel[0]
        key = list(self.cart.keys())[idx]
        del self.cart[key]
        self.refresh_cart()

    def process_order(self):
        if not self.cart:
            return messagebox.showwarning('Aviso', 'Carrito vacío')
        items = [{'id': v['id'], 'name': v['name'], 'qty': v['qty'], 'price': v['price']} for v in self.cart.values()]
        total = sum(v['price'] * v['qty'] for v in self.cart.values())
        numero = f"POS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            self.db.execute('INSERT INTO pedidos (numero, mesa, items, total, estado, canal, cliente_telefono, cliente_nombre) VALUES (?,?,?,?,?,?,?,?)',
                            (numero, 'Presencial', json.dumps(items), total, 'RECIBIDO', 'CAJA', '', 'Venta Mostrador'))
            messagebox.showinfo('OK', f'Pedido {numero} creado')
            self.cart = {}
            self.refresh_cart()
            self.destroy()
        except Exception as e:
            logging.error(f'Error creating order: {e}')
            messagebox.showerror('Error', 'No se pudo crear el pedido')


class KDSWindow(tk.Toplevel):
    """Pantalla de cocina (KDS) con polling sencillo para refrescar pedidos."""

    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.title('KDS - Cocina')
        self.geometry('1000x600')
        self.configure(bg=BG)
        cols = ('id', 'numero', 'mesa', 'items', 'estado')
        self.tree = ttk.Treeview(self, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c.upper())
        self.tree.pack(fill='both', expand=True)
        btns = tk.Frame(self, bg=BG)
        btns.pack(fill='x')
        tk.Button(btns, text='Avanzar a PREPARANDO', command=lambda: self.change_status('PREPARANDO'), bg=WARN).pack(side='left', padx=6)
        tk.Button(btns, text='Marcar COMPLETADO', command=lambda: self.change_status('COMPLETADO'), bg=OK).pack(side='left', padx=6)
        self.poll()

        # KDS keyboard shortcuts: 'p' = PREPARANDO, 'c' = COMPLETADO, F5 refresh
        self.bind('<p>', lambda e: self.change_status('PREPARANDO'))
        self.bind('<c>', lambda e: self.change_status('COMPLETADO'))
        self.bind('<F5>', lambda e: self.refresh())

    def poll(self):
        self.refresh()
        self.after(3000, self.poll)

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = self.db.fetch_all("SELECT id, numero, mesa, items, estado FROM pedidos ORDER BY id DESC LIMIT 50")
        for r in rows:
            items_text = (r[3][:80] + '...') if r[3] and len(r[3]) > 80 else (r[3] or '')
            self.tree.insert('', 'end', iid=r[0], values=(r[0], r[1], r[2], items_text, r[4]))

    def change_status(self, new_status):
        sel = self.tree.selection()
        if not sel:
            return
        oid = int(sel[0])
        self.db.execute('UPDATE pedidos SET estado = ? WHERE id = ?', (new_status, oid))
        self.refresh()


class AdminWindow(tk.Toplevel):
    """Panel administrativo: visor de logs e inventario minimal."""

    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.title('Admin')
        self.geometry('1000x600')
        self.configure(bg=BG)

        left = tk.Frame(self, bg=PANEL)
        left.pack(side='left', fill='y')
        right = tk.Frame(self, bg=BG)
        right.pack(side='right', fill='both', expand=True)

        tk.Button(left, text='Ver logs', command=self.view_logs, bg='#6366f1', fg='white').pack(fill='x', pady=6, padx=6)
        tk.Button(left, text='Refrescar inventario', command=self.load_inventory, bg=ACCENT, fg='white').pack(fill='x', pady=6, padx=6)

        self.inv_frame = tk.Frame(right, bg=BG)
        self.inv_frame.pack(fill='both', expand=True, padx=12, pady=12)
        self.load_inventory()

        # Admin keyboard: 'l' = logs, 'r' = refresh inventory
        self.bind('<l>', lambda e: self.view_logs())
        self.bind('<r>', lambda e: self.load_inventory())

    def view_logs(self):
        win = tk.Toplevel(self)
        t = tk.Text(win)
        t.pack(fill='both', expand=True)
        if os.path.exists('error_log.txt'):
            with open('error_log.txt', 'r', encoding='utf-8') as f:
                t.insert('1.0', f.read())
        else:
            t.insert('1.0', 'No logs')

    def load_inventory(self):
        for w in self.inv_frame.winfo_children():
            w.destroy()
        rows = self.db.fetch_all('SELECT id, ingrediente, cantidad, unidad, stock_minimo FROM inventario')
        if not rows:
            tk.Label(self.inv_frame, text='Inventario vacío', bg=BG, fg=FG).pack()
            return
        for r in rows:
            f = tk.Frame(self.inv_frame, bd=1, relief='solid', padx=8, pady=8)
            f.pack(fill='x', pady=4)
            tk.Label(f, text=r[1], font=(None, 12, 'bold')).pack(side='left')
            tk.Label(f, text=f"{r[2]} {r[3]}").pack(side='right')
            b = tk.Button(f, text='+1', command=lambda id=r[0]: self.add_stock(id, 1), bg=OK, fg='white')
            b.pack(side='right', padx=6)

    def add_stock(self, id, amount):
        try:
            self.db.execute('UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?', (amount, id))
            self.load_inventory()
        except Exception as e:
            logging.error(f'Error updating stock: {e}')
            messagebox.showerror('Error', 'No se pudo actualizar el inventario')


if __name__ == '__main__':
    app = App()
    app.mainloop()
