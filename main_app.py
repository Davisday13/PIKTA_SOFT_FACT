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

DB_NAME = 'PIKTA_SOFT.db'
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
            cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS productos_menu (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY, numero TEXT, mesa TEXT, items TEXT, total REAL, estado TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY, nombre TEXT, cantidad REAL)''')
            cur.execute('INSERT OR IGNORE INTO usuarios (id, username, password) VALUES (1, "admin", "1234")')
            conn.commit()

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
        self.title('POS')
        self.geometry('700x400')
        self.products = tk.Listbox(self)
        self.products.pack(side='left', fill='both', expand=True)
        for p in self.db.fetch_all('SELECT id, nombre, precio FROM productos_menu'):
            self.products.insert('end', f"{p[0]} - {p[1]} (${p[2]})")
        frame = tk.Frame(self)
        frame.pack(side='right', fill='y')
        tk.Button(frame, text='Agregar', command=self.add).pack(fill='x')
        tk.Button(frame, text='Enviar', command=self.send).pack(fill='x')
        self.cart = []

    def add(self):
        sel = self.products.curselection()
        if not sel: return
        self.cart.append(self.products.get(sel[0]))
        messagebox.showinfo('Carrito', f'Items: {len(self.cart)}')

    def send(self):
        if not self.cart:
            return messagebox.showwarning('Aviso','Carrito vacío')
        self.db.execute('INSERT INTO pedidos (numero, mesa, items, total, estado) VALUES (?,?,?,?,?)', (f'POS-{datetime.now().strftime("%H%M%S")}', 'Presencial', json.dumps(self.cart), 0.0, 'PENDIENTE'))
        messagebox.showinfo('OK','Orden enviada')
        self.destroy()


class KDSWindow(tk.Toplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.title('KDS')
        self.geometry('700x400')
        cols = ('num','mesa','items','estado')
        self.tree = ttk.Treeview(self, columns=cols, show='headings')
        for c in cols: self.tree.heading(c, text=c.upper())
        self.tree.pack(fill='both', expand=True)
        tk.Button(self, text='Refresh', command=self.refresh).pack()
        tk.Button(self, text='Avanzar', command=self.advance).pack()
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in self.db.fetch_all("SELECT id, numero, mesa, items, estado FROM pedidos ORDER BY id DESC"):
            self.tree.insert('', 'end', iid=r[0], values=(r[1], r[2], r[3][:50], r[4]))

    def advance(self):
        sel = self.tree.selection()
        if not sel: return
        oid = int(sel[0])
        self.db.execute('UPDATE pedidos SET estado = ? WHERE id = ?', ('EN_PREPARACION', oid))
        self.refresh()


class AdminWindow(tk.Toplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.title('Admin')
        self.geometry('700x400')
        tk.Button(self, text='Ver logs', command=self.view_logs).pack()

    def view_logs(self):
        win = tk.Toplevel(self)
        t = tk.Text(win)
        t.pack(fill='both', expand=True)
        if os.path.exists('error_log.txt'):
            with open('error_log.txt', 'r', encoding='utf-8') as f:
                t.insert('1.0', f.read())
        else:
            t.insert('1.0', 'No logs')


if __name__ == '__main__':
    app = App()
    app.mainloop()
