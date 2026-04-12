from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.recycleview import RecycleView
from kivy.network.urlrequest import UrlRequest
from kivy.properties import StringProperty
import json

# ==========================================================
# CONFIGURACIÓN: CAMBIA ESTA IP POR LA DE TU COMPUTADORA
# ==========================================================
SERVER_URL = "http://192.168.1.100:5000" 

class MobileClient(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.padding = 20
        self.spacing = 10
        
        self.add_widget(Label(text="🚀 PIK'TA SOFT - CLIENTE MÓVIL", size_hint_y=0.1, font_size='20sp', bold=True))
        
        self.status_label = Label(text="Estado: Desconectado", size_hint_y=0.05, color=(1, 0.5, 0, 1))
        self.add_widget(self.status_label)
        
        # Área de visualización de datos
        self.data_label = Label(text="Presiona un botón para cargar datos", size_hint_y=0.7, halign='left', valign='top')
        self.data_label.bind(size=self.data_label.setter('text_size'))
        self.add_widget(self.data_label)
        
        btn_layout = BoxLayout(size_hint_y=0.15, spacing=10)
        btn_layout.add_widget(Button(text="Ver Menú", on_press=self.get_menu, background_color=(0.2, 0.5, 1, 1)))
        btn_layout.add_widget(Button(text="Ver Pedidos", on_press=self.get_orders, background_color=(0.1, 0.7, 0.5, 1)))
        self.add_widget(btn_layout)

    def get_menu(self, instance):
        self.status_label.text = "Cargando menú..."
        UrlRequest(f"{SERVER_URL}/api/menu", on_success=self.on_data, on_error=self.on_error, on_failure=self.on_error)

    def get_orders(self, instance):
        self.status_label.text = "Cargando pedidos..."
        UrlRequest(f"{SERVER_URL}/api/pedidos", on_success=self.on_data, on_error=self.on_error, on_failure=self.on_error)

    def on_data(self, request, result):
        if result.get('status') == 'success':
            self.status_label.text = "✅ Datos cargados con éxito"
            self.status_label.color = (0, 1, 0, 1)
            
            # Formatear datos para mostrar en pantalla
            display_text = ""
            data = result.get('data', [])
            if not data:
                display_text = "No hay información disponible."
            else:
                for item in data[:10]: # Mostrar los primeros 10
                    if 'nombre' in item: # Es un producto
                        display_text += f"• {item['nombre']} - ${item['precio']}\n"
                    elif 'numero' in item: # Es un pedido
                        display_text += f"• Orden: {item['numero']} | Mesa: {item['mesa']} | Total: ${item['total']}\n"
            
            self.data_label.text = display_text
        else:
            self.status_label.text = "❌ Error en respuesta del servidor"
            self.status_label.color = (1, 0, 0, 1)

    def on_error(self, request, error):
        self.status_label.text = f"❌ Error de conexión: {error}"
        self.status_label.color = (1, 0, 0, 1)
        self.data_label.text = f"Asegúrate de que:\n1. main_app.py esté corriendo.\n2. La IP {SERVER_URL} sea correcta.\n3. Ambos dispositivos estén en el mismo WiFi."

class PiktaMobileApp(App):
    def build(self):
        return MobileClient()

if __name__ == '__main__':
    PiktaMobileApp().run()
