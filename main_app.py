"""
main_app.py - Minimal Tkinter GUI (clean replacement)
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import json
import os
from datetime import datetime
import logging

logging.basicConfig(filename='error_log.txt', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = "PIK'TADB.db"
BG = '#0F172A'
PANEL = '#1E293B'
FG = '#FFFFFF'


class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        with self.get_connection() as conn:
            cur = conn.cursor()
            # core tables (idempotent)
            cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, rol TEXT, nombre_completo TEXT
            )''')

            cur.execute('''CREATE TABLE IF NOT EXISTS productos_menu (
                id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, categoria TEXT, emoji TEXT
            )''')

            cur.execute('''CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY, numero TEXT, mesa TEXT, items TEXT, total REAL, estado TEXT, canal TEXT, cliente TEXT, telefono TEXT, usuario_id INTEGER, sesion_id INTEGER
            )''')

            cur.execute('''CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY, nombre TEXT, cantidad REAL, unidad TEXT, stock_minimo REAL
            )''')

            # ensure columns exist (safe migration)
            self._ensure_column('productos_menu', 'categoria', 'TEXT')
            self._ensure_column('productos_menu', 'emoji', 'TEXT')
            self._ensure_column('pedidos', 'canal', 'TEXT')
            self._ensure_column('pedidos', 'cliente', 'TEXT')
            self._ensure_column('pedidos', 'telefono', 'TEXT')
            self._ensure_column('pedidos', 'usuario_id', 'INTEGER')
            self._ensure_column('pedidos', 'sesion_id', 'INTEGER')

            # seed default users safely
            cur.execute('INSERT OR IGNORE INTO usuarios (username, password, rol, nombre_completo) VALUES (?,?,?,?)', ("Davis", "1234", "Administrador", "Davis Admin"))
            cur.execute('INSERT OR IGNORE INTO usuarios (username, password, rol, nombre_completo) VALUES (?,?,?,?)', ("Rommel", "1234", "Supervisor", "Rommel Supervisor"))
            cur.execute('INSERT OR IGNORE INTO usuarios (username, password, rol, nombre_completo) VALUES (?,?,?,?)', ("Estefani", "1234", "Cajera", "Estefani Cajera"))
            cur.execute('INSERT OR IGNORE INTO usuarios (username, password, rol, nombre_completo) VALUES (?,?,?,?)', ("cocina", "1234", "Cocina", "Personal de Cocina"))
            cur.execute('INSERT OR IGNORE INTO usuarios (username, password, rol, nombre_completo) VALUES (?,?,?,?)', ("mesero", "1234", "Mesero", "Personal de Mesas"))

            conn.commit()

    def _ensure_column(self, table, column, col_type):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            if column not in cols:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                except Exception as e:
                    logging.error(f"Error adding column {column} to {table}: {e}")

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
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            return cur


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Restaurante - Panel')
        self.configure(bg=BG)
        self.db = DatabaseManager()
        self.build()

    def build(self):
        tk.Label(self, text='Sistema Restaurante', bg=BG, fg=FG, font=(None, 18, 'bold')).pack(pady=10)
        tk.Button(self, text='Caja / POS', command=self.open_pos).pack(fill='x', padx=40, pady=5)
        tk.Button(self, text='Cocina (KDS)', command=self.open_kds).pack(fill='x', padx=40, pady=5)
        tk.Button(self, text='Admin', command=self.open_admin).pack(fill='x', padx=40, pady=5)

    def open_pos(self):
        POSWindow(self, self.db)

    def open_kds(self):
        KDSWindow(self, self.db)

    def open_admin(self):
        AdminWindow(self, self.db)


class POSWindow(tk.Toplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.title('POS - Caja')
        self.geometry('1000x600')
        self.configure(bg=BG)
        self.cart = {}  # product_id -> {id,name,price,qty}

        left = tk.Frame(self, bg=BG)
        left.pack(side='left', fill='both', expand=True)
        right = tk.Frame(self, bg=PANEL, width=320)
        right.pack(side='right', fill='y')

        # categories
        self.categories = [r[0] for r in self.db.fetch_all('SELECT DISTINCT categoria FROM productos_menu WHERE categoria IS NOT NULL')]
        if not self.categories:
            self.categories = ['Combos','Extras','Bebidas']
        cat_frame = tk.Frame(left, bg=BG)
        cat_frame.pack(fill='x', padx=12, pady=8)
        self.selected_category = tk.StringVar(value=self.categories[0])
        for c in self.categories:
            b = tk.Button(cat_frame, text=c, command=lambda cc=c: self.select_category(cc))
            b.pack(side='left', padx=6)

        self.products_frame = tk.Frame(left, bg=BG)
        self.products_frame.pack(fill='both', expand=True, padx=12, pady=12)
        self.render_products()

        # cart sidebar
        tk.Label(right, text='Orden Actual', bg=PANEL, fg=FG, font=(None,14,'bold')).pack(pady=10)
        self.cart_box = tk.Listbox(right)
        self.cart_box.pack(fill='both', expand=True, padx=8, pady=6)
        tk.Button(right, text='Quitar seleccionado', command=self.remove_selected).pack(fill='x', padx=8, pady=4)
        tk.Button(right, text='Confirmar y Enviar', bg='#0ea5e9', fg='white', command=self.process_order).pack(fill='x', padx=8, pady=8)

    def select_category(self, cat):
        self.selected_category.set(cat)
        self.render_products()

    def render_products(self):
        for w in self.products_frame.winfo_children():
            w.destroy()
        products = self.db.fetch_all('SELECT id, nombre, precio, categoria, emoji FROM productos_menu WHERE categoria = ? OR ? = ""', (self.selected_category.get(), self.selected_category.get()))
        if not products:
            # fallback sample
            products = [(1,'Combo Clásico',5.5,'Combos','🍔'),(4,'Papas fritas',1.5,'Extras','🍟')]
        rows = 0
        for p in products:
            f = tk.Frame(self.products_frame, bd=0, relief='flat', padx=8, pady=8, bg='white')
            f.pack(side='left', padx=8, pady=8)
            tk.Label(f, text=p[4] or '🍽', font=(None,24)).pack()
            tk.Label(f, text=p[1], font=(None,10,'bold')).pack()
            tk.Label(f, text=f"${p[2]:.2f}", fg='#0ea5e9', font=(None,10,'bold')).pack()
            tk.Button(f, text='Agregar', command=lambda pid=p: self.add_product(pid)).pack(pady=6)

    def add_product(self, p):
        pid, name, price = p[0], p[1], p[2]
        if pid in self.cart:
            self.cart[pid]['qty'] += 1
        else:
            self.cart[pid] = {'id': pid, 'name': name, 'price': price, 'qty': 1}
        self.refresh_cart()

    def refresh_cart(self):
        self.cart_box.delete(0,'end')
        for item in self.cart.values():
            self.cart_box.insert('end', f"{item['name']} x{item['qty']}  - ${item['price']*item['qty']:.2f}")

    def remove_selected(self):
        sel = self.cart_box.curselection()
        if not sel: return
        idx = sel[0]
        key = list(self.cart.keys())[idx]
        del self.cart[key]
        self.refresh_cart()

    def process_order(self):
        if not self.cart:
            return messagebox.showwarning('Aviso','Carrito vacío')
        items = [{'id':v['id'],'name':v['name'],'qty':v['qty'],'price':v['price']} for v in self.cart.values()]
        total = sum(v['price']*v['qty'] for v in self.cart.values())
        numero = f"POS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            cur = self.db.execute('INSERT INTO pedidos (numero, mesa, items, total, estado, canal, cliente) VALUES (?,?,?,?,?,?,?)', (numero, 'Presencial', json.dumps(items), total, 'RECIBIDO', 'CAJA', 'Venta Mostrador'))
            messagebox.showinfo('OK', f'Pedido {numero} creado')
            self.cart = {}
            self.refresh_cart()
            self.destroy()
        except Exception as e:
            logging.error(f'Error creating order: {e}')
            messagebox.showerror('Error','No se pudo crear el pedido')


class KDSWindow(tk.Toplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.title('KDS - Cocina')
        self.geometry('1000x600')
        cols = ('id','numero','mesa','items','estado')
        self.tree = ttk.Treeview(self, columns=cols, show='headings')
        for c in cols: self.tree.heading(c, text=c.upper())
        self.tree.pack(fill='both', expand=True)
        btns = tk.Frame(self)
        btns.pack(fill='x')
        tk.Button(btns, text='Avanzar a PREPARANDO', command=lambda: self.change_status('PREPARANDO')).pack(side='left', padx=6)
        tk.Button(btns, text='Marcar COMPLETADO', command=lambda: self.change_status('COMPLETADO')).pack(side='left', padx=6)
        self.poll()

    def poll(self):
        self.refresh()
        self.after(3000, self.poll)

    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        rows = self.db.fetch_all("SELECT id, numero, mesa, items, estado FROM pedidos WHERE estado IN ('RECIBIDO','PREPARANDO','EN_PREPARACION') ORDER BY id DESC")
        for r in rows:
            items_text = r[3][:80] if r[3] else ''
            self.tree.insert('', 'end', iid=r[0], values=(r[0], r[1], r[2], items_text, r[4]))

    def change_status(self, new_status):
        sel = self.tree.selection()
        if not sel: return
        oid = int(sel[0])
        self.db.execute('UPDATE pedidos SET estado = ? WHERE id = ?', (new_status, oid))
        self.refresh()


class AdminWindow(tk.Toplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.title('Admin')
        self.geometry('1000x600')
        left = tk.Frame(self)
        left.pack(side='left', fill='y')
        right = tk.Frame(self)
        right.pack(side='right', fill='both', expand=True)

        tk.Button(left, text='Ver logs', command=self.view_logs).pack(fill='x', pady=6, padx=6)
        tk.Button(left, text='Refrescar inventario', command=self.load_inventory).pack(fill='x', pady=6, padx=6)

        self.inv_frame = tk.Frame(right)
        self.inv_frame.pack(fill='both', expand=True, padx=12, pady=12)
        self.load_inventory()

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
        for w in self.inv_frame.winfo_children(): w.destroy()
        rows = self.db.fetch_all('SELECT id, nombre, cantidad, unidad, stock_minimo FROM inventario')
        if not rows:
            tk.Label(self.inv_frame, text='Inventario vacío').pack()
            return
        for r in rows:
            f = tk.Frame(self.inv_frame, bd=1, relief='solid', padx=8, pady=8)
            f.pack(fill='x', pady=4)
            tk.Label(f, text=r[1], font=(None,12,'bold')).pack(side='left')
            tk.Label(f, text=f"{r[2]} {r[3]}").pack(side='right')
            b = tk.Button(f, text='+1', command=lambda id=r[0]: self.add_stock(id,1))
            b.pack(side='right', padx=6)

    def add_stock(self, id, amount):
        try:
            self.db.execute('UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?', (amount, id))
            self.load_inventory()
        except Exception as e:
            logging.error(f'Error updating stock: {e}')
            messagebox.showerror('Error','No se pudo actualizar el inventario')


if __name__ == '__main__':
    app = App()
    app.mainloop()
