from kivy.config import Config
# Config.set('graphics', 'width', '1280')
# Config.set('graphics', 'height', '800')
# Config.set('graphics', 'resizable', '1')

import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.network.urlrequest import UrlRequest
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import AsyncImage, Image
from kivy.graphics import Color, RoundedRectangle, Rectangle
import json
import socket
import threading
import time
import os

BG_COLOR = (0.17, 0.24, 0.31, 1)
PANEL_COLOR = (0.31, 0.36, 0.42, 1)
ACCENT_COLOR = (0.87, 0.41, 0.10, 1)
SUCCESS_COLOR = (0.36, 0.72, 0.36, 1)
INFO_COLOR = (0.36, 0.75, 0.87, 1)
DANGER_COLOR = (0.8, 0.2, 0.2, 1)

# ==========================================================
# CONFIGURACION: IP dinámica (Local) o URL Fija (Cloud)
# ==========================================================
# PARA PRUEBA EN LA NUBE: Pon aquí tu URL de PythonAnywhere, ej: "https://usuario.pythonanywhere.com"
# PARA USO LOCAL: Déjalo vacío "" para que use el auto-descubrimiento UDP
SERVER_URL = "https://Davis2025.pythonanywhere.com"
APK_VERSION = "1.1.9"

class ClickableBoxLayout(ButtonBehavior, BoxLayout):
    pass
class ProductCard(BoxLayout):
    def __init__(self, product_data, **kwargs):
        super().__init__(orientation='vertical', padding=2, spacing=2, **kwargs)
        self.product_data = product_data
        self.register_event_type('on_add_here')
        self.register_event_type('on_add_to_go')
        
        with self.canvas.before:
            Color(0.82, 0.84, 0.86, 1) # #d1d5db (Gris claro)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[5])
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        # Imagen
        import urllib.parse
        img_url = f"{SERVER_URL}/api/images/{urllib.parse.quote(product_data.get('nombre', ''))}"
        self.img_container = BoxLayout(size_hint_y=0.45)
        self.img = AsyncImage(source=img_url, fit_mode='contain')
        self.img_container.add_widget(self.img)
        
        # Si no hay imagen, mostrar Logo local
        def on_img_error(inst, val):
            self.img_container.clear_widgets()
            self.img_container.add_widget(Image(source='assets/logo.png', fit_mode='contain'))
        self.img.bind(on_error=on_img_error)
        
        # Nombre
        self.lbl_title = Label(text=f"{product_data.get('nombre')}", size_hint_y=0.2, halign='center', color=(0.17, 0.24, 0.31, 1), bold=True, font_size='12sp')
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        
        # Precio
        price_box = BoxLayout(size_hint_y=0.18, size_hint_x=0.8, pos_hint={'center_x': 0.5})
        with price_box.canvas.before:
            Color(0.15, 0.2, 0.25, 1)
            self.p_rect = Rectangle(pos=price_box.pos, size=price_box.size)
        def update_p_rect(inst, val):
            self.p_rect.pos = inst.pos
            self.p_rect.size = inst.size
        price_box.bind(pos=update_p_rect, size=update_p_rect)
        price_lbl = Label(text=f"${product_data.get('precio', 0):.2f}", bold=True, color=(1,1,1,1), font_size='16sp')
        price_box.add_widget(price_lbl)
        
        # Botones de Acción
        btn_box = BoxLayout(size_hint_y=0.17, spacing=2)
        btn_aqui = Button(text="Aquí", background_color=(0.12, 0.59, 0.71, 1), background_normal='', bold=True)
        btn_aqui.bind(on_press=lambda x: self.dispatch('on_add_here'))
        
        btn_llevar = Button(text="Llevar", background_color=(0.1, 0.6, 0.4, 1), background_normal='', bold=True)
        btn_llevar.bind(on_press=lambda x: self.dispatch('on_add_to_go'))
        
        btn_box.add_widget(btn_aqui)
        btn_box.add_widget(btn_llevar)
  
        self.add_widget(self.img_container)
        self.add_widget(self.lbl_title)
        self.add_widget(price_box)
        self.add_widget(btn_box)

    def on_add_here(self): pass
    def on_add_to_go(self): pass

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

class SunmiPrinter:
    @staticmethod
    def print_receipt(pedido_data):
        """Muestra una previsualización del ticket con formato fiscal profesional."""
        import datetime
        fecha = datetime.datetime.now().strftime('%d/%m/%Y %I:%M %p')
        num_fac = str(pedido_data.get('numero', '000000')).zfill(8)
        
        texto =  "              DGI               \n"
        texto += "      RUC: 8-765-4321 DV 01     \n"
        texto += "      PIK'TA GRILL  \n"
        texto += "  Vía Principal, Edif. Pik'ta   \n"
        texto += "      Chiriquí, Panamá          \n"
        texto += "          777-1234              \n"
        texto += "  COMPROBANTE AUXILIAR DE       \n"
        texto += "     FACTURA ELECTRÓNICA        \n"
        texto += "--------------------------------\n"
        texto += "  Factura de Operación Interna  \n"
        texto += f" # {num_fac}\n"
        texto += f" FECHA: {fecha}\n"
        texto += " SUCURSAL: 001\n"
        texto += " CAJA/PTO FACT: 001\n"
        texto += "--------------------------------\n"
        texto += " RECEPTOR: Consumidor final\n"
        texto += f" CLIENTE: {pedido_data.get('cliente', 'CLIENTE GENERAL')}\n"
        texto += "--------------------------------\n"
        texto += f"{'DESCRIPCION':<20} {'MONTO':>10}\n"
        texto += "--------------------------------\n"
        
        for item in pedido_data.get('items', []):
            cant = item.get('cantidad', item.get('qty', 1))
            nom = str(item.get('nombre', '')).upper()
            pre = item.get('precio_unitario', item.get('precio', 0))
            sub = pre * cant
            
            texto += f"{nom[:32]}\n"
            texto += f" {cant:.2f} X {pre:>8.2f} (0%)    {sub:>8.2f}\n"
            
        texto += "--------------------------------\n"
        total = pedido_data.get('total', 0)
        texto += f" SUBTOTAL                B/.{total:>8.2f}\n"
        texto += f" TOTAL                   B/.{total:>8.2f}\n"
        texto += "--------------------------------\n"
        metodo = pedido_data.get('metodo_pago', 'EFECTIVO')
        texto += f" {metodo:<15}         B/.{total:>8.2f}\n"
        texto += "--------------------------------\n"
        texto += "Consulte en: https://dgi-fep.mef.gob.pa\n"
        texto += "CUFE: FE01200001675920-1-680848...\n"
        texto += "      Gracias por su compra     \n"
        texto += "================================\n"

        content = BoxLayout(orientation='vertical', padding=10)
        scroll = ScrollView()
        lbl = Label(text=texto, font_name='RobotoMono-Regular' if os.path.exists('assets/fonts/RobotoMono-Regular.ttf') else 'Roboto',
                    font_size='14sp', size_hint_y=None, halign='left', valign='top')
        lbl.bind(texture_size=lbl.setter('size'))
        scroll.add_widget(lbl)
        content.add_widget(scroll)
        
        btn_cerrar = Button(text="CERRAR VISTA", size_hint_y=None, height=50, background_color=ACCENT_COLOR)
        content.add_widget(btn_cerrar)
        
        popup = Popup(title="Vista Previa de Ticket", content=content, size_hint=(0.9, 0.9))
        btn_cerrar.bind(on_press=popup.dismiss)
        popup.open()

    @staticmethod
    def print_closing_report(report_data):
        from kivy.utils import platform
        if platform != 'android':
            print("Impresión Sunmi solo soportada en Android.")
            return
            
        try:
            from jnius import autoclass
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            UUID = autoclass('java.util.UUID')
            
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled(): return
                
            paired_devices = adapter.getBondedDevices().toArray()
            sunmi_device = None
            for d in paired_devices:
                if d.getName() == 'InnerPrinter':
                    sunmi_device = d
                    break
                    
            if not sunmi_device: return
                
            spp_uuid = UUID.fromString('00001101-0000-1000-8000-00805F9B34FB')
            socket = sunmi_device.createRfcommSocketToServiceRecord(spp_uuid)
            socket.connect()
            out_stream = socket.getOutputStream()
            
            def send(data): out_stream.write(data)
            def out(text): send(text.encode('cp850', 'replace'))
            
            INIT = b'\x1b\x40'
            ALIGN_CENTER = b'\x1b\x61\x01'
            ALIGN_LEFT = b'\x1b\x61\x00'
            BOLD_ON = b'\x1b\x45\x01'
            BOLD_OFF = b'\x1b\x45\x00'
            FEED = b'\r\n'
            
            send(INIT)
            send(ALIGN_CENTER)
            send(BOLD_ON)
            out("********************************\r\n")
            out("   INFORME DE CIERRE DE CAJA    \r\n")
            out("********************************\r\n")
            send(BOLD_OFF)
            
            import datetime
            fecha = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
            out(f"Cierre:  {fecha}\r\n")
            out(f"Sesion:  {report_data.get('sesion_id', '')}\r\n")
            out("--------------------------------\r\n")
            
            send(ALIGN_LEFT)
            out(f"Total EFECTIVO:   ${report_data.get('efectivo', 0):>8.2f}\r\n")
            out(f"Total YAPPY:      ${report_data.get('yappy', 0):>8.2f}\r\n")
            out(f"Total TARJETA:    ${report_data.get('tarjeta', 0):>8.2f}\r\n")
            out("--------------------------------\r\n")
            out(f"Monto Inicial:    ${report_data.get('monto_inicial', 0):>8.2f}\r\n")
            out(f"Total Ventas:     ${report_data.get('total_ventas', 0):>8.2f}\r\n")
            out("================================\r\n")
            send(BOLD_ON)
            out(f"TOTAL EN CAJA:    ${report_data.get('total_en_caja', 0):>8.2f}\r\n")
            send(BOLD_OFF)
            out("================================\r\n")
            out(f"No. Tickets:      {report_data.get('tickets', 0):>8}\r\n")
            
            send(ALIGN_CENTER)
            out("\r\nSISTEMA POS PIK'TA - 2026\r\n")
            send(FEED * 4)
            
            out_stream.flush()
            socket.close()
        except Exception as e:
            print(f"Error imprimiendo reporte cierre: {e}")

    @staticmethod
    def open_drawer():
        from kivy.utils import platform
        if platform != 'android': return
        try:
            from jnius import autoclass
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled(): return
            paired_devices = adapter.getBondedDevices().toArray()
            sunmi_device = None
            for d in paired_devices:
                if d.getName() == 'InnerPrinter':
                    sunmi_device = d
                    break
            if not sunmi_device: return
            UUID = autoclass('java.util.UUID')
            spp_uuid = UUID.fromString('00001101-0000-1000-8000-00805F9B34FB')
            socket = sunmi_device.createRfcommSocketToServiceRecord(spp_uuid)
            socket.connect()
            out_stream = socket.getOutputStream()
            # Comando ESC/POS para abrir cajón (Pin 2/5)
            out_stream.write(b'\x1b\x70\x00\x19\xfa')
            out_stream.flush()
            socket.close()
        except Exception as e:
            print(f"Error abriendo cajón: {e}")

    @staticmethod
    def print_receipt_preview(pedido):
        """Genera una vista previa del ticket en pantalla en lugar de imprimir físicamente."""
        # Generar texto del ticket
        import datetime
        fecha = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        
        texto =  "      PIK'TA GRILL      \n"
        texto += "DONDE SI SABEMOS DE HAMBURGUESAS\n"
        texto += "--------------------------------\n"
        texto += f"Factura: {pedido.get('numero', pedido.get('id', 'N/A'))}\n"
        texto += f"Fecha:   {fecha}\n"
        texto += f"Mesa:    {pedido.get('mesa', 'Caja')}\n"
        texto += "--------------------------------\n"
        texto += f"{'Cant':<4} {'Desc':<18} {'Sub':>6}\n"
        for item in pedido.get('items', []):
            nom = item.get('nombre', '')[:17]
            qty = item.get('cantidad', 1)
            pre = float(item.get('precio_unitario', item.get('precio', 0)))
            texto += f"{qty:<4} {nom:<18} ${pre*qty:>6.2f}\n"
        
        texto += "--------------------------------\n"
        texto += f"TOTAL:           ${float(pedido.get('total', 0)):>10.2f}\n"
        texto += "--------------------------------\n"
        texto += "GRACIAS POR SU PREFERENCIA\n"

        from kivy.uix.popup import Popup
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        
        content = ScrollView()
        lbl = Label(text=texto, font_name='RobotoMono-Regular' if os.path.exists('assets/fonts/RobotoMono-Regular.ttf') else 'Roboto', 
                    font_size='14sp', size_hint_y=None, halign='left', valign='top', padding=(10, 10))
        lbl.bind(texture_size=lbl.setter('size'))
        content.add_widget(lbl)
        
        Popup(title="Documento de Venta (Pre-visualización)", content=content, size_hint=(0.9, 0.8)).open()

    @staticmethod
    def print_receipt(pedido_data):
        from kivy.utils import platform
        import os
        import datetime
        
        # SI ESTAMOS EN WINDOWS (Entorno de prueba)
        if platform != 'android':
            try:
                import tempfile
                fecha = datetime.datetime.now().strftime('%d/%m/%Y %I:%M %p')
                num_fac = str(pedido_data.get('numero', '000000')).zfill(8)
                
                # Crear ticket para Windows
                ticket = f"\n      PIK'TA GRILL SOLUTIONS\n"
                ticket += f"      FACTURA: {num_fac} | {fecha}\n"
                ticket += "--------------------------------\n"
                for item in pedido_data.get('items', []):
                    nom = item.get('nombre', '')
                    cant = item.get('cantidad', 1)
                    pre = float(item.get('precio', 0))
                    ticket += f"{nom[:20]:<20} {cant:>2} ${pre*cant:>7.2f}\n"
                ticket += "--------------------------------\n"
                ticket += f"TOTAL: B/.{float(pedido_data.get('total', 0)):.2f}\n\n"
                
                fd, path = tempfile.mkstemp(suffix=".txt")
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(ticket)
                
                # Abrir diálogo de impresión de Windows
                import win32api
                win32api.ShellExecute(0, "print", path, None, ".", 0)
                return
            except Exception as e:
                print(f"Error test Windows: {e}")
                SunmiPrinter.print_receipt_preview(pedido_data)
                return
            
        try:
            from jnius import autoclass, cast
            import datetime
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            current_activity = PythonActivity.mActivity
            
            fecha = datetime.datetime.now().strftime('%d/%m/%Y %I:%M %p')
            num_fac = str(pedido_data.get('numero', '000000')).zfill(8)
            cliente = pedido_data.get('cliente', 'CLIENTE GENERAL')
            total = float(pedido_data.get('total', 0))
            
            # Crear contenido HTML profesional para el diálogo de impresión
            html_content = f"""
            <html><body style='font-family:monospace; font-size:14px; padding: 20px;'>
                <center>
                    <h2 style='margin:0;'>PIK'TA GRILL SOLUTIONS</h2>
                    <p>RUC: 8-765-4321 DV 01</p>
                    <hr>
                    <h3>FACTURA: {num_fac}</h3>
                    <p>FECHA: {fecha}</p>
                    <p>CLIENTE: {cliente}</p>
                </center>
                <table width='100%' style='border-collapse: collapse;'>
                    <tr style='border-bottom: 1px solid black;'>
                        <th align='left'>DESC</th>
                        <th align='right'>CANT</th>
                        <th align='right'>SUB</th>
                    </tr>
            """
            for item in pedido_data.get('items', []):
                cant = item.get('cantidad', item.get('qty', 1))
                nom = item.get('nombre', '')
                pre = float(item.get('precio_unitario', item.get('precio', 0)))
                html_content += f"<tr><td>{nom}</td><td align='right'>{cant}</td><td align='right'>${pre*cant:.2f}</td></tr>"
            
            html_content += f"""
                </table>
                <hr>
                <div align='right' style='font-size: 18px;'><b>TOTAL: B/.{total:.2f}</b></div>
                <br>
                <center>
                    <p>¡Gracias por su preferencia!</p>
                    <p style='font-size: 10px;'>Consulte en: https://dgi-fep.mef.gob.pa</p>
                </center>
            </body></html>
            """
            
            # Lanzar el PrintManager de Android
            Context = autoclass('android.content.Context')
            PrintManager = autoclass('android.print.PrintManager')
            print_manager = cast(PrintManager, current_activity.getSystemService(Context.PRINT_SERVICE))
            
            WebView = autoclass('android.webkit.WebView')
            webview = WebView(current_activity)
            webview.loadDataWithBaseURL(None, html_content, "text/html", "UTF-8", None)
            
            job_name = f"Factura_Pikta_{num_fac}"
            print_adapter = webview.createPrintDocumentAdapter(job_name)
            print_manager.print(job_name, print_adapter, None)
            
        except Exception as e:
            print(f"Error en impresión: {e}")
            SunmiPrinter.print_receipt_preview(pedido_data)

    @staticmethod
    def print_closing_report(r):
        """Vista previa e impresión del reporte de cierre."""
        texto =  "*** REPORTE DE CIERRE ***\n"
        texto += f"Sesión: #{r.get('sesion_id', 'N/A')}\n"
        texto += f"Tickets: {r.get('tickets', 0)}\n"
        texto += "------------------------\n"
        texto += f"Ventas Totales: B/.{r.get('total_ventas', 0):.2f}\n"
        texto += f"Efectivo:      B/.{r.get('efectivo', 0):.2f}\n"
        texto += f"Yappy:         B/.{r.get('yappy', 0):.2f}\n"
        texto += f"Tarjeta:       B/.{r.get('tarjeta', 0):.2f}\n"
        texto += "------------------------\n"
        texto += f"Monto Inicial: B/.{r.get('monto_inicial', 0):.2f}\n"
        texto += f"TOTAL EN CAJA: B/.{r.get('total_en_caja', 0):.2f}\n"

        from kivy.uix.popup import Popup
        from kivy.uix.label import Label
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=texto, font_size='14sp', halign='center'))
        
        btn_print = Button(text="🖨️ IMPRIMIR REPORTE", size_hint_y=None, height=50, background_color=INFO_COLOR)
        content.add_widget(btn_print)
        
        pop = Popup(title="Reporte de Cierre", content=content, size_hint=(0.8, 0.7))
        
        def _print_report(instance):
            # Usar la lógica de impresión de sistema (HTML para Android/Windows)
            from kivy.utils import platform
            import os
            
            html = f"<html><body style='font-family:monospace;'><pre>{texto}</pre></body></html>"
            
            if platform == 'android':
                try:
                    from jnius import autoclass, cast
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    current_activity = PythonActivity.mActivity
                    Context = autoclass('android.content.Context')
                    PrintManager = autoclass('android.print.PrintManager')
                    print_manager = cast(PrintManager, current_activity.getSystemService(Context.PRINT_SERVICE))
                    WebView = autoclass('android.webkit.WebView')
                    webview = WebView(current_activity)
                    webview.loadDataWithBaseURL(None, html, "text/html", "UTF-8", None)
                    job_name = "Cierre_Caja_Pikta"
                    print_adapter = webview.createPrintDocumentAdapter(job_name)
                    print_manager.print(job_name, print_adapter, None)
                except Exception as e: print(f"Error print Android: {e}")
            else:
                try:
                    import tempfile
                    import win32api
                    fd, path = tempfile.mkstemp(suffix=".txt")
                    with os.fdopen(fd, 'w') as f: f.write(texto)
                    win32api.ShellExecute(0, "print", path, None, ".", 0)
                except Exception as e: print(f"Error print Win: {e}")
            pop.dismiss()

        btn_print.bind(on_press=_print_report)
        pop.open()


class GlobalState:
    user = None
    cart = []
    caja_cart = []
    mesa_actual = "Mesa 1"
    sesion_id = None


class APIClient:
    @staticmethod
    def login(username, password, totp_code, on_success, on_error):
        req_body = json.dumps({"username": username, "password": password, "totp_code": totp_code})
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/login",
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_menu(on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/menu",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_pedidos(on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/pedidos",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_historial_pedidos(search="", fecha="", on_success=None, on_error=None):
        import urllib.parse
        url = f"{SERVER_URL}/api/pedidos/historial?search={urllib.parse.quote(search)}&fecha={urllib.parse.quote(fecha)}"
        UrlRequest(url, on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def create_pedido(items, total, mesa, on_success, on_error):
        req_body = json.dumps({"items": items, "total": total, "mesa": mesa})
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/pedidos",
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def update_pedido_extras(pedido_id, items, total, on_success, on_error):
        req_body = json.dumps({"items": items, "total": total})
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/pedidos/{pedido_id}/extras", method='POST',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_ads(on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/publicidad",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def update_pedido(pedido_id, estado, on_success, on_error):
        req_body = json.dumps({"estado": estado})
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/pedidos/{pedido_id}", method='PUT',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_usuarios(on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/usuarios",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_inventario(on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/inventario",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_cierres(on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/cierres",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_cierre_detalle(sesion_id, on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/cierres/{sesion_id}",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_seguridad(on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/seguridad",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def abrir_caja(data, on_success, on_error):
        req_body = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/caja/abrir", method='POST',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def cerrar_caja(data, on_success, on_error):
        req_body = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/caja/cerrar", method='POST',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def get_pedidos_pendientes(on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/pedidos/pendientes",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def upload_product_image(product_name, file_path, on_success, on_error):
        import requests
        import threading
        def _upload():
            try:
                url = f"{SERVER_URL}/api/menu/upload_image"
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    data = {'product_name': product_name}
                    response = requests.post(url, files=files, data=data)
                    from kivy.clock import Clock
                    if response.status_code == 200:
                        Clock.schedule_once(lambda dt: on_success(None, response.json()))
                    else:
                        Clock.schedule_once(lambda dt: on_error(None, response.text))
            except Exception as e:
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: on_error(None, str(e)))
        
        threading.Thread(target=_upload, daemon=True).start()

    @staticmethod
    def cobrar_pedido(pedido_id, data, on_success, on_error):
        req_body = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/pedidos/cobrar/{pedido_id}", method='POST',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def crear_pedido_caja(data, on_success, on_error):
        req_body = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/caja/crear_pedido_caja", method='POST',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def check_caja_activa(usuario_id, on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/caja/activa/{usuario_id}",
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def abrir_cajon(on_success=None, on_error=None):
        UrlRequest(f"{SERVER_URL}/api/caja/abrir_cajon", method='POST',
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def upload_ad(file_path, on_success, on_error):
        """Sube un archivo de publicidad usando multipart/form-data."""
        import os
        filename = os.path.basename(file_path)
        try:
            from requests_toolbelt.multipart.encoder import MultipartEncoder
            import requests
            
            def upload_thread():
                try:
                    with open(file_path, 'rb') as f:
                        m = MultipartEncoder(fields={'file': (filename, f, 'application/octet-stream')})
                        r = requests.post(f"{SERVER_URL}/api/publicidad/upload", data=m, headers={'Content-Type': m.content_type})
                        if r.status_code == 200:
                            Clock.schedule_once(lambda dt: on_success(None, r.json()), 0)
                        else:
                            Clock.schedule_once(lambda dt: on_error(None, r.json() if r.headers.get('Content-Type')=='application/json' else r.text), 0)
                except Exception as e:
                    Clock.schedule_once(lambda dt: on_error(None, str(e)), 0)
            
            import threading
            threading.Thread(target=upload_thread, daemon=True).start()
            
        except ImportError:
            on_error(None, "Se requiere la librería 'requests' y 'requests_toolbelt' para subir archivos en Android.")

    @staticmethod
    def delete_ad(nombre, on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/publicidad/delete/{nombre}", method='DELETE',
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def create_usuario(data, on_success, on_error):
        req_body = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/usuarios", method='POST',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def update_usuario(user_id, data, on_success, on_error):
        req_body = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/usuarios/{user_id}", method='PUT',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def delete_usuario(user_id, on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/usuarios/{user_id}", method='DELETE',
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def update_inventario_item(item_id, data, on_success, on_error):
        req_body = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/inventario/{item_id}", method='PUT',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def delete_inventario_item(item_id, on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/inventario/{item_id}", method='DELETE',
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def create_menu_item(data, on_success, on_error):
        req_body = json.dumps(data)
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(f"{SERVER_URL}/api/menu", method='POST',
                   req_body=req_body, req_headers=headers,
                   on_success=on_success, on_failure=on_error, on_error=on_error)

    @staticmethod
    def delete_menu_item(product_id, on_success, on_error):
        UrlRequest(f"{SERVER_URL}/api/menu/{product_id}", method='DELETE',
                   on_success=on_success, on_failure=on_error, on_error=on_error)

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            # USAMOS EL LOGO COMO FONDO (Ajustado a la ruta real)
            self.bg_img = Rectangle(source='logo.png', pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        root = AnchorLayout(anchor_y='center') # Centrado real
        
        layout = BoxLayout(orientation='vertical', padding=[20, 20, 20, 20], spacing=20, 
                           size_hint=(None, None), width=450)
        layout.bind(minimum_height=layout.setter('height'))

        # Logo Principal
        logo = Image(source='logo.png', size_hint_y=None, height=180, fit_mode='contain')
        layout.add_widget(logo)
        
        card = BoxLayout(orientation='vertical', padding=[30, 40, 30, 40], spacing=15, size_hint_y=None)
        card.bind(minimum_height=card.setter('height'))
        with card.canvas.before:
            # Color semi-transparente (Efecto Cristal)
            Color(0.1, 0.15, 0.2, 0.85)
            self.card_rect = RoundedRectangle(radius=[20])
        card.bind(pos=self._update_card_rect, size=self._update_card_rect)

        self.username_input = TextInput(hint_text='Usuario', multiline=False,
                                        font_size='18sp', size_hint_y=None, height=50,
                                        background_color=(0.9, 0.9, 0.9, 1))
        self.password_input = TextInput(hint_text='Contraseña', password=True,
                                        multiline=False, font_size='18sp',
                                        size_hint_y=None, height=50,
                                        background_color=(0.9, 0.9, 0.9, 1))
        self.totp_input = TextInput(hint_text='Código 2FA (Solo Admin)',
                                        multiline=False, font_size='18sp',
                                        size_hint_y=None, height=50,
                                        background_color=(0.9, 0.9, 0.9, 1))
        card.add_widget(self.username_input)
        card.add_widget(self.password_input)
        card.add_widget(self.totp_input)

        self.login_btn = Button(text='INICIAR SESION', font_size='18sp', bold=True,
                                size_hint_y=None, height=60, background_color=ACCENT_COLOR)
        self.login_btn.bind(on_press=self.do_login)
        self.login_btn.disabled = True
        card.add_widget(self.login_btn)
        
        self.status_label = Label(text=f"Buscando servidor principal...",
                                   size_hint_y=None, height=30, color=(0.7, 0.7, 0.7, 1))
        card.add_widget(self.status_label)
        
        layout.add_widget(card)
        root.add_widget(layout)
        self.add_widget(root)
        
        self.start_udp_listener()

    def _update_bg(self, instance, value):
        self.bg_img.pos = instance.pos
        self.bg_img.size = instance.size

    def _update_card_rect(self, instance, value):
        self.card_rect.pos = instance.pos
        self.card_rect.size = instance.size

    def start_udp_listener(self):
        # Si ya hay una URL configurada (Cloud Mode), no buscamos por UDP
        if SERVER_URL and SERVER_URL.startswith("http"):
            self.status_label.text = f"Conectado a: {SERVER_URL}"
            self.login_btn.disabled = False
            return

        def listen():
            global SERVER_URL
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', 5005))
            sock.settimeout(2.0)
            
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    info = json.loads(data.decode('utf-8'))
                    if info.get('pikta_server'):
                        ip = info.get('ip', addr[0])
                        if ip == '127.0.0.1': ip = addr[0]
                        SERVER_URL = f"http://{ip}:{info.get('port', 5000)}"
                        Clock.schedule_once(lambda dt, found_ip=ip: self.on_server_found(found_ip), 0)
                        break
                except socket.timeout:
                    pass
                except Exception as e:
                    time.sleep(2)
            sock.close()
        
        threading.Thread(target=listen, daemon=True).start()
        
    def on_server_found(self, ip):
        self.status_label.text = f"Servidor conectado: {ip}"
        self.status_label.color = (0.2, 0.8, 0.2, 1)
        self.login_btn.disabled = False

    def update_status(self, text):
        self.status_label.text = text

    def do_login(self, instance):
        u = self.username_input.text.strip()
        p = self.password_input.text.strip()
        t = self.totp_input.text.strip()
        if not u or not p:
            self.status_label.text = "Ingrese usuario y contraseña"
            self.status_label.color = (1, 0, 0, 1)
            return
        self.status_label.text = "Conectando..."
        self.status_label.color = (1, 1, 1, 1)
        self.login_btn.disabled = True
        APIClient.login(u, p, t, self.on_login_success, self.on_login_error)

    def on_login_success(self, req, result):
        self.login_btn.disabled = False
        if result.get('status') == 'success':
            GlobalState.user = result.get('user')
            rol = GlobalState.user.get('rol', '').upper()
            self.username_input.text = ''
            self.password_input.text = ''
            self.totp_input.text = ''
            
            if 'PUBLICIDAD' in rol or 'TV' in rol:
                self.manager.current = 'ads'
            elif 'MESERO' in rol:
                self.manager.get_screen('pos').load_menu()
                self.manager.current = 'pos'
            elif 'COCINA' in rol:
                self.manager.current = 'kds'
            elif 'CAJERA' in rol or 'ADMIN' in rol:
                # Verificar sesión de caja activa
                def _on_caja_check(req, res):
                    if res.get('status') == 'success':
                        GlobalState.sesion_id = res.get('sesion_id')
                    self.manager.get_screen('caja').load_menu()
                    self.manager.current = 'caja'
                APIClient.check_caja_activa(GlobalState.user['id'], _on_caja_check, 
                                          lambda r, e: setattr(self.manager, 'current', 'caja'))
            else:
                self.manager.current = 'dashboard'
        else:
            self.status_label.text = result.get('message', 'Credenciales incorrectas')
            self.status_label.color = (1, 0.3, 0.3, 1)

    def on_login_error(self, req, error):
        self.login_btn.disabled = False
        if isinstance(error, dict) and 'message' in error:
            self.status_label.text = error['message']
        else:
            self.status_label.text = "Error de conexión o credenciales incorrectas"
        self.status_label.color = (1, 0.3, 0.3, 1)


class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        self.title_label = Label(text="Panel Principal", font_size='24sp', bold=True, size_hint_y=0.1, color=INFO_COLOR)
        self.layout.add_widget(self.title_label)
        
        self.grid = GridLayout(cols=2, spacing=15, size_hint_y=0.9)
        
        self.btn_pos = Button(text="📦\n\nMesero (POS)", background_color=SUCCESS_COLOR, background_normal='', font_size='18sp', bold=True, halign='center')
        self.btn_pos.bind(on_press=lambda x: self.go_to('pos'))
        self.grid.add_widget(self.btn_pos)
        
        self.btn_kds = Button(text="👨‍🍳\n\nCocina (KDS)", background_color=ACCENT_COLOR, background_normal='', font_size='18sp', bold=True, halign='center')
        self.btn_kds.bind(on_press=lambda x: self.go_to('kds'))
        self.grid.add_widget(self.btn_kds)
        
        self.btn_caja = Button(text="💰\n\nCaja Móvil", background_color=INFO_COLOR, background_normal='', font_size='18sp', bold=True, halign='center')
        self.btn_caja.bind(on_press=lambda x: self.go_to('caja'))
        self.grid.add_widget(self.btn_caja)

        self.btn_admin = Button(text="⚙️\n\nAdministración", background_color=(0.3, 0.4, 0.5, 1), background_normal='', font_size='18sp', bold=True, halign='center')
        self.btn_admin.bind(on_press=lambda x: self.go_to('admin'))
        self.grid.add_widget(self.btn_admin)

        
        self.btn_logout = Button(text="🚪\n\nCerrar Sesión", background_color=(0.8, 0.2, 0.2, 1), background_normal='', font_size='18sp', bold=True, halign='center')
        self.btn_logout.bind(on_press=self.logout)
        self.grid.add_widget(self.btn_logout)
        
        self.layout.add_widget(self.grid)
        self.add_widget(self.layout)

    def on_enter(self):
        if GlobalState.user:
            self.title_label.text = f"Bienvenido, {GlobalState.user.get('nombre_completo', '')}"
            rol = GlobalState.user.get('rol', '').upper()
            
            if 'ADMIN' in rol or 'SUPERVISOR' in rol:
                self.btn_pos.disabled = False
                self.btn_kds.disabled = False
                self.btn_caja.disabled = False
                self.btn_admin.disabled = False
            elif 'CAJERA' in rol:
                self.btn_pos.disabled = True
                self.btn_kds.disabled = True
                self.btn_caja.disabled = False
                self.btn_admin.disabled = True
            elif 'COCINA' in rol:
                self.btn_pos.disabled = True
                self.btn_kds.disabled = False
                self.btn_caja.disabled = True
                self.btn_admin.disabled = True
            elif 'PUBLICIDAD' in rol or 'TV' in rol:
                self.btn_pos.disabled = True
                self.btn_kds.disabled = True
                self.btn_caja.disabled = True
                self.btn_admin.disabled = True
            else:
                self.btn_pos.disabled = False
                self.btn_kds.disabled = True
                self.btn_caja.disabled = True
                self.btn_admin.disabled = True
                pass

    def go_to(self, screen_name):
        if screen_name == 'pos':
            self.manager.get_screen('pos').load_menu()
        self.manager.current = screen_name

    def logout(self, instance):
        GlobalState.user = None
        GlobalState.cart = [] # Limpiar carrito al cerrar sesión
        self.manager.current = 'login'


class POSScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.productos_data = []
        self.categorias_btns = []
        self.mesas_btns = []
        self.pending_orders = []
        self.active_order_id = None
        
        with self.canvas.before:
            Color(*BG_COLOR)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.layout = BoxLayout(orientation='vertical')
        
        # --- TOP BAR ---
        top_bar = BoxLayout(size_hint_y=None, height=60, padding=[10, 5], spacing=10)
        with top_bar.canvas.before:
            Color(*PANEL_COLOR)
            self.top_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=self._update_top_rect, size=self._update_top_rect)
        
        top_bar.add_widget(Label(text="PIK'TA MOBILE POS", bold=True, font_size='22sp', size_hint_x=0.5, halign='left'))
        
        btn_logout = Button(text="SALIR", size_hint_x=None, width=100, background_color=(0.8, 0.2, 0.2, 1), background_normal='')
        btn_logout.bind(on_press=self.logout)
        top_bar.add_widget(btn_logout)
        
        self.layout.add_widget(top_bar)

        # --- MAIN AREA (HORIZONTAL SPLIT) ---
        main_area = BoxLayout(orientation='horizontal', padding=10, spacing=10)
        
        # LEFT SIDE: Product Catalog (65%)
        left_side = BoxLayout(orientation='vertical', size_hint_x=0.65, spacing=10)
        
        # Categories Scroll
        cat_scroll = ScrollView(size_hint_y=None, height=55)
        self.cat_grid = BoxLayout(orientation='horizontal', size_hint_x=None, spacing=5)
        self.cat_grid.bind(minimum_width=self.cat_grid.setter('width'))
        cat_scroll.add_widget(self.cat_grid)
        left_side.add_widget(cat_scroll)
        
        # Products Grid
        prod_scroll = ScrollView()
        self.prod_grid = GridLayout(cols=3, spacing=10, size_hint_y=None, padding=5)
        self.prod_grid.bind(minimum_height=self.prod_grid.setter('height'))
        prod_scroll.add_widget(self.prod_grid)
        left_side.add_widget(prod_scroll)
        
        main_area.add_widget(left_side)
        
        Window.bind(on_resize=self._on_window_resize)
        self._on_window_resize()

        # RIGHT SIDE: Cart and Table Selection (35%)
        right_side = BoxLayout(orientation='vertical', size_hint_x=0.35, spacing=10)
        with right_side.canvas.before:
            Color(0.15, 0.2, 0.25, 1)
            self.right_rect = RoundedRectangle(pos=right_side.pos, size=right_side.size, radius=[10])
        right_side.bind(pos=self._update_right_rect, size=self._update_right_rect)

        # Mesas Selector (Grid para ver todas las mesas)
        right_side.add_widget(Label(text="Seleccionar Mesa", size_hint_y=None, height=30, bold=True))
        mesa_area = ScrollView(size_hint_y=None, height=130) # Altura para ver unas 3 filas
        self.mesas_grid = GridLayout(cols=4, spacing=5, size_hint_y=None, padding=5)
        self.mesas_grid.bind(minimum_height=self.mesas_grid.setter('height'))
        mesa_area.add_widget(self.mesas_grid)
        right_side.add_widget(mesa_area)

        # Cart View
        right_side.add_widget(Label(text="Pedido Actual", size_hint_y=None, height=30, bold=True))
        
        # Cart Items List
        self.cart_scroll = ScrollView()
        self.cart_grid = GridLayout(cols=1, spacing=2, size_hint_y=None)
        self.cart_grid.bind(minimum_height=self.cart_grid.setter('height'))
        self.cart_scroll.add_widget(self.cart_grid)
        right_side.add_widget(self.cart_scroll)

        # Footer Actions
        footer = BoxLayout(orientation='vertical', size_hint_y=None, height=120, padding=10, spacing=10)
        self.cart_total_lbl = Label(text="Total: $0.00", bold=True, font_size='20sp')
        footer.add_widget(self.cart_total_lbl)
        
        self.order_status_lbl = Label(text="", font_size='12sp', color=(1, 0.8, 0, 1), size_hint_y=None, height=20)
        footer.add_widget(self.order_status_lbl)

        btn_box = BoxLayout(spacing=10)
        btn_clear = Button(text="Limpiar", background_color=(0.8, 0.2, 0.2, 1), background_normal='', size_hint_x=0.3)
        btn_clear.bind(on_press=self.clear_cart)
        
        self.btn_send = Button(text="ENVIAR", background_color=ACCENT_COLOR, background_normal='', bold=True, size_hint_x=0.7)
        self.btn_send.bind(on_press=self.send_order)
        
        btn_box.add_widget(btn_clear)
        btn_box.add_widget(self.btn_send)
        footer.add_widget(btn_box)
        
        right_side.add_widget(footer)
        
        main_area.add_widget(right_side)
        self.layout.add_widget(main_area)
        self.add_widget(self.layout)

    def _on_window_resize(self, *args):
        # Ajustar columnas de productos según el ancho de pantalla
        if Window.width > 1400: self.prod_grid.cols = 5
        elif Window.width > 1100: self.prod_grid.cols = 4
        elif Window.width > 800: self.prod_grid.cols = 3
        else: self.prod_grid.cols = 2

    def _update_top_rect(self, inst, val):
        self.top_rect.pos = inst.pos
        self.top_rect.size = inst.size
    def _update_right_rect(self, inst, val):
        self.right_rect.pos = inst.pos
        self.right_rect.size = inst.size
    def update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def on_enter(self):
        self.load_menu()
        self.load_pending_orders()
        # Setup Mesas (Hasta 20 mesas)
        self.mesas_grid.clear_widgets()
        self.mesas_btns = []
        for i in range(1, 21):
            name = f"Mesa {i}"
            btn = Button(text=str(i), size_hint_y=None, height=40, background_normal='', background_color=(0.3, 0.4, 0.5, 1))
            btn.bind(on_press=lambda inst, n=name: self.select_mesa(n, inst))
            self.mesas_btns.append(btn)
            self.mesas_grid.add_widget(btn)
        
        btn_llevar = Button(text="LLEVAR", size_hint_y=None, height=40, background_normal='', background_color=(0.3, 0.4, 0.5, 1))
        btn_llevar.bind(on_press=lambda inst: self.select_mesa("Para Llevar", inst))
        self.mesas_btns.append(btn_llevar)
        self.mesas_grid.add_widget(btn_llevar)
        
        if self.mesas_btns:
            self.select_mesa("Mesa 1", self.mesas_btns[0])

    def load_pending_orders(self):
        APIClient.get_pedidos_pendientes(self.on_pending_success, lambda r,e: None)

    def on_pending_success(self, req, result):
        if result.get('status') == 'success':
            self.pending_orders = result.get('data', [])
            self.update_active_order_status()

    def update_active_order_status(self):
        mesa = GlobalState.mesa_actual
        self.active_order_id = None
        self.order_status_lbl.text = ""
        self.btn_send.text = "ENVIAR A COCINA"
        
        for p in self.pending_orders:
            if p.get('mesa') == mesa:
                self.active_order_id = p.get('id')
                self.order_status_lbl.text = f"Pedido activo #{self.active_order_id} detectado"
                self.btn_send.text = "AGREGAR A PEDIDO"
                break
        
    def select_mesa(self, nombre_mesa, btn_instance):
        GlobalState.mesa_actual = nombre_mesa
        for b in self.mesas_btns:
            b.background_color = (0.3, 0.4, 0.5, 1) # Inactive
        btn_instance.background_color = ACCENT_COLOR # Active
        self.update_active_order_status()

    def select_category(self, nombre_cat, btn_instance):
        for b in self.categorias_btns:
            b.background_color = (0.17, 0.24, 0.31, 1) # Inactive
        btn_instance.background_color = (0.94, 0.68, 0.30, 1) # Active
        self.render_products(nombre_cat)

    def load_menu(self):
        APIClient.get_menu(self.on_menu_success, self.on_menu_error)

    def on_menu_success(self, req, result):
        if result.get('status') == 'success':
            self.productos_data = result.get('data', [])
            categorias = list(set([p.get('categoria', 'Otros') for p in self.productos_data]))
            categorias.insert(0, 'Todas')
            
            self.cat_grid.clear_widgets()
            self.categorias_btns = []
            
            for c in categorias:
                btn = Button(text=c, size_hint_x=None, width=100, background_normal='', background_color=(0.17, 0.24, 0.31, 1))
                btn.bind(on_press=lambda instance, c_name=c: self.select_category(c_name, instance))
                self.categorias_btns.append(btn)
                self.cat_grid.add_widget(btn)
            
            if self.categorias_btns:
                self.select_category('Todas', self.categorias_btns[0])
                
            self.render_cart()

    def on_menu_error(self, req, error):
        pass

    def render_products(self, category):
        self.prod_grid.clear_widgets()
        for p in self.productos_data:
            if category == 'Todas' or p.get('categoria', 'Otros') == category:
                card = ProductCard(product_data=p, size_hint_y=None, height=200) # Un poco más alto para los 2 botones
                card.bind(on_add_here=lambda inst, prod=p: self.add_to_cart(prod, False))
                card.bind(on_add_to_go=lambda inst, prod=p: self.add_to_cart(prod, True))
                self.prod_grid.add_widget(card)

    def add_to_cart(self, p, para_llevar):
        nombre = p['nombre']
        if para_llevar:
            nombre += " (LLEVAR)"
        else:
            nombre += " (AQUÍ)"
            
        for item in GlobalState.cart:
            if item['nombre'] == nombre:
                item['cantidad'] += 1
                item['subtotal'] = item['cantidad'] * item['precio_unitario']
                self.render_cart()
                return
        
        GlobalState.cart.append({
            'nombre': nombre,
            'precio_unitario': p['precio'],
            'cantidad': 1,
            'subtotal': p['precio'],
            'para_llevar': para_llevar
        })
        self.render_cart()

    def toggle_llevar(self, idx):
        if 0 <= idx < len(GlobalState.cart):
            item = GlobalState.cart[idx]
            item['para_llevar'] = not item.get('para_llevar', False)
            if item['para_llevar'] and " (LLEVAR)" not in item['nombre']:
                item['nombre'] += " (LLEVAR)"
            elif not item['para_llevar']:
                item['nombre'] = item['nombre'].replace(" (LLEVAR)", "")
            self.render_cart()

    def render_cart(self):
        self.cart_grid.clear_widgets()
        total = 0
        for idx, item in enumerate(GlobalState.cart):
            total += item['subtotal']
            row = BoxLayout(size_hint_y=None, height=45, padding=2, spacing=5)
            with row.canvas.before:
                Color(0.2, 0.25, 0.3, 1)
                r_rect = Rectangle(pos=row.pos, size=row.size)
            def _ur(inst, val, r=r_rect):
                r.pos = inst.pos
                r.size = inst.size
            row.bind(pos=_ur, size=_ur)

            lbl_n = Label(text=f"{item['nombre']}", halign='left', size_hint_x=0.45, font_size='13sp')
            row.add_widget(lbl_n)
            row.add_widget(Label(text=f"{item['cantidad']}", size_hint_x=0.1, font_size='13sp'))
            row.add_widget(Label(text=f"${item['subtotal']:.2f}", size_hint_x=0.2, font_size='13sp'))
            
            # Botón Llevar individual
            btn_ll = Button(text="🎁" if item.get('para_llevar') else "🏠", size_hint_x=0.12, background_normal='', background_color=(0.1, 0.6, 0.4, 1))
            btn_ll.bind(on_press=lambda x, i=idx: self.toggle_llevar(i))
            row.add_widget(btn_ll)

            btn_del = Button(text="X", size_hint_x=0.13, background_color=(0.8, 0.2, 0.2, 1), background_normal='')
            btn_del.bind(on_press=lambda x, i=idx: self.remove_item(i))
            row.add_widget(btn_del)
            
            self.cart_grid.add_widget(row)
            
        self.cart_total_lbl.text = f"Total: ${total:.2f}"

    def remove_item(self, idx):
        if 0 <= idx < len(GlobalState.cart):
            del GlobalState.cart[idx]
            self.render_cart()
            
    def clear_cart(self, instance):
        GlobalState.cart = []
        self.render_cart()

    def send_order(self, instance):
        if not GlobalState.cart:
            return
        
        try:
            total = sum(i['subtotal'] for i in GlobalState.cart)
            self.btn_send.text = "Enviando..."
            self.btn_send.disabled = True
            
            if self.active_order_id:
                APIClient.update_pedido_extras(
                    self.active_order_id, GlobalState.cart, total,
                    self.on_order_success, self.on_order_error
                )
            else:
                APIClient.create_pedido(
                    GlobalState.cart, total, GlobalState.mesa_actual,
                    self.on_order_success, self.on_order_error
                )
        except Exception as e:
            self.btn_send.disabled = False
            self.btn_send.text = "ENVIAR A COCINA"
            Popup(title="Error Crítico", content=Label(text=f"Error interno:\n{str(e)}"), size_hint=(0.8, 0.4)).open()

    def on_order_success(self, req, result):
        self.btn_send.disabled = False
        self.btn_send.text = "ENVIAR A COCINA"
        if result.get('status') == 'success':
            self.clear_cart(None)
            self.load_pending_orders()
        else:
            self.on_order_error(req, result.get('message', 'Error desconocido'))

    def on_order_error(self, req, error):
        self.btn_send.disabled = False
        self.btn_send.text = "ERROR - REINTENTAR"
        print(f"Error al enviar pedido: {error}")
        Popup(title="Error", content=Label(text="Fallo al enviar pedido"), size_hint=(0.8, 0.3)).open()

    def logout(self, instance):
        self.manager.current = 'dashboard'

class KDSCard(BoxLayout):
    def __init__(self, pedido, on_action, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=320, spacing=0, **kwargs)
        self.pedido = pedido
        estado = pedido.get('estado', 'RECIBIDO')
        
        if estado == 'RECIBIDO':
            header_color = (0.8, 0.2, 0.2, 1) # Rojo
        elif estado == 'PREPARANDO':
            header_color = (0.94, 0.68, 0.30, 1) # Naranja
        else:
            header_color = (0.3, 0.3, 0.3, 1)

        with self.canvas.before:
            Color(*PANEL_COLOR)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self.bind(pos=self._update_rect, size=self._update_rect)

        # 1. Cabecera (Siempre arriba)
        header = BoxLayout(size_hint_y=None, height=50, padding=[10, 0])
        with header.canvas.before:
            Color(*header_color)
            self.h_rect = RoundedRectangle(pos=header.pos, size=header.size, radius=[10, 10, 0, 0])
        header.bind(pos=self._update_h_rect, size=self._update_h_rect)

        title_text = f"#{pedido.get('id')} - {pedido.get('mesa')}"
        header.add_widget(Label(text=title_text, bold=True, halign='left', size_hint_x=0.7))
        
        self.timer_lbl = Label(text="0s", bold=True, halign='right', size_hint_x=0.3)
        header.add_widget(self.timer_lbl)
        self.add_widget(header)

        # 2. Lista de Items (Cuerpo)
        items_text = ""
        items_list = pedido.get('items', [])
        if not items_list:
            items_text = "(Sin productos)"
        else:
            for i in items_list:
                items_text += f"• {i.get('cantidad', 1)}x {i.get('nombre', '')}\n"

        items_scroll = ScrollView(size_hint_y=1)
        items_lbl = Label(text=items_text, size_hint_y=None, halign='left', valign='top', 
                          font_size='15sp', padding=(15, 15), color=(1,1,1,1))
        items_lbl.bind(texture_size=items_lbl.setter('size'))
        items_scroll.add_widget(items_lbl)
        self.add_widget(items_scroll)

        # 3. Botones de Acción (Abajo)
        btn_box = BoxLayout(size_hint_y=None, height=60, padding=8)
        if estado == 'RECIBIDO':
            btn = Button(text="PREPARAR", background_color=ACCENT_COLOR, bold=True, background_normal='', font_size='16sp')
            btn.bind(on_press=lambda x: on_action(pedido['id'], 'PREPARANDO'))
            btn_box.add_widget(btn)
        elif estado == 'PREPARANDO':
            btn = Button(text="LISTO", background_color=SUCCESS_COLOR, bold=True, background_normal='', font_size='16sp')
            btn.bind(on_press=lambda x: on_action(pedido['id'], 'LISTO'))
            btn_box.add_widget(btn)
        
        self.add_widget(btn_box)
        self.update_timer()

    def update_timer(self, *args):
        from datetime import datetime, timedelta
        estado = self.pedido.get('estado', 'RECIBIDO')
        
        if estado in ('RECIBIDO', 'COBRADO'):
            self.timer_lbl.text = "Esperando..."
            return
            
        try:
            prep_start = self.pedido.get('preparacion_inicio', '')
            if not prep_start:
                # Si no tiene inicio pero está en preparación, usamos el tiempo desde creación como fallback
                prep_start = self.pedido.get('created_at', '')
            
            if not prep_start:
                self.timer_lbl.text = "--"
                return

            s = prep_start.replace('T', ' ').split('.')[0].replace('Z', '')
            dt = datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
            
            elapsed = datetime.now() - dt
            dur_min = self.pedido.get('preparacion_duracion')
            if dur_min is None: dur_min = 15 # Default Windows
            
            remaining = timedelta(minutes=dur_min) - elapsed
            total_sec = int(remaining.total_seconds())
            
            if total_sec <= 0:
                self.timer_lbl.text = "¡TIEMPO AGOTADO!"
            else:
                mins = total_sec // 60
                secs = total_sec % 60
                self.timer_lbl.text = f"{mins}:{secs:02d}"
        except:
            self.timer_lbl.text = "0s"

    def _update_rect(self, inst, val):
        self.rect.pos = inst.pos
        self.rect.size = inst.size
    def _update_h_rect(self, inst, val):
        self.h_rect.pos = inst.pos
        self.h_rect.size = inst.size

class KDSScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.refresh_event = None
        self.layout = BoxLayout(orientation='vertical')

        # Top Bar
        top_bar = BoxLayout(size_hint_y=None, height=60, padding=10, spacing=10)
        with top_bar.canvas.before:
            Color(0.12, 0.17, 0.23, 1)
            self.top_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=self._update_top_rect, size=self._update_top_rect)

        self.title_label = Label(text="PANEL DE COCINA (KDS)", font_size='20sp',
                                  bold=True, halign='left')
        self.title_label.bind(size=self.title_label.setter('text_size'))
        btn_refresh = Button(text="Refrescar", size_hint_x=None, width=110,
                             background_color=INFO_COLOR, bold=True)
        btn_refresh.bind(on_press=self.load_orders)
        btn_back = Button(text="VOLVER", size_hint_x=None, width=90,
                            background_color=(0.4, 0.4, 0.4, 1), bold=True)
        btn_back.bind(on_press=self.go_back)
        top_bar.add_widget(self.title_label)
        
        self.clock_lbl = Label(text="--:--:--", font_size='18sp', bold=True, color=(1, 1, 1, 1), size_hint_x=None, width=120)
        top_bar.add_widget(self.clock_lbl)

        top_bar.add_widget(btn_refresh)
        top_bar.add_widget(btn_back)
        self.layout.add_widget(top_bar)

        self.scroll = ScrollView(size_hint_y=1)
        # 3 columnas por defecto
        self.grid = GridLayout(cols=3 if Window.width > Window.height else 1, spacing=15, padding=15, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        self.layout.add_widget(self.scroll)

        self.add_widget(self.layout)
        Window.bind(on_resize=self._on_resize)

    def _on_resize(self, *args):
        self.grid.cols = 3 if Window.width > Window.height else 1

    def _update_top_rect(self, inst, val):
        self.top_rect.pos = inst.pos
        self.top_rect.size = inst.size

    def on_enter(self):
        self.load_orders()
        self.refresh_event = Clock.schedule_interval(lambda dt: self.load_orders(), 10)
        # Actualizar los tiempos locales cada segundo para que se vea el avance
        self.timer_tick = Clock.schedule_interval(self.update_local_timers, 1)

    def on_leave(self):
        if self.refresh_event:
            self.refresh_event.cancel()
            self.refresh_event = None
        if hasattr(self, 'timer_tick') and self.timer_tick:
            self.timer_tick.cancel()

    def update_local_timers(self, dt):
        from datetime import datetime
        # Actualizar reloj principal
        self.clock_lbl.text = datetime.now().strftime('%H:%M:%S')
        
        # Actualizar tarjetas
        for card in self.grid.children:
            if isinstance(card, KDSCard):
                card.update_timer()

    def load_orders(self, *args):
        APIClient.get_pedidos(self.on_orders_success, self.on_orders_error)

    def on_orders_success(self, req, result):
        self.grid.clear_widgets()
        if result.get('status') == 'success':
            pedidos = result.get('data', [])
            pedidos.sort(key=lambda x: x.get('id', 0)) # Más antiguos primero
            
            if not pedidos:
                self.grid.add_widget(Label(text="No hay pedidos activos",
                                           size_hint_y=None, height=100))
                return

            # Ajustar columnas dinámicamente según ancho actual
            self.grid.cols = 3 if Window.width > Window.height else 1

            for p in pedidos:
                card = KDSCard(pedido=p, on_action=self.change_status)
                self.grid.add_widget(card)

    def on_orders_error(self, req, error):
        pass

    def change_status(self, pedido_id, nuevo_estado):
        def on_err(req, err):
            Popup(title="Error", content=Label(text=f"No se pudo actualizar:\n{err}"), size_hint=(0.8, 0.4)).open()

        APIClient.update_pedido(pedido_id, nuevo_estado,
                                lambda r, res: self.load_orders(),
                                on_err)

    def go_back(self, instance):
        self.manager.current = 'dashboard'


class CajaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.productos_data = []
        self.categorias_btns = []
        self.pedidos_pendientes = []
        self.current_tab = "venta" # "venta" o "cobros"
        self.editing_pedido_id = None # Para modo "Agregar Extras"
        self.selected_item_idx = -1
        
        self.main_layout = BoxLayout(orientation='vertical')
        
        # 1. Header (Replica Desktop) - Row 1 (User Info)
        top_bar = BoxLayout(size_hint_y=None, height=50, padding=[15, 5])
        with top_bar.canvas.before:
            Color(0.15, 0.2, 0.25, 1)
            self.top_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=self._update_top_rect, size=self._update_top_rect)
        
        user_name = GlobalState.user['nombre_completo'] if GlobalState.user else "Usuario"
        top_bar.add_widget(Label(text=f"Bienvenido(a), {user_name}", halign='left', size_hint_x=0.7, text_size=(Window.width*0.7, None)))
        
        btn_logout = Button(text="Cerrar Sesión", size_hint_x=0.2, background_color=(0.8, 0.2, 0.2, 1), font_size='12sp')
        btn_logout.bind(on_press=self.logout_action)
        top_bar.add_widget(btn_logout)
        self.main_layout.add_widget(top_bar)

        # Row 2 (System Name)
        sys_bar = BoxLayout(size_hint_y=None, height=40, padding=[15, 0])
        with sys_bar.canvas.before:
            Color(0.15, 0.2, 0.25, 1)
            self.sys_rect = Rectangle(pos=sys_bar.pos, size=sys_bar.size)
        sys_bar.bind(pos=self._update_sys_rect, size=self._update_sys_rect)
        sys_bar.add_widget(Label(text="SISTEMA POS PIK'TA", bold=True, font_size='22sp', halign='left', text_size=(Window.width, None)))
        self.main_layout.add_widget(sys_bar)

        # Row 3 (Cyan Sub-header)
        sub_header = BoxLayout(size_hint_y=None, height=60, padding=10, spacing=10)
        with sub_header.canvas.before:
            Color(0.12, 0.59, 0.71, 1) # #1e96b3
            self.sh_rect = Rectangle(pos=sub_header.pos, size=sub_header.size)
        sub_header.bind(pos=self._update_sh_rect, size=self._update_sh_rect)
        
        sub_header.add_widget(Label(text="🛒 PUNTO DE VENTA (Caja)", bold=True, font_size='18sp', size_hint_x=0.4))
        
        btn_cerrar_caja = Button(text="Cerrar Caja", size_hint_x=0.2, background_color=(0.8, 0.2, 0.2, 1))
        btn_cerrar_caja.bind(on_press=self.confirmar_cierre)
        sub_header.add_widget(btn_cerrar_caja)
        
        btn_abrir_caja = Button(text="Abrir Caja", size_hint_x=0.2, background_color=SUCCESS_COLOR)
        btn_abrir_caja.bind(on_press=self.show_abrir_caja)
        sub_header.add_widget(btn_abrir_caja)
        
        btn_regresar = Button(text="Regresar", size_hint_x=0.2, background_color=(0.5, 0.5, 0.5, 1))
        btn_regresar.bind(on_press=self.go_back)
        sub_header.add_widget(btn_regresar)
        
        self.main_layout.add_widget(sub_header)
        
        # 2. Tabs Selector (subtle style)
        tabs_bar = BoxLayout(size_hint_y=None, height=40, spacing=2, padding=[10, 0])
        self.btn_tab_venta = Button(text="Venta Directa", bold=True, background_color=(0.2, 0.25, 0.3, 1), background_normal='')
        self.btn_tab_venta.bind(on_press=lambda x: self.switch_tab("venta"))
        self.btn_tab_cobros = Button(text="Cobrar Mesas", bold=True, background_color=(0.1, 0.15, 0.2, 1), background_normal='')
        self.btn_tab_cobros.bind(on_press=lambda x: self.switch_tab("cobros"))
        tabs_bar.add_widget(self.btn_tab_venta)
        tabs_bar.add_widget(self.btn_tab_cobros)
        self.main_layout.add_widget(tabs_bar)
        
        # 3. Content Area
        self.content_area = BoxLayout()
        self.main_layout.add_widget(self.content_area)
        
        # 4. Footer
        footer = BoxLayout(size_hint_y=None, height=30)
        with footer.canvas.before:
            Color(0.1, 0.15, 0.2, 1)
            self.foot_rect = Rectangle(pos=footer.pos, size=footer.size)
        footer.bind(pos=self._update_foot_rect, size=self._update_foot_rect)
        footer.add_widget(Label(text="SISTEMA POS PIK'TA | Desarrollado por YAFA SOLUTIONS © 2026", font_size='10sp', color=(0.7,0.7,0.7,1)))
        self.main_layout.add_widget(footer)
        
        # Pre-create Layouts
        self._setup_venta_layout()
        self._setup_cobros_layout()
        
        self.add_widget(self.main_layout)

    def _update_top_rect(self, inst, val): self.top_rect.pos = inst.pos; self.top_rect.size = inst.size
    def _update_sys_rect(self, inst, val): self.sys_rect.pos = inst.pos; self.sys_rect.size = inst.size
    def _update_sh_rect(self, inst, val): self.sh_rect.pos = inst.pos; self.sh_rect.size = inst.size
    def _update_foot_rect(self, inst, val): self.foot_rect.pos = inst.pos; self.foot_rect.size = inst.size

    def logout_action(self, instance):
        GlobalState.user = None
        self.manager.current = 'login'

    def _update_header_rect(self, inst, val):
        self.header_rect.pos = inst.pos
        self.header_rect.size = inst.size

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        self.content_area.clear_widgets()
        if tab_name == "venta":
            self.btn_tab_venta.background_color = (0.2, 0.25, 0.3, 1)
            self.btn_tab_cobros.background_color = (0.1, 0.15, 0.2, 1)
            self.content_area.add_widget(self.venta_layout)
            self.load_menu()
        else:
            self.btn_tab_venta.background_color = (0.1, 0.15, 0.2, 1)
            self.btn_tab_cobros.background_color = (0.2, 0.25, 0.3, 1)
            self.content_area.add_widget(self.cobros_layout)
            self.load_pedidos_pendientes()

    def _setup_venta_layout(self):
        self.venta_layout = BoxLayout(orientation='horizontal')
        self.selected_item_idx = -1
        
        # Left: Categories + Products
        left_side = BoxLayout(orientation='vertical', size_hint_x=0.6)
        
        # Categorías (Estilo sutil como la imagen)
        self.cat_grid = GridLayout(rows=1, spacing=5, size_hint_y=None, height=45, padding=5)
        left_side.add_widget(self.cat_grid)
        
        # Grid de productos
        prod_scroll = ScrollView()
        self.prod_grid = GridLayout(cols=3, spacing=10, padding=10, size_hint_y=None)
        self.prod_grid.bind(minimum_height=self.prod_grid.setter('height'))
        prod_scroll.add_widget(self.prod_grid)
        left_side.add_widget(prod_scroll)
        
        self.venta_layout.add_widget(left_side)
        
        # Right: Order Summary (Cart)
        right_side = BoxLayout(orientation='vertical', size_hint_x=0.4, padding=5, spacing=5)
        with right_side.canvas.before:
            Color(0.2, 0.25, 0.3, 1)
            self.cart_bg = Rectangle(pos=right_side.pos, size=right_side.size)
        right_side.bind(pos=self._update_cart_bg, size=self._update_cart_bg)
        
        right_side.add_widget(Label(text="ORDEN ACTUAL", bold=True, size_hint_y=None, height=35))
        
        # Table Header
        h_row = BoxLayout(size_hint_y=None, height=35, padding=[5, 0])
        with h_row.canvas.before:
            Color(0.2, 0.25, 0.3, 1)
            Rectangle(pos=h_row.pos, size=h_row.size)
        
        h_row.add_widget(Label(text="Producto", size_hint_x=0.4, font_size='11sp', bold=True, halign='left'))
        h_row.add_widget(Label(text="Cant", size_hint_x=0.2, font_size='11sp', bold=True))
        h_row.add_widget(Label(text="Precio", size_hint_x=0.2, font_size='11sp', bold=True))
        h_row.add_widget(Label(text="Subtotal", size_hint_x=0.2, font_size='11sp', bold=True))
        
        # Ensure header labels also align left where needed
        for child in h_row.children:
            if isinstance(child, Label):
                child.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        
        right_side.add_widget(h_row)

        cart_scroll = ScrollView()
        self.cart_grid = GridLayout(cols=1, spacing=1, size_hint_y=None)
        self.cart_grid.bind(minimum_height=self.cart_grid.setter('height'))
        cart_scroll.add_widget(self.cart_grid)
        right_side.add_widget(cart_scroll)
        
        self.lbl_total_caja = Label(text="Total: $0.00", bold=True, font_size='22sp', size_hint_y=None, height=50, halign='left')
        self.lbl_total_caja.bind(size=self.lbl_total_caja.setter('text_size'))
        right_side.add_widget(self.lbl_total_caja)
        

        
        btn_quitar = Button(text="Quitar Item", background_color=(0.85, 0.32, 0.31, 1), size_hint_y=None, height=40, font_size='14sp')
        btn_quitar.bind(on_press=lambda x: self.remove_selected_item())
        right_side.add_widget(btn_quitar)
        
        btn_confirmar = Button(text="CONFIRMAR PEDIDO", background_color=SUCCESS_COLOR, bold=True, size_hint_y=None, height=55)
        btn_confirmar.bind(on_press=self.confirmar_pedido_caja)
        right_side.add_widget(btn_confirmar)
        
        self.venta_layout.add_widget(right_side)

    def _update_cart_bg(self, inst, val):
        self.cart_bg.pos = inst.pos
        self.cart_bg.size = inst.size

    def _setup_cobros_layout(self):
        self.cobros_layout = BoxLayout(orientation='horizontal', padding=5, spacing=5)
        self.selected_pedido = None
        
        # --- LEFT SIDE: LIST ---
        left_side = BoxLayout(orientation='vertical', size_hint_x=0.35)
        left_side.add_widget(Label(text="PEDIDOS PENDIENTES", bold=True, size_hint_y=None, height=35))
        
        # Table Header
        h_row = BoxLayout(size_hint_y=None, height=30)
        with h_row.canvas.before:
            Color(0.12, 0.59, 0.71, 1)
            Rectangle(pos=h_row.pos, size=h_row.size)
        h_row.add_widget(Label(text="ID", size_hint_x=0.2, font_size='11sp', bold=True))
        h_row.add_widget(Label(text="Número", size_hint_x=0.4, font_size='11sp', bold=True))
        h_row.add_widget(Label(text="Mesa", size_hint_x=0.2, font_size='11sp', bold=True))
        h_row.add_widget(Label(text="Total", size_hint_x=0.2, font_size='11sp', bold=True))
        left_side.add_widget(h_row)

        self.cobros_scroll = ScrollView()
        self.cobros_grid = GridLayout(cols=1, spacing=2, size_hint_y=None)
        self.cobros_grid.bind(minimum_height=self.cobros_grid.setter('height'))
        self.cobros_scroll.add_widget(self.cobros_grid)
        left_side.add_widget(self.cobros_scroll)
        
        btn_update = Button(text="Actualizar Lista", size_hint_y=None, height=45, background_color=(0.17, 0.24, 0.31, 1))
        btn_update.bind(on_press=lambda x: self.load_pedidos_pendientes())
        left_side.add_widget(btn_update)
        
        self.cobros_layout.add_widget(left_side)
        
        # --- RIGHT SIDE: DETAILS & PAYMENT ---
        right_side = BoxLayout(orientation='vertical', size_hint_x=0.65, padding=5, spacing=5)
        with right_side.canvas.before:
            Color(0.2, 0.25, 0.3, 1)
            self.rs_rect = Rectangle(pos=right_side.pos, size=right_side.size)
        right_side.bind(pos=self._update_rs_rect, size=self._update_rs_rect)
        
        right_side.add_widget(Label(text="DETALLE DE CUENTA", bold=True, size_hint_y=None, height=35))
        
        # List of items in selected order
        self.details_grid = GridLayout(cols=1, spacing=1, size_hint_y=None)
        self.details_grid.bind(minimum_height=self.details_grid.setter('height'))
        details_scroll = ScrollView(size_hint_y=0.3)
        details_scroll.add_widget(self.details_grid)
        right_side.add_widget(details_scroll)
        
        # Total a Cobrar
        self.lbl_total_cobro = Label(text="Total a Cobrar: $0.00", bold=True, font_size='24sp', size_hint_y=None, height=50)
        right_side.add_widget(self.lbl_total_cobro)
        
        btn_add_prod = Button(text="+ AGREGAR PRODUCTOS A ESTA MESA", size_hint_y=None, height=40, background_color=(0.95, 0.65, 0.2, 1), bold=True)
        btn_add_prod.bind(on_press=self.entrar_modo_edicion)
        right_side.add_widget(btn_add_prod)
        
        # Payment Logic area
        pay_area = BoxLayout(orientation='horizontal', size_hint_y=0.5, spacing=10)
        
        # Left of pay_area: Numpad + Display
        num_part = BoxLayout(orientation='vertical', size_hint_x=0.6)
        
        display_box = BoxLayout(size_hint_y=0.25, spacing=5)
        display_box.add_widget(Label(text="Monto Recibido $:", font_size='12sp'))
        self.lbl_monto_input = Label(text="0.00", font_size='32sp', bold=True, halign='right')
        display_box.add_widget(self.lbl_monto_input)
        num_part.add_widget(display_box)
        
        # Cambio
        cambio_box = BoxLayout(size_hint_y=0.15)
        cambio_box.add_widget(Label(text="Cambio $:", font_size='12sp'))
        self.lbl_cambio_val = Label(text="$0.00", font_size='24sp', bold=True)
        cambio_box.add_widget(self.lbl_cambio_val)
        num_part.add_widget(cambio_box)
        
        # Actual Numpad
        numpad_grid = GridLayout(cols=3, spacing=5)
        for b in ['7','8','9','4','5','6','1','2','3','0','.','C']:
            btn = Button(text=b, font_size='22sp', background_color=(0.1, 0.15, 0.2, 1))
            btn.bind(on_press=self.on_numpad_press)
            numpad_grid.add_widget(btn)
        num_part.add_widget(numpad_grid)
        pay_area.add_widget(num_part)
        
        # Right of pay_area: Methods
        methods_part = BoxLayout(orientation='vertical', size_hint_x=0.4, spacing=10)
        methods_part.add_widget(Label(text="MÉTODOS", bold=True, size_hint_y=None, height=30))
        
        btn_efectivo = Button(text="EFECTIVO", background_color=SUCCESS_COLOR, bold=True)
        btn_efectivo.bind(on_press=lambda x: self.finalizar_cobro_mesa("EFECTIVO"))
        
        btn_yappy = Button(text="YAPPY", background_color=INFO_COLOR, bold=True)
        btn_yappy.bind(on_press=lambda x: self.finalizar_cobro_mesa("YAPPY"))
        
        btn_tarjeta = Button(text="TARJETA", background_color=(0.3, 0.5, 0.9, 1), bold=True)
        btn_tarjeta.bind(on_press=lambda x: self.finalizar_cobro_mesa("TARJETA"))
        
        methods_part.add_widget(btn_efectivo)
        methods_part.add_widget(btn_yappy)
        methods_part.add_widget(btn_tarjeta)
        pay_area.add_widget(methods_part)
        
        right_side.add_widget(pay_area)
        
        self.cobros_layout.add_widget(right_side)

    def _update_rs_rect(self, inst, val): self.rs_rect.pos = inst.pos; self.rs_rect.size = inst.size

    def on_numpad_press(self, instance):
        current = self.lbl_monto_input.text
        key = instance.text
        if key == 'C':
            self.lbl_monto_input.text = "0.00"
        elif key == '.':
            if '.' not in current:
                self.lbl_monto_input.text += '.'
        else:
            if current == "0.00":
                self.lbl_monto_input.text = key
            else:
                self.lbl_monto_input.text += key
        
        # Update cambio
        self.update_cambio_display()

    def update_cambio_display(self):
        try:
            recibido = float(self.lbl_monto_input.text or 0)
            total = float(self.lbl_total_cobro.text.replace("Total a Cobrar: $", ""))
            cambio = recibido - total
            self.lbl_cambio_val.text = f"${max(0, cambio):.2f}"
            self.lbl_cambio_val.color = SUCCESS_COLOR if cambio >= 0 else (0.8, 0.2, 0.2, 1)
        except: pass

    def on_enter(self):
        self.switch_tab("venta")

    # --- Lógica Venta Directa ---
    def load_menu(self):
        APIClient.get_menu(self.on_menu_success, self.on_error)

    def on_menu_success(self, req, result):
        if result.get('status') == 'success':
            self.productos_data = result.get('data', [])
            categorias = list(set([p.get('categoria', 'Otros') for p in self.productos_data]))
            categorias.insert(0, 'Todas')
            
            self.cat_grid.clear_widgets()
            for c in categorias:
                btn = Button(text=c, size_hint_x=None, width=100, background_color=(0.15, 0.2, 0.25, 1), background_normal='', font_size='12sp')
                btn.bind(on_press=lambda inst, c_name=c: self.render_products(c_name))
                self.cat_grid.add_widget(btn)
            self.render_products("Todas")
            self.render_cart()

    def render_products(self, category):
        self.prod_grid.clear_widgets()
        for p in self.productos_data:
            if category == "Todas" or p.get('categoria') == category:
                card = ProductCard(product_data=p, size_hint_y=None, height=200)
                card.bind(on_add_here=lambda inst, prod=p: self.add_to_cart_caja(prod, False))
                card.bind(on_add_to_go=lambda inst, prod=p: self.add_to_cart_caja(prod, True))
                self.prod_grid.add_widget(card)

    def add_to_cart_caja(self, p, para_llevar):
        nombre = p['nombre']
        if para_llevar:
            nombre += " (LLEVAR)"
        else:
            nombre += " (AQUÍ)"
            
        for item in GlobalState.caja_cart:
            if item['nombre'] == nombre:
                item['cantidad'] += 1
                item['subtotal'] = item['cantidad'] * item['precio_unitario']
                self.render_cart()
                return
        GlobalState.caja_cart.append({
            'nombre': nombre,
            'precio_unitario': p['precio'],
            'cantidad': 1,
            'subtotal': p['precio']
        })
        self.render_cart()

    def render_cart(self):
        self.cart_grid.clear_widgets()
        total = 0
        for idx, item in enumerate(GlobalState.caja_cart):
            total += item['subtotal']
            row_bg = (0.25, 0.3, 0.35, 1) if idx == self.selected_item_idx else (0.18, 0.22, 0.26, 1)
            
            # Contenedor principal de la fila (RelativeLayout para posicionamiento correcto)
            row_rl = RelativeLayout(size_hint_y=None, height=50)
            
            # Capa de contenido (BoxLayout horizontal)
            content = BoxLayout(size_hint=(1, 1), padding=[5, 0], spacing=2)
            with content.canvas.before:
                Color(*row_bg)
                rect = Rectangle(pos=(0, 0), size=(Window.width, 50)) # Posición relativa
            content.bind(size=lambda inst, val, r=rect: setattr(r, 'size', val))
            
            # Columna Producto (0.4)
            lbl_nom = Label(text=item['nombre'], halign='left', valign='middle', size_hint_x=0.4, font_size='11sp')
            lbl_nom.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
            content.add_widget(lbl_nom)
            
            # Columna Cant (0.2)
            lbl_qty = Label(text=f"x{item['cantidad']}", size_hint_x=0.2, font_size='12sp', bold=True, color=INFO_COLOR, halign='center')
            lbl_qty.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
            content.add_widget(lbl_qty)
            
            # Columna Precio (0.2)
            lbl_pr = Label(text=f"${item['precio_unitario']:.2f}", size_hint_x=0.2, font_size='11sp', halign='center')
            lbl_pr.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
            content.add_widget(lbl_pr)
            
            # Columna Subtotal (0.2)
            lbl_sub = Label(text=f"${item['subtotal']:.2f}", size_hint_x=0.2, font_size='11sp', bold=True, halign='center')
            lbl_sub.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
            content.add_widget(lbl_sub)
            
            # Botón invisible para capturar el click en toda la fila
            btn_trigger = Button(background_color=(0,0,0,0), size_hint=(1, 1))
            btn_trigger.bind(on_press=lambda x, i=idx: self.select_cart_item(i))
            
            row_rl.add_widget(content)
            row_rl.add_widget(btn_trigger)
            self.cart_grid.add_widget(row_rl)
        
        total_text = f"Total: ${total:.2f}"
        if self.editing_pedido_id:
            mesa_name = getattr(self, 'editing_mesa_name', 'Mesa')
            total_text += f" [EDITANDO: {mesa_name}]"
            self.lbl_total_caja.color = (1, 0.5, 0, 1) # Naranja para edición
        else:
            self.lbl_total_caja.color = (1, 1, 1, 1) # Blanco normal
            
        self.lbl_total_caja.text = total_text

    def select_cart_item(self, idx):
        self.selected_item_idx = idx
        self.render_cart()
        
        # Abrir diálogo para editar cantidad (paridad con Windows)
        item = GlobalState.caja_cart[idx]
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f"Editar cantidad para:\n{item['nombre']}", halign='center'))
        
        qty_input = TextInput(text=str(item['cantidad']), multiline=False, input_filter='int', font_size='24sp', size_hint_y=None, height=60, halign='center')
        content.add_widget(qty_input)
        
        btn_save = Button(text="GUARDAR", background_color=SUCCESS_COLOR, bold=True, size_hint_y=None, height=50)
        content.add_widget(btn_save)
        
        popup = Popup(title="Cambiar Cantidad", content=content, size_hint=(0.7, 0.4))
        
        def save(x):
            try:
                new_q = int(qty_input.text or 1)
                if new_q < 1: new_q = 1
                item['cantidad'] = new_q
                item['subtotal'] = new_q * item['precio_unitario']
                popup.dismiss()
                self.render_cart()
            except: pass
            
        btn_save.bind(on_press=save)
        popup.open()

    def remove_selected_item(self):
        if 0 <= self.selected_item_idx < len(GlobalState.caja_cart):
            del GlobalState.caja_cart[self.selected_item_idx]
            self.selected_item_idx = -1
            self.render_cart()

    def remove_cart_item(self, idx):
        if 0 <= idx < len(GlobalState.caja_cart):
            del GlobalState.caja_cart[idx]
            self.render_cart()

    def clear_cart_caja(self):
        GlobalState.caja_cart = []
        self.render_cart()

    def confirmar_pedido_caja(self, instance):
        if not GlobalState.caja_cart:
            return
        
        # En Venta Directa ya NO se procesa pago
        # Solo se realiza el pedido o se agregan extras
        canal = 'Llevar' if any('(LLEVAR)' in item['nombre'] for item in GlobalState.caja_cart) else 'Local'
        
        if self.editing_pedido_id:
            self.finalizar_edicion_pedido()
            return

        if canal == 'Llevar':
            content = BoxLayout(orientation='vertical', spacing=10, padding=10)
            content.add_widget(Label(text="Nombre del Cliente (Opcional):"))
            name_input = TextInput(multiline=False, font_size='18sp', size_hint_y=None, height=50)
            content.add_widget(name_input)
            
            btn_confirm = Button(text="REALIZAR PEDIDO", background_color=SUCCESS_COLOR, bold=True, size_hint_y=None, height=60)
            content.add_widget(btn_confirm)
            
            popup = Popup(title="Datos del Cliente", content=content, size_hint=(0.8, 0.4))
            
            def proceed(x):
                cliente = name_input.text.strip()
                popup.dismiss()
                self.finalizar_pedido_caja(cliente)
                
            btn_confirm.bind(on_press=proceed)
            popup.open()
        else:
            self.finalizar_pedido_caja("")

    def finalizar_pedido_caja(self, cliente_nombre):
        total = sum(i['subtotal'] for i in GlobalState.caja_cart)
        data = {
            "items": GlobalState.caja_cart,
            "total": total,
            "metodo_pago": None,
            "canal": "LLEVAR" if any('(LLEVAR)' in item['nombre'] for item in GlobalState.caja_cart) else "CAJA",
            "mesa": "CAJA",
            "cliente_nombre": cliente_nombre,
            "sesion_id": GlobalState.sesion_id,
            "usuario_id": GlobalState.user['id'] if GlobalState.user else 1,
            "pagado": 0
        }
        APIClient.crear_pedido_caja(data, self.on_pedido_caja_success, self.on_error)

    def entrar_modo_edicion(self, instance):
        if not self.selected_pedido:
            Popup(title="Aviso", content=Label(text="Seleccione un pedido de la lista primero."), size_hint=(0.7, 0.3)).open()
            return
        
        self.editing_pedido_id = self.selected_pedido['id']
        self.editing_mesa_name = self.selected_pedido['mesa']
        
        # Cambiar a pestaña de Venta
        self.switch_tab("venta")
        self.render_cart() # Actualizar para mostrar estado de edición

    def finalizar_edicion_pedido(self):
        total_extras = sum(i['subtotal'] for i in GlobalState.caja_cart)
        # Endpoint para agregar extras
        APIClient.update_pedido_extras(
            self.editing_pedido_id, 
            GlobalState.caja_cart, 
            total_extras, 
            self.on_edicion_success, 
            self.on_error
        )

    def on_edicion_success(self, req, result):
        self.editing_pedido_id = None
        self.editing_mesa_name = None
        GlobalState.caja_cart = []
        self.render_cart()
        self.load_pedidos_pendientes() # Refrescar lista para ver cambios
        self.switch_tab("cobros")
        Popup(title="Éxito", content=Label(text="Productos extras añadidos correctamente."), size_hint=(0.7, 0.3)).open()

    def on_pedido_caja_success(self, req, result):
        # Imprimir ticket de la venta directa
        total = sum(i['subtotal'] for i in GlobalState.caja_cart)
        pedido_print = {
            "id": result.get('numero', 'N/A'),
            "mesa": "CAJA",
            "items": list(GlobalState.caja_cart),
            "total": total
        }
        SunmiPrinter.print_receipt(pedido_print)
        
        GlobalState.caja_cart = []
        self.render_cart()
        Popup(title="Venta Exitosa", content=Label(text="Venta registrada correctamente."), size_hint=(0.8, 0.3)).open()

    # --- Lógica Cobrar Mesas ---
    def load_pedidos_pendientes(self):
        APIClient.get_pedidos_pendientes(self.on_pendientes_success, self.on_error)

    def on_pendientes_success(self, req, result):
        self.cobros_grid.clear_widgets()
        if result.get('status') == 'success':
            self.pedidos_pendientes = result.get('data', [])
            for p in self.pedidos_pendientes:
                row = BoxLayout(size_hint_y=None, height=45, spacing=2)
                with row.canvas.before:
                    Color(0.25, 0.3, 0.35, 1)
                    Rectangle(pos=row.pos, size=row.size)
                
                btn_sel = Button(background_color=(0,0,0,0), size_hint=(1,1))
                btn_sel.bind(on_press=lambda x, p_data=p: self.select_pedido_cobro(p_data))
                
                content = BoxLayout(size_hint=(1,1))
                content.add_widget(Label(text=str(p['id']), size_hint_x=0.2, font_size='11sp'))
                content.add_widget(Label(text=p['numero'], size_hint_x=0.4, font_size='11sp'))
                content.add_widget(Label(text=p['mesa'], size_hint_x=0.2, font_size='11sp'))
                content.add_widget(Label(text=f"${p['total']:.2f}", size_hint_x=0.2, font_size='11sp', bold=True, color=SUCCESS_COLOR))
                
                fl = FloatLayout(size_hint_y=None, height=45)
                fl.add_widget(content)
                fl.add_widget(btn_sel)
                self.cobros_grid.add_widget(fl)

    def select_pedido_cobro(self, p_data):
        self.selected_pedido = p_data
        self.details_grid.clear_widgets()
        for item in p_data.get('items', []):
            row = BoxLayout(size_hint_y=None, height=30)
            row.add_widget(Label(text=f"{item.get('cantidad',1)}x {item.get('nombre','')}", halign='left', size_hint_x=0.7, font_size='11sp', text_size=(Window.width*0.4, None)))
            row.add_widget(Label(text=f"${item.get('precio',0)*item.get('cantidad',1):.2f}", size_hint_x=0.3, font_size='11sp'))
            self.details_grid.add_widget(row)
        
        self.lbl_total_cobro.text = f"Total a Cobrar: ${p_data['total']:.2f}"
        self.lbl_monto_input.text = "0.00"
        self.update_cambio_display()

    def finalizar_cobro_mesa(self, metodo):
        if not self.selected_pedido:
            Popup(title="Error", content=Label(text="Seleccione un pedido primero."), size_hint=(0.7, 0.3)).open()
            return
        
        try:
            recibido = float(self.lbl_monto_input.text or 0)
            total = self.selected_pedido['total']
            if metodo == "EFECTIVO" and recibido < total:
                Popup(title="Error", content=Label(text="Monto recibido insuficiente."), size_hint=(0.7, 0.3)).open()
                return
        except: pass

        data = {"metodo_pago": metodo, "sesion_id": GlobalState.sesion_id}
        pedido_id = self.selected_pedido['id']
        pedido_data_copy = dict(self.selected_pedido)
        
        def on_success(req, res):
            SunmiPrinter.print_receipt(pedido_data_copy)
            self.selected_pedido = None
            self.details_grid.clear_widgets()
            self.lbl_total_cobro.text = "Total a Cobrar: $0.00"
            self.lbl_monto_input.text = "0.00"
            self.lbl_cambio_val.text = "$0.00"
            self.load_pedidos_pendientes()
            Popup(title="Exito", content=Label(text="Cobro registrado correctamente."), size_hint=(0.7, 0.3)).open()
            
        APIClient.cobrar_pedido(pedido_id, data, on_success, self.on_error)
    # --- Utilitarios ---
    def show_payment_popup(self, callback, total_amount=0):
        if not GlobalState.sesion_id:
            Popup(title="Error", content=Label(text="No hay caja abierta.\nAbra caja antes de cobrar."), size_hint=(0.8, 0.3)).open()
            return
            
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f"TOTAL A COBRAR: ${total_amount:.2f}", bold=True, font_size='20sp', color=SUCCESS_COLOR))
        
        # Campo para monto recibido y cambio
        monto_recibido_input = TextInput(text="", hint_text="Monto Recibido $", multiline=False, input_filter='float', font_size='24sp', size_hint_y=None, height=60, halign='center')
        content.add_widget(monto_recibido_input)
        
        lbl_cambio = Label(text="Cambio: $0.00", font_size='18sp', bold=True)
        content.add_widget(lbl_cambio)
        
        def update_cambio(inst, val):
            try:
                recibido = float(val or 0)
                cambio = recibido - total_amount
                lbl_cambio.text = f"Cambio: ${max(0, cambio):.2f}"
                lbl_cambio.color = SUCCESS_COLOR if cambio >= 0 else (0.8, 0.2, 0.2, 1)
            except: pass
        monto_recibido_input.bind(text=update_cambio)

        content.add_widget(Label(text="Seleccione Método de Pago", bold=True))
        
        methods_layout = GridLayout(cols=3, spacing=10, size_hint_y=None, height=80)
        methods = [("EFECTIVO", SUCCESS_COLOR), ("YAPPY", INFO_COLOR), ("TARJETA", (0.5, 0.2, 0.8, 1))]
        
        popup = Popup(title="Procesar Pago", content=content, size_hint=(0.9, 0.7))
        
        for name, color in methods:
            btn = Button(text=name, background_color=color, bold=True)
            btn.bind(on_press=lambda x, m=name: [callback(m), popup.dismiss()])
            methods_layout.add_widget(btn)
        
        content.add_widget(methods_layout)
        
        btn_cancel = Button(text="CANCELAR", size_hint_y=None, height=50, background_color=(0.5, 0.5, 0.5, 1))
        btn_cancel.bind(on_press=popup.dismiss)
        content.add_widget(btn_cancel)
        
        popup.open()



    # Sobrescribir on_pendientes_success para que use un formato de tabla
    def on_pendientes_success(self, req, result):
        self.cobros_grid.clear_widgets()
        if result.get('status') == 'success':
            self.pedidos_pendientes = result.get('data', [])
            
            # Header de la "Tabla"
            h_row = BoxLayout(size_hint_y=None, height=40, padding=[10, 0])
            with h_row.canvas.before:
                Color(0.2, 0.25, 0.3, 1)
                Rectangle(pos=h_row.pos, size=h_row.size)
            h_row.add_widget(Label(text="PEDIDO", size_hint_x=0.2, bold=True))
            h_row.add_widget(Label(text="MESA", size_hint_x=0.2, bold=True))
            h_row.add_widget(Label(text="TOTAL", size_hint_x=0.2, bold=True))
            h_row.add_widget(Label(text="ACCIONES", size_hint_x=0.4, bold=True))
            self.cobros_grid.add_widget(h_row)

            for p in self.pedidos_pendientes:
                # Omitir filas que parezcan vacías o corruptas
                if not p.get('id') and not p.get('numero'):
                    continue
                    
                row = BoxLayout(size_hint_y=None, height=60, padding=[10, 5], spacing=5)
                with row.canvas.before:
                    Color(0.25, 0.3, 0.35, 1)
                    rect = Rectangle(pos=row.pos, size=row.size)
                def _ur(inst, val, r=rect): r.pos = inst.pos; r.size = inst.size
                row.bind(pos=_ur, size=_ur)
                
                # Usar RelativeLayout para asegurar que los hijos se posicionen bien dentro de la fila
                left_container = RelativeLayout(size_hint_x=0.6)
                
                lbls_box = BoxLayout(size_hint=(1, 1))
                lbls_box.add_widget(Label(text=str(p.get('numero', '')), size_hint_x=0.33, font_size='11sp'))
                lbls_box.add_widget(Label(text=str(p.get('mesa', '')), size_hint_x=0.33))
                lbls_box.add_widget(Label(text=f"${float(p.get('total', 0)):.2f}", size_hint_x=0.34, bold=True, color=SUCCESS_COLOR))
                
                btn_sel = Button(background_color=(0,0,0,0), background_normal='', size_hint=(1, 1))
                btn_sel.bind(on_press=lambda x, p_data=p: self.select_pedido_cobro(p_data))
                
                left_container.add_widget(lbls_box)
                left_container.add_widget(btn_sel)
                
                row.add_widget(left_container)
                
                btn_actions = BoxLayout(size_hint_x=0.4, spacing=5)
                btn_pre = Button(text="PRE", background_color=INFO_COLOR, size_hint_x=0.4)
                btn_pre.bind(on_press=lambda x, p_data=p: SunmiPrinter.print_receipt(p_data))
                
                btn_cobrar = Button(text="COBRAR", background_color=SUCCESS_COLOR, size_hint_x=0.6)
                btn_cobrar.bind(on_press=lambda x, p_data=p: self.show_payment_popup(lambda m: self.cobrar_pedido_mesa(p_data, m), p_data['total']))
                
                btn_actions.add_widget(btn_pre)
                btn_actions.add_widget(btn_cobrar)
                row.add_widget(btn_actions)
                
                self.cobros_grid.add_widget(row)

    def cobrar_pedido_mesa(self, pedido_data, metodo):
        data = {"metodo_pago": metodo, "sesion_id": GlobalState.sesion_id}
        pedido_id = pedido_data['id']
        def on_success(req, res):
            SunmiPrinter.print_receipt(pedido_data)
            # Abrir el cajón remotamente
            APIClient.abrir_cajon()
            self.load_pedidos_pendientes()
            
        APIClient.cobrar_pedido(pedido_id, data, on_success, self.on_error)

    # --- Lógica Sesión de Caja ---
    def show_abrir_caja(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text="Monto Inicial en Caja ($):"))
        monto_input = TextInput(text="0.00", multiline=False, input_filter='float', font_size='20sp', size_hint_y=None, height=50)
        content.add_widget(monto_input)
        btn = Button(text="ABRIR SESION", background_color=SUCCESS_COLOR, bold=True, size_hint_y=None, height=60)
        content.add_widget(btn)
        popup = Popup(title="Apertura de Caja", content=content, size_hint=(0.8, 0.4))
        
        def abrir(x):
            data = {"usuario_id": GlobalState.user['id'] if GlobalState.user else 1, "monto_inicial": float(monto_input.text or 0)}
            APIClient.abrir_caja(data, lambda r, res: self._on_caja_abierta(popup, res), self.on_error)
        btn.bind(on_press=abrir)
        popup.open()

    def _on_caja_abierta(self, popup, result):
        popup.dismiss()
        GlobalState.sesion_id = result.get('sesion_id')
        Popup(title="Exito", content=Label(text="Caja abierta correctamente"), size_hint=(0.7, 0.3)).open()

    def confirmar_cierre(self, instance):
        content = BoxLayout(orientation='vertical', spacing=15, padding=10)
        content.add_widget(Label(text="¿Está seguro de cerrar la caja?", bold=True))
        content.add_widget(Label(text="Se generará el reporte de ventas final.", font_size='12sp'))
        
        btn_row = BoxLayout(spacing=10, size_hint_y=None, height=50)
        btn_si = Button(text="SI, CERRAR", background_color=(0.8, 0.2, 0.2, 1))
        btn_no = Button(text="CANCELAR")
        btn_row.add_widget(btn_si)
        btn_row.add_widget(btn_no)
        content.add_widget(btn_row)
        
        popup = Popup(title="Confirmar Cierre", content=content, size_hint=(0.8, 0.4))
        btn_no.bind(on_press=popup.dismiss)
        btn_si.bind(on_press=lambda x: self.realizar_cierre(popup))
        popup.open()

    def realizar_cierre(self, popup):
        popup.dismiss()
        data = {"sesion_id": GlobalState.sesion_id}
        APIClient.cerrar_caja(data, self.on_cierre_success, self.on_error)

    def on_cierre_success(self, req, result):
        GlobalState.sesion_id = None
        r = result.get('reporte', {})
        resumen = f"Ventas Totales: ${r.get('total_ventas',0):.2f}\n"
        resumen += f"Efectivo: ${r.get('efectivo',0):.2f}\n"
        resumen += f"Yappy: ${r.get('yappy',0):.2f}\n"
        resumen += f"Tarjeta: ${r.get('tarjeta',0):.2f}\n"
        resumen += f"Total en Caja: ${r.get('total_en_caja',0):.2f}"
        
        # Generar formato de ticket para imprimir
        SunmiPrinter.print_closing_report(r)
        
        Popup(title="Caja Cerrada", content=Label(text=resumen, halign='center'), size_hint=(0.9, 0.6)).open()

    def on_error(self, req, error):
        msg = str(error)
        if isinstance(error, dict) and 'message' in error: msg = error['message']
        Popup(title="Error", content=Label(text=msg), size_hint=(0.8, 0.3)).open()

    def go_back(self, instance):
        self.manager.current = 'dashboard'


class AdsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        self.media_container = FloatLayout(size_hint=(1, 1))
        self.layout.add_widget(self.media_container)

        self.btn_exit = Button(text="X", size_hint=(None, None), size=(60, 60), 
                               pos_hint={'x': 0, 'top': 1}, background_color=(0,0,0,0.3), font_size='24sp')
        self.btn_exit.bind(on_press=self.go_back)
        self.layout.add_widget(self.btn_exit)

        self.add_widget(self.layout)
        self.ads_list = []
        self.current_ad_index = 0
        self.carousel_event = None
        self.is_active = False # Flag para evitar procesos en segundo plano al salir

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def on_enter(self):
        self.is_active = True
        rol = ""
        if GlobalState.user:
            rol = GlobalState.user.get('rol', '').upper()

        if 'PUBLICIDAD' in rol or 'TV' in rol:
            self.btn_exit.text = "SALIR"
            self.btn_exit.size = (120, 60)
            self.btn_exit.opacity = 0.5 # Sutil
        else:
            self.btn_exit.text = "X"
            self.btn_exit.size = (60, 60)
            self.btn_exit.opacity = 1
            
        self.btn_exit.disabled = False
        
        # Soporte para control remoto (Botón Atrás / Esc)
        Window.bind(on_keyboard=self._on_keyboard)
        
        self.fetch_ads()

    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        # 27 es la tecla ESC y suele ser el botón 'Atrás' en Android/TV
        if key == 27:
            self.go_back(None)
            return True
        return False

    def fetch_ads(self):
        APIClient.get_ads(self.on_ads_success, self.on_ads_error)

    def on_ads_success(self, req, result):
        if not self.is_active: return # Evitar si ya salió
        if result.get('status') == 'success':
            self.ads_list = result.get('images', [])
            if self.ads_list:
                self.current_ad_index = 0
                if self.carousel_event:
                    self.carousel_event.cancel()
                    self.carousel_event = None
                self.show_current_ad()
            else:
                self.media_container.clear_widgets()

    def on_ads_error(self, req, error):
        pass

    def show_current_ad(self):
        if not self.ads_list or not self.is_active:
            return

        ad_name = self.ads_list[self.current_ad_index]
        import urllib.parse
        # Asegurar que la URL sea correcta y compatible
        media_url = f"{SERVER_URL}/api/publicidad/{urllib.parse.quote(ad_name)}"
        self.media_container.clear_widgets()

        print(f"Cargando publicidad: {media_url}")

        if ad_name.lower().endswith(('.mp4', '.avi', '.mov')):
            # Lógica para videos
            if self.carousel_event:
                self.carousel_event.cancel()
                self.carousel_event = None
                
            from kivy.utils import platform
            import os
            
            # Ruta local esperada dentro del paquete de la aplicación
            local_path = os.path.join("Imagenes", "publicidad", ad_name)
            
            if platform == 'android':
                if os.path.exists(local_path):
                    try:
                        # Si el video ya está empaquetado en el APK, para evitar problemas de
                        # permisos de mediaserver, lo copiamos temporalmente a la caché externa
                        from jnius import autoclass
                        PythonActivity = autoclass('org.kivy.android.PythonActivity')
                        activity = PythonActivity.mActivity
                        ext_cache_dir = activity.getExternalCacheDir().getAbsolutePath()
                        
                        import shutil
                        dest_path = os.path.join(ext_cache_dir, ad_name)
                        shutil.copy(local_path, dest_path)
                        
                        # Reproducimos localmente desde la caché externa y activamos borrado al terminar
                        Clock.schedule_once(lambda dt: self._play_local_video(dest_path, is_url=False, delete_on_eos=True), 0)
                    except Exception as copy_err:
                        print(f"Error copiando video local a cache externa: {copy_err}")
                        # Fallback a transmisión remota si la copia falla
                        Clock.schedule_once(lambda dt: self._play_local_video(media_url, is_url=True), 0)
                else:
                    # Si no está localmente, lo transmitimos remotamente
                    Clock.schedule_once(lambda dt: self._play_local_video(media_url, is_url=True), 0)
            else:
                # Versión de escritorio (Windows/Linux)
                if os.path.exists(local_path):
                    Clock.schedule_once(lambda dt: self._play_local_video(local_path, is_url=False, delete_on_eos=False), 0)
                else:
                    import tempfile, threading, urllib.request, uuid
                    ext = os.path.splitext(ad_name)[1]
                    # Usar nombre único para evitar errores de acceso si el video anterior sigue en uso
                    tmp_path = os.path.join(tempfile.gettempdir(), f"pikta_ad_{uuid.uuid4().hex}{ext}")

                    def download_thread():
                        try:
                            # Descarga forzada para reproducción local (más fluido en TV)
                            urllib.request.urlretrieve(media_url, tmp_path)
                            if not self.is_active: return
                            Clock.schedule_once(lambda dt: self._play_local_video(tmp_path, is_url=False, delete_on_eos=True), 0)
                        except Exception as e:
                            print(f"Error descargando video: {e}")
                            if self.is_active:
                                Clock.schedule_once(lambda dt: self.next_ad(None), 2)

                    threading.Thread(target=download_thread, daemon=True).start()
        else:
            # Lógica para imágenes (con recarga si falla)
            img = AsyncImage(source=media_url, fit_mode='fill', nocache=True)
            def on_img_err(inst, error):
                inst.source = 'Imagenes/pikata.png'
            img.bind(on_error=on_img_err)
            self.media_container.add_widget(img)
            
            if not self.carousel_event:
                self.carousel_event = Clock.schedule_interval(self.next_ad, 10)

    def _play_local_video(self, source_path, is_url=False, delete_on_eos=False):
        if not self.is_active: return
        if delete_on_eos and not is_url:
            self.current_video_tmp_path = source_path
        else:
            self.current_video_tmp_path = None
            
        self.native_video_loading_ticks = 0
        
        from kivy.utils import platform
        if platform == 'android':
            try:
                from jnius import autoclass
                from android.runnable import run_on_ui_thread
                
                # Preparamos las clases de Java
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                VideoView = autoclass('android.widget.VideoView')
                Uri = autoclass('android.net.Uri')
                FrameLayout = autoclass('android.widget.FrameLayout')
                LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
                Color = autoclass('android.graphics.Color')
                
                self.media_container.clear_widgets()
                
                @run_on_ui_thread
                def _start_native():
                    try:
                        activity = PythonActivity.mActivity
                        
                        # Creamos el contenedor nativo
                        layout = FrameLayout(activity)
                        layout.setBackgroundColor(Color.BLACK)
                        self.native_layout = layout
                        
                        # Creamos el VideoView nativo
                        video_view = VideoView(activity)
                        video_view.setFocusable(False)
                        video_view.setFocusableInTouchMode(False)
                        self.native_video_view = video_view
                        
                        # Añadimos el VideoView al FrameLayout centrado
                        vv_params = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
                        layout.addView(video_view, vv_params)
                        
                        # Cargamos la URI del video (Remota en Android evita problemas de permisos de lectura de mediaserver)
                        video_view.setVideoURI(Uri.parse(source_path))
                        
                        # Añadimos todo a la ventana de Android
                        activity.addContentView(layout, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
                        
                        # Iniciamos la reproducción
                        video_view.start()
                        
                        # Programamos el chequeo de finalización en Kivy
                        Clock.schedule_once(lambda dt: setattr(self, 'native_video_check', Clock.schedule_interval(self._check_native_video_status, 0.5)), 0.1)
                        
                    except Exception as ex:
                        print(f"Error en hilo UI nativo: {ex}")
                        if self.is_active:
                            Clock.schedule_once(lambda dt: self.next_ad(None), 1)
                            
                _start_native()
                
            except Exception as e:
                print(f"Error iniciando reproducción nativa Android: {e}")
                if self.is_active:
                    self.next_ad(None)
        else:
            # Versión no Android (Windows/Linux) - Usamos la clase Video estándar de Kivy
            try:
                from kivy.uix.video import Video
                self.media_container.clear_widgets()
                video = Video(source=source_path, state='play', options={'eos': 'stop'})
                video.allow_stretch = True
                
                def on_eos_handler(inst, val):
                    if val:
                        # 1. Saltar al siguiente anuncio
                        self.on_video_eos(inst, val)
                        # 2. Limpieza del video temporal si corresponde
                        if delete_on_eos:
                            try:
                                def _del(dt):
                                    if os.path.exists(source_path):
                                        try: os.remove(source_path)
                                        except: pass
                                Clock.schedule_once(_del, 2)
                            except: pass
                            
                video.bind(eos=on_eos_handler)
                self.media_container.add_widget(video)
            except Exception as e:
                print(f"Error reproduciendo video Kivy: {e}")
                if self.is_active:
                    self.next_ad(None)

    def _check_native_video_status(self, dt):
        if not self.is_active or not hasattr(self, 'native_layout') or not self.native_layout:
            return False
            
        try:
            # Comprobamos si el video nativo ha terminado
            pos = self.native_video_view.getCurrentPosition()
            dur = self.native_video_view.getDuration()
            is_playing = self.native_video_view.isPlaying()
            
            # Control de timeout si el video no carga o no reproduce
            if dur <= 0 and not is_playing:
                if not hasattr(self, 'native_video_loading_ticks'):
                    self.native_video_loading_ticks = 0
                self.native_video_loading_ticks += 1
                if self.native_video_loading_ticks > 20:  # 10 segundos (20 ticks de 0.5s)
                    print("Timeout cargando video en Android TV - Pasando al siguiente anuncio")
                    self._stop_native_video()
                    self.next_ad(None)
                    return False
            else:
                self.native_video_loading_ticks = 0
            
            # Si la duración es válida y llegamos al final (con 300ms de tolerancia)
            if dur > 0 and pos >= (dur - 300):
                self._stop_native_video()
                self.next_ad(None)
                return False
                
            # Si no está reproduciendo pero la posición está cerca del final
            if not is_playing and pos > 0 and dur > 0 and pos >= (dur - 1000):
                self._stop_native_video()
                self.next_ad(None)
                return False
                
        except Exception as e:
            print(f"Error comprobando video nativo: {e}")
            self._stop_native_video()
            self.next_ad(None)
            return False
            
        return True

    def _stop_native_video(self):
        if hasattr(self, 'native_video_check') and self.native_video_check:
            self.native_video_check.cancel()
            self.native_video_check = None
            
        from kivy.utils import platform
        if platform == 'android':
            try:
                from android.runnable import run_on_ui_thread
                
                @run_on_ui_thread
                def _stop():
                    try:
                        if hasattr(self, 'native_video_view') and self.native_video_view:
                            self.native_video_view.stopPlayback()
                            self.native_video_view = None
                    except Exception as e:
                        print(f"Error deteniendo playback nativo: {e}")
                        
                    try:
                        if hasattr(self, 'native_layout') and self.native_layout:
                            parent = self.native_layout.getParent()
                            if parent:
                                parent.removeView(self.native_layout)
                            self.native_layout = None
                    except Exception as e:
                        print(f"Error removiendo layout nativo: {e}")
                        
                _stop()
            except Exception as e:
                print(f"Error al programar detención en hilo UI: {e}")
            
        if hasattr(self, 'current_video_tmp_path') and self.current_video_tmp_path:
            try:
                if os.path.exists(self.current_video_tmp_path):
                    os.remove(self.current_video_tmp_path)
            except:
                pass
            self.current_video_tmp_path = None

    def on_video_eos(self, instance, value):
        if value:
            self.next_ad(None)

    def next_ad(self, dt=None):
        if self.ads_list and self.is_active:
            self.current_ad_index = (self.current_ad_index + 1) % len(self.ads_list)
            self.show_current_ad()

    def on_leave(self):
        Window.unbind(on_keyboard=self._on_keyboard)
        self.stop_ads()

    def go_back(self, instance):
        self.stop_ads() # Asegurar detención
        rol = ""
        if GlobalState.user:
            rol = GlobalState.user.get('rol', '').upper()
        if 'PUBLICIDAD' in rol or 'TV' in rol:
            GlobalState.user = None
            self.manager.current = 'login'
        else:
            self.manager.current = 'dashboard'

    def stop_ads(self):
        """Detiene todos los procesos de publicidad de forma externa y mata el audio."""
        self.is_active = False
        if self.carousel_event:
            self.carousel_event.cancel()
            self.carousel_event = None
            
        # Detener video nativo de Android
        self._stop_native_video()
            
        # Forzar detención de audio/video antes de limpiar
        for child in list(self.media_container.children):
            if hasattr(child, 'state'):
                child.state = 'stop'
            if hasattr(child, 'unload'):
                try: child.unload()
                except: pass
                
        self.media_container.clear_widgets()


class AdminScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')

        self.top_bar = BoxLayout(size_hint_y=None, height=60, padding=10, spacing=10)
        self.title_label = Label(text="Panel Administrativo", font_size='20sp', bold=True, halign='left')
        self.title_label.bind(size=self.title_label.setter('text_size'))
        
        self.btn_back_main = Button(text="Salir", size_hint_x=None, width=80, background_color=(0.8, 0.2, 0.2, 1))
        self.btn_back_main.bind(on_press=self.go_back)
        
        self.btn_back_menu = Button(text="Volver", size_hint_x=None, width=80, background_color=(0.5, 0.5, 0.5, 1))
        self.btn_back_menu.bind(on_press=self.load_admin_menu)
        
        self.top_bar.add_widget(self.title_label)
        self.top_bar.add_widget(self.btn_back_main)
        self.layout.add_widget(self.top_bar)

        self.scroll = ScrollView(size_hint_y=1)
        self.grid = GridLayout(cols=1, spacing=10, padding=15, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        self.layout.add_widget(self.scroll)

        self.add_widget(self.layout)

    def on_enter(self):
        self.load_admin_menu()

    def load_admin_menu(self, *args):
        self.grid.clear_widgets()
        self.grid.cols = 2
        
        if self.btn_back_menu in self.top_bar.children:
            self.top_bar.remove_widget(self.btn_back_menu)
        if self.btn_back_main not in self.top_bar.children:
            self.top_bar.add_widget(self.btn_back_main)
            
        self.title_label.text = "Panel Administrativo"
        
        cards = []
        rol = ""
        if GlobalState.user:
            rol = GlobalState.user.get('rol', '').upper()
            
        if 'ADMIN' in rol or 'SUPERVISOR' in rol:
            cards.append(("📦\nInventario", ACCENT_COLOR, self.load_inventory))
            cards.append(("🛒\nMenú", SUCCESS_COLOR, self.load_menu_editor))
            cards.append(("📄\nHistorial Ventas", INFO_COLOR, self.load_ventas_historial))
            cards.append(("📊\nCierres de Caja", (0.8, 0.5, 0.2, 1), self.load_cierres))
            cards.append(("📺\nPublicidad TV", (0.1, 0.6, 0.6, 1), self.load_ads_manager))
            
        if 'ADMIN' in rol:
            cards.insert(1, ("👥\nUsuarios", INFO_COLOR, self.load_users))
            cards.insert(2, ("🛡️\nSeguridad", (0.2, 0.2, 0.2, 1), self.load_seguridad))
        
        for text, color, cmd in cards:
            btn = Button(text=text, background_color=color, background_normal='', font_size='18sp', bold=True, halign='center', size_hint_y=None, height=150)
            btn.bind(on_press=cmd)
            self.grid.add_widget(btn)

    def _setup_sub_menu(self, title):
        self.title_label.text = title
        if self.btn_back_main in self.top_bar.children:
            self.top_bar.remove_widget(self.btn_back_main)
        if self.btn_back_menu not in self.top_bar.children:
            self.top_bar.add_widget(self.btn_back_menu)

    # --- USUARIOS ---
    def load_users(self, *args):
        self.grid.clear_widgets()
        self.grid.cols = 1
        self._setup_sub_menu("Gestión de Personal")
        
        btn_new = Button(text="+ Nuevo Usuario", size_hint_y=None, height=50, background_color=SUCCESS_COLOR)
        btn_new.bind(on_press=self.show_user_form)
        self.grid.add_widget(btn_new)
        
        APIClient.get_usuarios(self.on_users_success, self.on_error)

    def on_users_success(self, req, result):
        if result.get('status') == 'success':
            for u in result.get('data', []):
                card = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, padding=10, spacing=10)
                with card.canvas.before:
                    Color(*PANEL_COLOR)
                    rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[5])
                def _ur(inst, val, r=rect):
                    r.pos = inst.pos
                    r.size = inst.size
                card.bind(pos=_ur, size=_ur)
                
                card.add_widget(Label(text=f"{u.get('username')}", bold=True, size_hint_x=0.3))
                card.add_widget(Label(text=f"{u.get('nombre_completo')}", size_hint_x=0.4))
                
                btn_edit = Button(text="Editar", size_hint_x=0.3, background_color=INFO_COLOR)
                btn_edit.bind(on_press=lambda x, user=u: self.show_user_form(None, user))
                card.add_widget(btn_edit)
                
                self.grid.add_widget(card)

    def show_user_form(self, instance, user_data=None):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        username_input = TextInput(text=user_data.get('username', '') if user_data else '', multiline=False, hint_text='Usuario')
        if user_data: username_input.readonly = True # No edit username
        
        nombre_input = TextInput(text=user_data.get('nombre_completo', '') if user_data else '', multiline=False, hint_text='Nombre Completo')
        password_input = TextInput(password=True, multiline=False, hint_text='Contraseña (Dejar vacío si no se cambia)')
        rol_spinner = Spinner(text=user_data.get('rol', 'Mesero') if user_data else 'Mesero', values=('Mesero', 'Cajera', 'Cocina', 'Publicidad', 'Administrador', 'Supervisor'))
        
        content.add_widget(Label(text="Usuario:"))
        content.add_widget(username_input)
        content.add_widget(Label(text="Nombre:"))
        content.add_widget(nombre_input)
        content.add_widget(Label(text="Clave:"))
        content.add_widget(password_input)
        content.add_widget(Label(text="Rol:"))
        content.add_widget(rol_spinner)
        
        btn_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        btn_save = Button(text="Guardar", background_color=SUCCESS_COLOR)
        btn_layout.add_widget(btn_save)
        
        if user_data:
            btn_del = Button(text="Eliminar", background_color=(0.8, 0.2, 0.2, 1))
            btn_layout.add_widget(btn_del)
            
        content.add_widget(btn_layout)
        popup = Popup(title="Usuario", content=content, size_hint=(0.9, 0.8))
        
        def save(btn):
            data = {'rol': rol_spinner.text, 'nombre_completo': nombre_input.text}
            if not user_data:
                data['username'] = username_input.text
                data['password'] = password_input.text
                APIClient.create_usuario(data, lambda r, res: self._on_saved(popup), self.on_error)
            else:
                if password_input.text: data['password'] = password_input.text
                APIClient.update_usuario(user_data['id'], data, lambda r, res: self._on_saved(popup), self.on_error)
                
        def delete(btn):
            APIClient.delete_usuario(user_data['id'], lambda r, res: self._on_saved(popup), self.on_error)
            
        btn_save.bind(on_press=save)
        if user_data: btn_del.bind(on_press=delete)
        popup.open()

    def _on_saved(self, popup):
        popup.dismiss()
        self.load_admin_menu()

    # --- INVENTARIO ---
    def load_inventory(self, *args):
        self.grid.clear_widgets()
        self.grid.cols = 1
        self._setup_sub_menu("Control de Inventario")
        APIClient.get_inventario(self.on_inv_success, self.on_error)

    def on_inv_success(self, req, result):
        if result.get('status') == 'success':
            for i in result.get('data', []):
                card = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, padding=10, spacing=10)
                with card.canvas.before:
                    Color(*PANEL_COLOR)
                    rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[5])
                def _ur(inst, val, r=rect):
                    r.pos = inst.pos
                    r.size = inst.size
                card.bind(pos=_ur, size=_ur)
                
                card.add_widget(Label(text=f"{i.get('ingrediente')}", bold=True, size_hint_x=0.4))
                qty = float(i.get('cantidad') or 0)
                s_min = float(i.get('stock_minimo') or 0)
                card.add_widget(Label(text=f"{qty} {i.get('unidad')}", size_hint_x=0.3, color=SUCCESS_COLOR if qty > s_min else (0.8, 0.2, 0.2, 1)))
                
                btn_edit = Button(text="Ajustar", size_hint_x=0.3, background_color=INFO_COLOR)
                btn_edit.bind(on_press=lambda x, item=i: self.show_inv_form(item))
                card.add_widget(btn_edit)
                
                self.grid.add_widget(card)

    def show_inv_form(self, item_data):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        qty_input = TextInput(text=str(item_data.get('cantidad', 0)), multiline=False, input_filter='float')
        min_input = TextInput(text=str(item_data.get('stock_minimo', 0)), multiline=False, input_filter='float')
        
        content.add_widget(Label(text=f"Ajustar: {item_data.get('ingrediente')}"))
        content.add_widget(Label(text="Cantidad Actual:"))
        content.add_widget(qty_input)
        content.add_widget(Label(text="Stock Mínimo:"))
        content.add_widget(min_input)
        
        btn_save = Button(text="Guardar", size_hint_y=None, height=50, background_color=SUCCESS_COLOR)
        btn_delete = Button(text="ELIMINAR ITEM", size_hint_y=None, height=40, background_color=(0.8, 0.2, 0.2, 1))
        content.add_widget(btn_save)
        content.add_widget(btn_delete)
        
        popup = Popup(title="Inventario", content=content, size_hint=(0.8, 0.7))
        
        def save(btn):
            data = {'cantidad': float(qty_input.text or 0), 'stock_minimo': float(min_input.text or 0)}
            APIClient.update_inventario_item(item_data['id'], data, lambda r, res: self._on_saved(popup), self.on_error)
            
        def delete_item(btn):
            def confirm(b):
                APIClient.delete_inventario_item(item_data['id'], lambda r, res: self._on_saved(popup), self.on_error)
                conf_popup.dismiss()
            
            conf_content = BoxLayout(orientation='vertical', padding=10, spacing=10)
            conf_content.add_widget(Label(text=f"¿Seguro que desea eliminar\n'{item_data['ingrediente']}'?"))
            btn_conf = Button(text="SÍ, ELIMINAR", background_color=(1, 0, 0, 1))
            btn_conf.bind(on_press=confirm)
            conf_content.add_widget(btn_conf)
            conf_popup = Popup(title="Confirmar", content=conf_content, size_hint=(0.7, 0.4))
            conf_popup.open()

        btn_save.bind(on_press=save)
        btn_delete.bind(on_press=delete_item)
        popup.open()

    # --- MENU (PRODUCTOS) ---
    def load_menu_editor(self, *args):
        self._setup_sub_menu("Gestión de Menú y Productos")
        self.grid.clear_widgets()
        self.grid.cols = 1
        self.grid.spacing = 5

        # --- CABECERA DE TABLA ---
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, padding=[5,0])
        with header.canvas.before:
            Color(0.35, 0.7, 0.85, 1) # Color azul claro como en imagen
            self.header_rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda inst, v: setattr(self.header_rect, 'pos', v),
                    size=lambda inst, v: setattr(self.header_rect, 'size', v))
        
        cols = [("ID", 0.08), ("Nombre", 0.3), ("Cat", 0.18), ("Precio", 0.12), ("Emoji", 0.1), ("Prep", 0.1), ("Disp", 0.12)]
        for text, hint in cols:
            header.add_widget(Label(text=text, bold=True, size_hint_x=hint, font_size='10sp', color=(0,0,0,1)))
        self.grid.add_widget(header)

        # Contenedor para scroll
        from kivy.uix.scrollview import ScrollView
        self.menu_scroll = ScrollView(size_hint_y=1) # Expandir para ocupar el espacio restante
        self.menu_list_layout = GridLayout(cols=1, size_hint_y=None, spacing=2)
        self.menu_list_layout.bind(minimum_height=self.menu_list_layout.setter('height'))
        self.menu_scroll.add_widget(self.menu_list_layout)
        self.grid.add_widget(self.menu_scroll)

        # --- FORMULARIO INFERIOR ---
        form_box = BoxLayout(orientation='vertical', size_hint_y=None, height=265, padding=10, spacing=5)
        with form_box.canvas.before:
            Color(*PANEL_COLOR)
            self.form_rect = RoundedRectangle(pos=form_box.pos, size=form_box.size, radius=[10])
        form_box.bind(pos=lambda inst, v: setattr(self.form_rect, 'pos', v),
                      size=lambda inst, v: setattr(self.form_rect, 'size', v))
        
        row_title = BoxLayout(size_hint_y=None, height=35, spacing=10)
        row_title.add_widget(Label(text="Añadir Nuevo Producto", bold=True, halign='left'))
        btn_refresh = Button(text="REFRESCAR", size_hint_x=None, width=100, background_color=(0.2, 0.5, 0.8, 1), font_size='11sp')
        btn_refresh.bind(on_press=lambda x: APIClient.get_menu(self.on_menu_edit_success, self.on_error))
        row_title.add_widget(btn_refresh)
        form_box.add_widget(row_title)
        
        row1 = BoxLayout(spacing=10, size_hint_y=None, height=40)
        self.prod_nombre = TextInput(hint_text='Nombre', multiline=False)
        self.prod_precio = TextInput(hint_text='Precio', multiline=False, input_filter='float')
        row1.add_widget(self.prod_nombre)
        row1.add_widget(self.prod_precio)
        form_box.add_widget(row1)

        row2 = BoxLayout(spacing=10, size_hint_y=None, height=40)
        from kivy.uix.spinner import Spinner
        self.prod_cat_spinner = Spinner(text='Categoría', values=('General',), size_hint_x=0.6)
        self.prod_emoji = TextInput(hint_text='Emoji', multiline=False, size_hint_x=0.4)
        row2.add_widget(self.prod_cat_spinner)
        row2.add_widget(self.prod_emoji)
        form_box.add_widget(row2)

        row3 = BoxLayout(spacing=10, size_hint_y=None, height=40)
        self.prod_prep = TextInput(hint_text='Prep (min)', multiline=False, input_filter='int', text='15')
        row3.add_widget(Label(text="Minutos:", size_hint_x=0.3))
        row3.add_widget(self.prod_prep)
        form_box.add_widget(row3)

        # Nueva fila para selección de imagen
        row_img = BoxLayout(spacing=10, size_hint_y=None, height=40)
        self.btn_sel_img = Button(text="SELECCIONAR IMAGEN", background_color=(0.3, 0.4, 0.6, 1), font_size='12sp', bold=True)
        self.lbl_img_path = Label(text="Ninguna", font_size='10sp', color=(0.7, 0.7, 0.7, 1), halign='left')
        self.lbl_img_path.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        row_img.add_widget(self.btn_sel_img)
        row_img.add_widget(self.lbl_img_path)
        form_box.add_widget(row_img)
        
        self.selected_img_path = None
        self.btn_sel_img.bind(on_press=self.open_image_picker)

        btn_row = BoxLayout(spacing=10, size_hint_y=None, height=50)
        btn_add = Button(text="CREAR PRODUCTO", background_color=INFO_COLOR, bold=True)
        btn_del = Button(text="ELIMINAR SELECCIONADO", background_color=(0.8, 0.3, 0.3, 1), bold=True)
        btn_row.add_widget(btn_add)
        btn_row.add_widget(btn_del)
        form_box.add_widget(btn_row)
        
        self.grid.add_widget(form_box)
        
        # Acciones
        btn_add.bind(on_press=self.action_create_product)
        btn_del.bind(on_press=self.action_delete_product)
        
        self.selected_product_id = None
        APIClient.get_menu(self.on_menu_edit_success, self.on_error)

    def on_menu_edit_success(self, req, result):
        if result.get('status') == 'success':
            data = result.get('data', [])
            # Actualizar Spinner de categorías
            cats = sorted(list(set([p.get('categoria') for p in data if p.get('categoria')])))
            if cats: self.prod_cat_spinner.values = cats
            
            self.menu_list_layout.clear_widgets()
            for p in data:
                row = ClickableBoxLayout(orientation='horizontal', size_hint_y=None, height=45, padding=[5,0])
                row.product_id = p.get('id')
                
                # Highlight si está seleccionado
                def update_row_bg(inst, val):
                    inst.canvas.before.clear()
                    with inst.canvas.before:
                        if getattr(self, 'selected_product_id', None) == inst.product_id:
                            Color(0.2, 0.6, 0.8, 0.5)
                        else:
                            Color(0.1, 0.1, 0.1, 0.2)
                        Rectangle(pos=inst.pos, size=inst.size)
                
                row.bind(pos=update_row_bg, size=update_row_bg)
                row.bind(on_press=lambda inst: self.select_product(inst.product_id))
                
                row.add_widget(Label(text=str(p.get('id')), size_hint_x=0.08, font_size='11sp'))
                row.add_widget(Label(text=p.get('nombre',''), size_hint_x=0.3, font_size='11sp', halign='left'))
                row.add_widget(Label(text=p.get('categoria',''), size_hint_x=0.18, font_size='10sp'))
                row.add_widget(Label(text=f"${p.get('precio',0):.2f}", size_hint_x=0.12, font_size='11sp'))
                row.add_widget(Label(text=p.get('emoji',''), size_hint_x=0.1, font_size='14sp'))
                row.add_widget(Label(text=str(p.get('prep_duration', 15)), size_hint_x=0.1, font_size='11sp'))
                row.add_widget(Label(text="SÍ" if p.get('disponible') else "NO", size_hint_x=0.12, font_size='10sp'))
                
                self.menu_list_layout.add_widget(row)

    def select_product(self, pid):
        self.selected_product_id = pid
        # Refrescar visual de la lista (forzar redibujado de fondos)
        for child in self.menu_list_layout.children:
            child.dispatch('pos', child.pos)

    def open_image_picker(self, *args):
        from kivy.uix.filechooser import FileChooserIconView
        import os
        
        content = BoxLayout(orientation='vertical', spacing=5, padding=5)
        fc = FileChooserIconView(path='.' if not os.path.exists('/sdcard') else '/sdcard', filters=['*.png', '*.jpg', '*.jpeg', '*.webp'])
        content.add_widget(fc)
        
        btn_box = BoxLayout(size_hint_y=None, height=45, spacing=10)
        btn_cancel = Button(text="CANCELAR")
        btn_ok = Button(text="SELECCIONAR", background_color=INFO_COLOR)
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_ok)
        content.add_widget(btn_box)
        
        popup = Popup(title="Seleccionar Imagen", content=content, size_hint=(0.9, 0.9))
        
        def on_ok(inst):
            if fc.selection:
                self.selected_img_path = fc.selection[0]
                self.lbl_img_path.text = os.path.basename(self.selected_img_path)
                self.lbl_img_path.color = SUCCESS_COLOR
                popup.dismiss()
        
        btn_ok.bind(on_press=on_ok)
        btn_cancel.bind(on_press=popup.dismiss)
        popup.open()

    def action_create_product(self, *args):
        if not self.prod_nombre.text: return
        nombre = self.prod_nombre.text
        data = {
            'nombre': nombre,
            'precio': float(self.prod_precio.text or 0),
            'categoria': self.prod_cat_spinner.text if self.prod_cat_spinner.text != 'Categoría' else 'General',
            'emoji': self.prod_emoji.text or '🍽',
            'prep_duration': int(self.prod_prep.text or 15)
        }
        
        def on_creation_success(req, res):
            if self.selected_img_path:
                # Si hay imagen, subirla después de crear el producto
                APIClient.upload_product_image(
                    nombre, 
                    self.selected_img_path, 
                    lambda r, rs: self.finalize_product_creation(),
                    self.on_error
                )
            else:
                self.finalize_product_creation()

        APIClient.create_menu_item(data, on_creation_success, self.on_error)

    def finalize_product_creation(self):
        self.selected_img_path = None
        self.lbl_img_path.text = "Ninguna"
        self.lbl_img_path.color = (0.7, 0.7, 0.7, 1)
        self.prod_nombre.text = ""
        self.prod_precio.text = ""
        self.prod_emoji.text = ""
        self.load_menu_editor()
        Popup(title="Éxito", content=Label(text="Producto creado correctamente"), size_hint=(0.6, 0.2)).open()

    def action_delete_product(self, *args):
        if not self.selected_product_id:
            Popup(title="Aviso", content=Label(text="Seleccione un producto de la lista"), size_hint=(0.6, 0.2)).open()
            return
        
        def confirm_delete(btn):
            APIClient.delete_menu_item(self.selected_product_id, lambda r, res: self.load_menu_editor(), self.on_error)
            popup.dismiss()

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="¿Eliminar producto seleccionado?"))
        btn_confirm = Button(text="SÍ, ELIMINAR", background_color=(0.8, 0, 0, 1))
        btn_confirm.bind(on_press=confirm_delete)
        content.add_widget(btn_confirm)
        popup = Popup(title="Confirmar", content=content, size_hint=(0.7, 0.3))
        popup.open()

    def on_error(self, req, error):
        url = getattr(req, 'url', 'N/A')
        msg = f"Error en API\nURL: {url}\nDetalle: {str(error)[:100]}"
        Popup(title="Error de Conexión", content=Label(text=msg, font_size='12sp'), size_hint=(0.8, 0.4)).open()

    # --- CIERRES DE CAJA ---
    def load_cierres(self, *args):
        self._setup_sub_menu("Cierres de Caja")
        self.grid.clear_widgets()
        self.grid.cols = 1
        APIClient.get_cierres(self.on_cierres_success, self.on_error)

    def on_cierres_success(self, req, result):
        if result.get('status') == 'success':
            for c in result.get('data', []):
                card = ClickableBoxLayout(orientation='vertical', size_hint_y=None, height=120, padding=10)
                with card.canvas.before:
                    Color(0.24, 0.31, 0.39, 1)
                    rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[5])
                def _ur(inst, val, r=rect):
                    r.pos = inst.pos
                    r.size = inst.size
                card.bind(pos=_ur, size=_ur)
                
                # Al presionar, cargar el detalle
                card.bind(on_press=lambda inst, sid=c.get('id'): self.load_cierre_detalle(sid))
                
                estado_color = "00FF00" if c.get('estado') == 'ABIERTO' else "FF0000"
                lbl_t = Label(text=f"Sesión #{c.get('id')} - [color={estado_color}]{c.get('estado')}[/color]", markup=True, bold=True, halign='left', size_hint_y=0.3)
                lbl_t.bind(size=lbl_t.setter('text_size'))
                card.add_widget(lbl_t)
                
                info = f"Fecha: {c.get('inicio') or c.get('apertura')}\nTotal: ${(c.get('cierre_total') or 0):.2f}\nPresione para ver detalle"
                lbl_i = Label(text=info, font_size='12sp', halign='left', size_hint_y=0.7)
                lbl_i.bind(size=lbl_i.setter('text_size'))
                card.add_widget(lbl_i)
                self.grid.add_widget(card)

    def load_cierre_detalle(self, sesion_id):
        APIClient.get_cierre_detalle(sesion_id, self.on_cierre_detalle_success, self.on_error)

    def on_cierre_detalle_success(self, req, result):
        if result.get('status') == 'success':
            s = result.get('sesion', {})
            tickets = result.get('tickets', [])
            
            texto =  "****************************************\n"
            texto += "       INFORME DE CIERRE DE CAJA        \n"
            texto += "****************************************\n"
            texto += f"Cierre:   {s.get('cierre_at') or s.get('inicio', '---')}\n"
            texto += f"Cajero:   ID {s.get('usuario_id')} - {s.get('cajero_nombre') or s.get('username')}\n"
            texto += f"Sesión:   {s.get('id')}\n"
            texto += "----------------------------------------\n"
            texto += f"{'TICKET':<12} {'FECHA':<18} {'TOTAL':>8}\n"
            texto += "----------------------------------------\n"
            
            total_efectivo = 0
            for t in tickets:
                num = t.get('numero', 'N/A')
                fecha = (t.get('created_at') or '')[11:19]
                monto = (t.get('total') or 0)
                texto += f"{num:<12} {fecha:<18} {monto:>8.2f}\n"
                if t.get('metodo_pago') == 'EFECTIVO':
                    total_efectivo += monto
            
            texto += "----------------------------------------\n"
            texto += f"Total EFECTIVO                   {total_efectivo:>8.2f}\n"
            texto += f"Monto Inicial                    {(s.get('inicial') or 0):>8.2f}\n"
            texto += f"TOTAL EN CAJA                    {(s.get('cierre_total') or 0):>8.2f}\n"
            texto += "----------------------------------------\n"

            from kivy.uix.scrollview import ScrollView
            main_content = BoxLayout(orientation='vertical', padding=10, spacing=10)
            scroll = ScrollView()
            lbl = Label(text=texto, font_name='RobotoMono-Regular' if os.path.exists('assets/fonts/RobotoMono-Regular.ttf') else 'Roboto',
                        font_size='13sp', size_hint_y=None, halign='left', valign='top', padding=(10, 10))
            lbl.bind(texture_size=lbl.setter('size'))
            scroll.add_widget(lbl)
            main_content.add_widget(scroll)
            
            btn_row = BoxLayout(size_hint_y=None, height=60, spacing=10)
            btn_reprint = Button(text="REIMPRIMIR REPORTE", background_color=INFO_COLOR, bold=True)
            btn_cerrar = Button(text="CERRAR", background_color=PANEL_COLOR)
            btn_row.add_widget(btn_reprint)
            btn_row.add_widget(btn_cerrar)
            main_content.add_widget(btn_row)
            
            popup = Popup(title=f"Reporte de Cierre #{s.get('id')}", content=main_content, size_hint=(0.9, 0.9))
            btn_cerrar.bind(on_press=popup.dismiss)
            # Reimprimir: Abre diálogo de sistema
            def _print_old_cierre(inst):
                from kivy.utils import platform
                import os
                html = f"<html><body style='font-family:monospace; font-size:12px;'><pre>{texto}</pre></body></html>"
                if platform == 'android':
                    try:
                        from jnius import autoclass, cast
                        PythonActivity = autoclass('org.kivy.android.PythonActivity')
                        current_activity = PythonActivity.mActivity
                        Context = autoclass('android.content.Context')
                        PrintManager = autoclass('android.print.PrintManager')
                        print_manager = cast(PrintManager, current_activity.getSystemService(Context.PRINT_SERVICE))
                        WebView = autoclass('android.webkit.WebView')
                        webview = WebView(current_activity)
                        webview.loadDataWithBaseURL(None, html, "text/html", "UTF-8", None)
                        job_name = f"Cierre_Reimpresion_{s.get('id')}"
                        print_adapter = webview.createPrintDocumentAdapter(job_name)
                        print_manager.print(job_name, print_adapter, None)
                    except Exception as e: print(f"Error print Android: {e}")
                else:
                    try:
                        import tempfile
                        import win32api
                        fd, path = tempfile.mkstemp(suffix=".txt")
                        with os.fdopen(fd, 'w') as f: f.write(texto)
                        win32api.ShellExecute(0, "print", path, None, ".", 0)
                    except Exception as e: print(f"Error print Win: {e}")

            btn_reprint.bind(on_press=_print_old_cierre)
            popup.open()

    # --- SEGURIDAD ---
    def load_seguridad(self, *args):
        self._setup_sub_menu("Seguridad / Logs")
        self.grid.clear_widgets()
        self.grid.cols = 1
        APIClient.get_seguridad(self.on_seguridad_success, self.on_error)

    def on_seguridad_success(self, req, result):
        if result.get('status') == 'success':
            log_text = result.get('data', '')
            lbl = Label(text=log_text, size_hint_y=None, font_size='10sp', halign='left', valign='top', markup=False)
            lbl.bind(width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None)), texture_size=lambda *x: lbl.setter('height')(lbl, lbl.texture_size[1]))
            self.grid.add_widget(lbl)

    # --- HISTORIAL DE VENTAS ---
    def load_ventas_historial(self, *args):
        self._setup_sub_menu("Historial de Facturación")
        self.grid.clear_widgets()
        self.grid.cols = 1
        
        # Conexión Status / Config
        status_row = BoxLayout(size_hint_y=None, height=40, spacing=10)
        self.ip_label = Label(text=f"Servidor: {SERVER_URL}", font_size='11sp')
        status_row.add_widget(self.ip_label)
        btn_ip = Button(text="CONFIG IP", size_hint_x=0.3, background_color=INFO_COLOR)
        btn_ip.bind(on_press=self.show_ip_config)
        status_row.add_widget(btn_ip)
        self.grid.add_widget(status_row)

        # Fila 1: Texto
        row1 = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.hist_search_input = TextInput(hint_text="Número o Mesa...", multiline=False)
        row1.add_widget(self.hist_search_input)
        self.grid.add_widget(row1)
        
        # Fila 2: Fecha + Botón
        row2 = BoxLayout(size_hint_y=None, height=50, spacing=10)
        import datetime
        hoy = datetime.datetime.now().strftime('%Y-%m-%d')
        self.hist_date_input = TextInput(text=hoy, hint_text="YYYY-MM-DD", multiline=False, size_hint_x=0.6)
        row2.add_widget(self.hist_date_input)
        
        btn_buscar = Button(text="🔍 BUSCAR", size_hint_x=0.4, background_color=PANEL_COLOR, bold=True)
        btn_buscar.bind(on_press=lambda x: self.fetch_ventas_historial())
        row2.add_widget(btn_buscar)
        self.grid.add_widget(row2)
        
        # Lista de resultados
        self.hist_scroll = ScrollView(size_hint_y=None, height=Window.height * 0.6)
        self.hist_list = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.hist_list.bind(minimum_height=self.hist_list.setter('height'))
        self.hist_scroll.add_widget(self.hist_list)
        self.grid.add_widget(self.hist_scroll)
        
        self.fetch_ventas_historial()

    def show_ip_config(self, instance):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="IP del Servidor:"))
        ip_in = TextInput(text=SERVER_URL.replace('http://', '').split(':')[0], multiline=False)
        content.add_widget(ip_in)
        btn = Button(text="CONECTAR", background_color=SUCCESS_COLOR)
        content.add_widget(btn)
        pop = Popup(title="Configuración", content=content, size_hint=(0.8, 0.4))
        def _save(b):
            global SERVER_URL
            if ip_in.text:
                SERVER_URL = f"http://{ip_in.text.strip()}:5000"
                self.ip_label.text = f"Servidor: {SERVER_URL}"
                pop.dismiss()
                self.fetch_ventas_historial()
        btn.bind(on_press=_save)
        pop.open()

    def fetch_ventas_historial(self):
        if not SERVER_URL:
            self.hist_list.clear_widgets()
            self.hist_list.add_widget(Label(text="⚠️ Error: No hay conexión con el servidor.\nVerifique que el servidor esté encendido.", color=DANGER_COLOR, halign='center'))
            return

        txt = self.hist_search_input.text.strip()
        fec = self.hist_date_input.text.strip()
        self.hist_list.clear_widgets()
        self.hist_list.add_widget(Label(text="Buscando facturas...", size_hint_y=None, height=40))
        APIClient.get_historial_pedidos(txt, fec, self.on_historial_success, self.on_historial_error)

    def on_historial_error(self, req, error):
        self.hist_list.clear_widgets()
        self.hist_list.add_widget(Label(text=f"❌ Error de conexión:\n{error}", color=DANGER_COLOR, halign='center'))

    def on_historial_success(self, req, result):
        self.hist_list.clear_widgets()
        if result.get('status') == 'success':
            pedidos = result.get('data', [])
            if not pedidos:
                self.hist_list.add_widget(Label(text="No se encontraron facturas.", size_hint_y=None, height=40))
                return
                
            import json
            for p in pedidos:
                # Asegurar que p sea un diccionario (por si viene como string JSON)
                if isinstance(p, str):
                    try:
                        p = json.loads(p)
                    except:
                        continue
                
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=70, padding=10, spacing=10)
                with row.canvas.before:
                    Color(0.2, 0.25, 0.3, 1)
                    rect = RoundedRectangle(pos=row.pos, size=row.size, radius=[5])
                def _ur(inst, val, r=rect): r.pos = inst.pos; r.size = inst.size
                row.bind(pos=_ur, size=_ur)
                
                # Info Factura
                info = BoxLayout(orientation='vertical', size_hint_x=0.7)
                info.add_widget(Label(text=f"FAC: {p.get('numero')}", bold=True, halign='left', text_size=(Window.width*0.5, None)))
                fecha_str = p.get('created_at', '').replace('T', ' ')[:16]
                info.add_widget(Label(text=f"Mesa: {p.get('mesa')} | {fecha_str} | ${p.get('total', 0):.2f}", font_size='11sp', halign='left', text_size=(Window.width*0.5, None)))
                row.add_widget(info)
                
                # Botones de impresión (Doble opción)
                btn_layout = BoxLayout(size_hint_x=0.45, spacing=5)
                
                btn_sunmi = Button(text="🖨️\nSUNMI", background_color=SUCCESS_COLOR, font_size='10sp', bold=True, halign='center')
                btn_sunmi.bind(on_press=lambda x, data=p: self.reprint_invoice_sunmi(data))
                
                btn_sys = Button(text="📱\nSISTEMA", background_color=INFO_COLOR, font_size='10sp', bold=True, halign='center')
                btn_sys.bind(on_press=lambda x, data=p: self.reprint_invoice_system(data))
                
                btn_layout.add_widget(btn_sunmi)
                btn_layout.add_widget(btn_sys)
                row.add_widget(btn_layout)
                
                self.hist_list.add_widget(row)

    def reprint_invoice_sunmi(self, pedido_data):
        """Impresión directa por Sunmi (Bluetooth RAW)."""
        from kivy.utils import platform
        if platform != 'android':
            SunmiPrinter.print_receipt_preview(pedido_data)
            return
            
        try:
            from jnius import autoclass
            import datetime
            import os
            
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                SunmiPrinter.print_receipt_preview(pedido_data)
                return
                
            paired_devices = adapter.getBondedDevices().toArray()
            sunmi_device = None
            for d in paired_devices:
                if d.getName() == 'InnerPrinter':
                    sunmi_device = d
                    break
                    
            if not sunmi_device:
                self.on_error(None, "Impresora Sunmi no detectada")
                return
                
            UUID = autoclass('java.util.UUID')
            spp_uuid = UUID.fromString('00001101-0000-1000-8000-00805F9B34FB')
            socket = sunmi_device.createRfcommSocketToServiceRecord(spp_uuid)
            socket.connect()
            out_stream = socket.getOutputStream()
            
            def send(cmd): out_stream.write(cmd)
            def out(text): send(text.encode('cp850', 'replace'))
            
            send(b'\x1b\x40') # INIT
            send(b'\x1b\x61\x01') # ALIGN_CENTER
            out("      PIK'TA GRILL SOLUTIONS\r\n")
            out("--------------------------------\r\n")
            out(f" FACTURA: {pedido_data.get('numero', '000000')}\r\n")
            out(f" FECHA:   {datetime.datetime.now().strftime('%d/%m/%Y %I:%M %p')}\r\n")
            out("--------------------------------\r\n")
            for item in pedido_data.get('items', []):
                out(f"{item.get('nombre', '')[:32]}\r\n")
                out(f" {item.get('cantidad', 1)}x ${item.get('precio', 0):.2f}  ${item.get('cantidad', 1)*item.get('precio', 0):.2f}\r\n")
            out("--------------------------------\r\n")
            out(f" TOTAL: B/.{float(pedido_data.get('total', 0)):.2f}\r\n")
            out("--------------------------------\r\n")
            out("¡GRACIAS POR SU PREFERENCIA!\r\n")
            send(b'\r\n' * 4)
            out_stream.flush()
            socket.close()
        except Exception as e:
            self.on_error(None, f"Error impresión directa: {e}")

    def reprint_invoice_system(self, pedido_data):
        """Impresión usando el diálogo nativo de Android (Universal)."""
        SunmiPrinter.print_receipt(pedido_data)

    # --- GESTIÓN DE PUBLICIDAD ---
    def load_ads_manager(self, *args):
        self._setup_sub_menu("Gestión de Publicidad TV")
        self.grid.clear_widgets()
        self.grid.cols = 1
        
        btn_upload = Button(text="+ Subir Nuevo Anuncio (Imagen/Video)", size_hint_y=None, height=60, background_color=SUCCESS_COLOR)
        btn_upload.bind(on_press=self.show_file_chooser)
        self.grid.add_widget(btn_upload)
        
        APIClient.get_ads(self.on_ads_manager_success, self.on_error)

    def on_ads_manager_success(self, req, result):
        if result.get('status') == 'success':
            for ad_name in result.get('images', []):
                card = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, padding=10, spacing=10)
                with card.canvas.before:
                    Color(*PANEL_COLOR)
                    rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[5])
                def _ur(inst, val, r=rect):
                    r.pos = inst.pos
                    r.size = inst.size
                card.bind(pos=_ur, size=_ur)
                
                card.add_widget(Label(text=ad_name, size_hint_x=0.7, halign='left'))
                
                btn_del = Button(text="Eliminar", size_hint_x=0.3, background_color=DANGER_COLOR)
                btn_del.bind(on_press=lambda inst, name=ad_name: self.confirm_delete_ad(name))
                card.add_widget(btn_del)
                
                self.grid.add_widget(card)

    def confirm_delete_ad(self, ad_name):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=f"¿Eliminar '{ad_name}'?"))
        
        btn_row = BoxLayout(spacing=10, size_hint_y=None, height=50)
        btn_si = Button(text="Eliminar", background_color=DANGER_COLOR)
        btn_no = Button(text="Cancelar")
        btn_row.add_widget(btn_si)
        btn_row.add_widget(btn_no)
        content.add_widget(btn_row)
        
        popup = Popup(title="Confirmar", content=content, size_hint=(0.8, 0.4))
        btn_no.bind(on_press=popup.dismiss)
        btn_si.bind(on_press=lambda x: self.realizar_eliminar_ad(ad_name, popup))
        popup.open()

    def realizar_eliminar_ad(self, ad_name, popup):
        popup.dismiss()
        APIClient.delete_ad(ad_name, lambda r, res: self.load_ads_manager(), self.on_error)

    def show_file_chooser(self, instance):
        # Kivy FileChooser simple
        from kivy.uix.filechooser import FileChooserIconView
        content = BoxLayout(orientation='vertical')
        fc = FileChooserIconView(path='/sdcard' if os.path.exists('/sdcard') else '.', 
                                 filters=['*.png', '*.jpg', '*.jpeg', '*.mp4', '*.avi'])
        content.add_widget(fc)
        
        btn_sel = Button(text="Subir Seleccionado", size_hint_y=None, height=50, background_color=SUCCESS_COLOR)
        content.add_widget(btn_sel)
        
        popup = Popup(title="Seleccionar Archivo", content=content, size_hint=(0.9, 0.9))
        
        def do_upload(btn):
            if fc.selection:
                popup.dismiss()
                APIClient.upload_ad(fc.selection[0], lambda r, res: self.load_ads_manager(), self.on_error)
            else:
                Popup(title="Error", content=Label(text="Seleccione un archivo"), size_hint=(0.6, 0.3)).open()
                
        btn_sel.bind(on_press=do_upload)
        popup.open()

    def go_back(self, instance):
        self.manager.current = 'dashboard'

class PiktaMobileApp(App):
    def build(self):
        Window.clearcolor = BG_COLOR
        self.sm = ScreenManager()
        
        # Cargar solo el Login inicialmente para un arranque instantáneo
        self.sm.add_widget(LoginScreen(name='login'))
        
        # Cargar el resto de pantallas en el siguiente frame para no bloquear el inicio
        Clock.schedule_once(self.lazy_load_screens, 0.1)
        
        return self.sm

    def lazy_load_screens(self, dt):
        """Carga las pantallas pesadas después de mostrar el Login."""
        if 'dashboard' not in self.sm.screen_names:
            self.sm.add_widget(DashboardScreen(name='dashboard'))
            self.sm.add_widget(POSScreen(name='pos'))
            self.sm.add_widget(KDSScreen(name='kds'))
            self.sm.add_widget(CajaScreen(name='caja'))
            self.sm.add_widget(AdminScreen(name='admin'))
            self.sm.add_widget(AdsScreen(name='ads'))

    def on_pause(self):
        # Detener publicidad si está activa al minimizar
        if self.sm.current == 'ads':
            self.sm.get_screen('ads').stop_ads()
        return True # Permitir pausa

    def on_resume(self):
        # Reiniciar publicidad si regresamos y era la pantalla actual
        if self.sm.current == 'ads':
            self.sm.get_screen('ads').on_enter()

    def on_stop(self):
        # Limpieza total al cerrar
        if 'ads' in self.sm.screen_names:
            self.sm.get_screen('ads').stop_ads()


if __name__ == '__main__':
    PiktaMobileApp().run()