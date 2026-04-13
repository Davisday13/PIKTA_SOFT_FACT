import webview
import sys

def open_whatsapp():
    try:
        # Crear la ventana de WhatsApp Web independiente
        webview.create_window(
            'WhatsApp Web PIK\'TA', 
            'https://web.whatsapp.com/',
            width=1200,
            height=900,
            resizable=True
        )
        webview.start()
    except Exception as e:
        with open('error_log.txt', 'a') as f:
            f.write(f"\nError en whatsapp_launcher.py: {str(e)}")

if __name__ == '__main__':
    open_whatsapp()
