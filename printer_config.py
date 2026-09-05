"""
printer_config.py - Sistema de configuración de impresoras por tipo de documento.

Lee/escribe archivo printers.ini con formato:
  [Sistemas]
  Impfiscal=0
  Copias=1
  ImprimeCopia=0

  ; Formato legacy (prefijo por tipo)
  impfactura=EPSON LASER LP-1300
  impfacPuerto=LPT1:
  impfacCopia=1
  impfacPapel=15

  ; Formato moderno (sección por documento)
  [facturas15]
  PRN_Device=EPSON LASER LP-1300
  PRN_Port=LPT1:
  PRN_Copy=1
  PRN_PaperBin=15
"""

import os
import configparser
import logging
try:
    import win32print
    WIN32PRINT_AVAILABLE = True
except ImportError:
    WIN32PRINT_AVAILABLE = False
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# =============================================================================
# CONFIGURACIÓN POR DEFECTO
# =============================================================================

CONFIG_FILE = "printers.ini"

TIPOS_DOCUMENTO = [
    ("factura", "Factura / Ticket"),
    ("nefac", "NEFAC (Nota Fiscal Electrónica)"),
    ("compra", "Compra"),
    ("recibodecaja", "Recibo de Caja"),
    ("ComisSER", "Comisión Servicios"),
    ("presupuesto", "Presupuesto"),
    ("comanda", "Comanda (Cocina)"),
    ("cierre", "Cierre de Caja"),
]

CONFIG_DEFAULT = {
    "Sistemas": {
        "Impfiscal": "0",
        "Copias": "1",
        "ImprimeCopia": "0",
    },
}

for tipo, _ in TIPOS_DOCUMENTO:
    CONFIG_DEFAULT[tipo] = {
        "PRN_Device": "",
        "PRN_Port": "LPT1:",
        "PRN_Copy": "1",
        "PRN_PaperBin": "15",
    }

# Mapeo de nombres legacy a modernos
LEGACY_MAP = {
    "impfactura": ("factura", "PRN_Device"),
    "impfacPuerto": ("factura", "PRN_Port"),
    "impfacCopia": ("factura", "PRN_Copy"),
    "impfacPapel": ("factura", "PRN_PaperBin"),
    "impnefac": ("nefac", "PRN_Device"),
    "impnefacPuerto": ("nefac", "PRN_Port"),
    "impnefacCopia": ("nefac", "PRN_Copy"),
    "impnefacPapel": ("nefac", "PRN_PaperBin"),
    "impcompra": ("compra", "PRN_Device"),
    "impcompraPuerto": ("compra", "PRN_Port"),
    "impcompraCopia": ("compra", "PRN_Copy"),
    "impcompraPapel": ("compra", "PRN_PaperBin"),
    "imprecibodecaja": ("recibodecaja", "PRN_Device"),
    "imprecibodecajaPuerto": ("recibodecaja", "PRN_Port"),
    "imprecibodecajaCopia": ("recibodecaja", "PRN_Copy"),
    "imprecibodecajaPapel": ("recibodecaja", "PRN_PaperBin"),
    "impComisSER": ("ComisSER", "PRN_Device"),
    "impComisSERPuerto": ("ComisSER", "PRN_Port"),
    "impComisSERCopia": ("ComisSER", "PRN_Copy"),
    "impComisSERPapel": ("ComisSER", "PRN_PaperBin"),
    "imppresupuesto": ("presupuesto", "PRN_Device"),
    "imppresupuestoPuerto": ("presupuesto", "PRN_Port"),
    "imppresupuestoCopia": ("presupuesto", "PRN_Copy"),
    "imppresupuestoPapel": ("presupuesto", "PRN_PaperBin"),
}


class PrinterConfig:
    """Gestiona la configuración de impresoras por tipo de documento."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = None
            cls._instance._loaded = False
        return cls._instance

    def get_config_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)

    def load(self):
        self._config = configparser.ConfigParser()
        path = self.get_config_path()
        if os.path.exists(path):
            try:
                self._config.read(path, encoding="utf-8")
            except Exception as e:
                logging.error(f"Error leyendo {path}: {e}")
                self._config = configparser.ConfigParser()

        # Asegurar secciones por defecto
        self._ensure_defaults()

        # Migrar claves legacy si existen en [Sistemas]
        self._migrate_legacy()

        self._loaded = True
        return True

    def _ensure_defaults(self):
        for section, values in CONFIG_DEFAULT.items():
            if not self._config.has_section(section):
                self._config.add_section(section)
            for key, val in values.items():
                if not self._config.has_option(section, key):
                    self._config.set(section, key, val)

    def _migrate_legacy(self):
        if not self._config.has_section("Sistemas"):
            return
        changed = False
        for legacy_key, (section, modern_key) in LEGACY_MAP.items():
            if self._config.has_option("Sistemas", legacy_key):
                val = self._config.get("Sistemas", legacy_key)
                if val.strip():
                    if not self._config.has_option(section, modern_key):
                        self._config.set(section, modern_key, val)
                        changed = True
        if changed:
            self.save()

    def save(self):
        path = self.get_config_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                self._config.write(f)
            return True
        except Exception as e:
            logging.error(f"Error guardando {path}: {e}")
            return False

    def get_printer(self, tipo_doc):
        """Devuelve el nombre de la impresora para un tipo de documento."""
        if not self._loaded:
            self.load()
        if self._config.has_option(tipo_doc, "PRN_Device"):
            val = self._config.get(tipo_doc, "PRN_Device").strip()
            if val:
                return val
        return None

    def get_port(self, tipo_doc):
        if not self._loaded:
            self.load()
        if self._config.has_option(tipo_doc, "PRN_Port"):
            return self._config.get(tipo_doc, "PRN_Port").strip()
        return "LPT1:"

    def get_copies(self, tipo_doc):
        if not self._loaded:
            self.load()
        if self._config.has_option(tipo_doc, "PRN_Copy"):
            try:
                return int(self._config.get(tipo_doc, "PRN_Copy"))
            except:
                pass
        return 1

    def get_paper_bin(self, tipo_doc):
        if not self._loaded:
            self.load()
        if self._config.has_option(tipo_doc, "PRN_PaperBin"):
            try:
                return int(self._config.get(tipo_doc, "PRN_PaperBin"))
            except:
                pass
        return 15

    def get_sistema(self, key, default=""):
        if not self._loaded:
            self.load()
        return self._config.get("Sistemas", key, fallback=default)

    def set_printer(self, tipo_doc, device, port, copies, paper_bin):
        if not self._loaded:
            self.load()
        if not self._config.has_section(tipo_doc):
            self._config.add_section(tipo_doc)
        self._config.set(tipo_doc, "PRN_Device", device)
        self._config.set(tipo_doc, "PRN_Port", port)
        self._config.set(tipo_doc, "PRN_Copy", str(copies))
        self._config.set(tipo_doc, "PRN_PaperBin", str(paper_bin))
        return self.save()

    def get_all_printers(self):
        """Devuelve lista de impresoras Windows instaladas."""
        if not WIN32PRINT_AVAILABLE:
            return []
        try:
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            return sorted([p[2] for p in printers])
        except:
            return []

    def resolve_printer(self, tipo_doc):
        """Obtiene la impresora para un tipo, con fallback a default Windows."""
        printer = self.get_printer(tipo_doc)
        if printer:
            return printer
        if WIN32PRINT_AVAILABLE:
            try:
                return win32print.GetDefaultPrinter()
            except:
                return None
        return None


class PrinterConfigDialog:
    """Diálogo de configuración de impresoras por tipo de documento."""

    def __init__(self, parent):
        self.parent = parent
        self.cfg = PrinterConfig()
        self.result = None

    def show(self):
        win = tk.Toplevel(self.parent)
        win.title("Configuración de Impresoras")
        win.geometry("700x550")
        win.transient(self.parent)
        win.grab_set()

        # Frame principal con scroll
        canvas = tk.Canvas(win, borderwidth=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Título
        ttk.Label(
            scroll_frame,
            text="Configurar Impresora por Tipo de Documento",
            font=(None, 14, "bold")
        ).pack(pady=(15, 5))

        ttk.Label(
            scroll_frame,
            text="Seleccione la impresora, puerto, copias y bandeja para cada tipo de documento.",
            foreground="gray"
        ).pack(pady=(0, 15))

        # Configuración de sistema
        sys_frame = ttk.LabelFrame(scroll_frame, text="Configuración General", padding=10)
        sys_frame.pack(fill="x", padx=15, pady=5)

        sys_row = ttk.Frame(sys_frame)
        sys_row.pack(fill="x", pady=2)
        ttk.Label(sys_row, text="Impfiscal:").pack(side="left", padx=5)
        sys_impfiscal = tk.StringVar(value=self.cfg.get_sistema("Impfiscal", "0"))
        ttk.Checkbutton(sys_row, variable=sys_impfiscal, onvalue="1", offvalue="0").pack(side="left")

        sys_row2 = ttk.Frame(sys_frame)
        sys_row2.pack(fill="x", pady=2)
        ttk.Label(sys_row2, text="Copias por defecto:").pack(side="left", padx=5)
        sys_copias = tk.StringVar(value=self.cfg.get_sistema("Copias", "1"))
        ttk.Spinbox(sys_row2, from_=1, to=99, textvariable=sys_copias, width=5).pack(side="left")

        sys_row3 = ttk.Frame(sys_frame)
        sys_row3.pack(fill="x", pady=2)
        ttk.Label(sys_row3, text="Imprimir copia de respaldo:").pack(side="left", padx=5)
        sys_imprimecopia = tk.StringVar(value=self.cfg.get_sistema("ImprimeCopia", "0"))
        ttk.Checkbutton(sys_row3, variable=sys_imprimecopia, onvalue="1", offvalue="0").pack(side="left")

        # Variables de cada tipo de documento
        doc_vars = {}

        for tipo, etiqueta in TIPOS_DOCUMENTO:
            doc_frame = ttk.LabelFrame(scroll_frame, text=etiqueta, padding=10)
            doc_frame.pack(fill="x", padx=15, pady=5)

            vars_doc = {
                "device": tk.StringVar(value=self.cfg.get_printer(tipo) or ""),
                "port": tk.StringVar(value=self.cfg.get_port(tipo)),
                "copies": tk.StringVar(value=str(self.cfg.get_copies(tipo))),
                "paper_bin": tk.StringVar(value=str(self.cfg.get_paper_bin(tipo))),
            }
            doc_vars[tipo] = vars_doc

            # Impresora
            row1 = ttk.Frame(doc_frame)
            row1.pack(fill="x", pady=2)
            ttk.Label(row1, text="Impresora:", width=12).pack(side="left")
            printers_list = self.cfg.get_all_printers()
            device_cb = ttk.Combobox(
                row1, textvariable=vars_doc["device"],
                values=printers_list, width=45, state="normal"
            )
            device_cb.pack(side="left", padx=5, fill="x", expand=True)

            # Puerto
            row2 = ttk.Frame(doc_frame)
            row2.pack(fill="x", pady=2)
            ttk.Label(row2, text="Puerto:", width=12).pack(side="left")
            ports = ["LPT1:", "LPT2:", "COM1:", "COM2:", "COM3:", "USB001:", "USB002:", "nul:", "FILE:"]
            port_cb = ttk.Combobox(
                row2, textvariable=vars_doc["port"],
                values=ports, width=20, state="normal"
            )
            port_cb.pack(side="left", padx=5)

            # Copias
            ttk.Label(row2, text="Copias:").pack(side="left", padx=(15, 2))
            ttk.Spinbox(row2, from_=1, to=99, textvariable=vars_doc["copies"], width=5).pack(side="left")

            # Bandeja
            ttk.Label(row2, text="Bandeja:").pack(side="left", padx=(15, 2))
            bins = [
                ("15 (Automática)", "15"),
                ("1 (Bandeja Superior)", "1"),
                ("2 (Bandeja Inferior)", "2"),
                ("4 (Bandeja Manual)", "4"),
                ("7 (Bandeja 2)", "7"),
            ]
            bin_cb = ttk.Combobox(
                row2, textvariable=vars_doc["paper_bin"],
                values=[b[0] for b in bins], width=20, state="normal"
            )
            bin_cb.pack(side="left", padx=5)

        # Botones
        btn_frame = ttk.Frame(scroll_frame, padding=15)
        btn_frame.pack(fill="x")

        def on_save():
            # Guardar sistema
            self.cfg._config.set("Sistemas", "Impfiscal", sys_impfiscal.get())
            self.cfg._config.set("Sistemas", "Copias", sys_copias.get())
            self.cfg._config.set("Sistemas", "ImprimeCopia", sys_imprimecopia.get())

            for tipo, vars_doc in doc_vars.items():
                device = vars_doc["device"].get().strip()
                port = vars_doc["port"].get().strip()
                copies = vars_doc["copies"].get().strip()
                paper_bin = vars_doc["paper_bin"].get().strip()
                # Extraer solo el número de la bandeja si está en formato "N (Nombre)"
                if paper_bin and "(" in paper_bin:
                    paper_bin = paper_bin.split()[0]
                self.cfg.set_printer(tipo, device, port, copies, paper_bin)

            if self.cfg.save():
                messagebox.showinfo("Éxito", "Configuración de impresoras guardada correctamente.", parent=win)
                win.destroy()
            else:
                messagebox.showerror("Error", "No se pudo guardar la configuración.", parent=win)

        def on_cancel():
            win.destroy()

        ttk.Button(btn_frame, text="Cancelar", command=on_cancel, bootstyle="secondary", width=15).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Guardar Configuración", command=on_save, bootstyle="success", width=20).pack(side="right", padx=5)

        win.wait_window()
