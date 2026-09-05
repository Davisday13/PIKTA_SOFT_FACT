import webview
import os
import sys

def main():
    session_dir = os.path.join(os.getcwd(), 'whatsapp_session')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        
    # Usar pywebview para crear una ventana que contenga WhatsApp Web
    window = webview.create_window(
        "WhatsApp Business - PIK'TA", 
        "https://web.whatsapp.com/",
        width=1024,
        height=768,
        text_select=True,
        zoomable=True
    )
    
    # Iniciar la ventana sin modo privado para que guarde la sesión y no pida QR cada vez
    webview.start(private_mode=False)

if __name__ == '__main__':
    main()
