import webview
import sys
import os

def open_whatsapp():
    # Evitar múltiples instancias usando un archivo de bloqueo temporal
    import tempfile
    lock_file = os.path.join(tempfile.gettempdir(), 'pikta_whatsapp.lock')
    
    if os.path.exists(lock_file):
        try:
            # Intentar eliminar si es antiguo o quedó huérfano
            os.remove(lock_file)
        except:
            # Si no se puede borrar, es que otra instancia lo tiene abierto
            print("WhatsApp ya está en ejecución.")
            return

    try:
        # Crear el archivo de bloqueo
        with open(lock_file, 'w') as f: f.write(str(os.getpid()))
        
        # Obtener ruta absoluta del directorio actual para evitar problemas de permisos
        base_dir = os.path.dirname(os.path.abspath(__file__))
        session_dir = os.path.join(base_dir, 'whatsapp_session')
        
        # Asegurarse de que el directorio existe
        if not os.path.exists(session_dir):
            try:
                os.makedirs(session_dir)
            except Exception:
                # Si falla en el directorio del programa, usar el temporal del usuario
                import tempfile
                session_dir = os.path.join(tempfile.gettempdir(), 'pikta_whatsapp_session')
                if not os.path.exists(session_dir):
                    os.makedirs(session_dir)

        # User Agent de Chrome moderno para asegurar compatibilidad total y sonidos
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        
        # Crear la ventana de WhatsApp Web independiente
        window = webview.create_window(
            'WhatsApp Web PIK\'TA', 
            'https://web.whatsapp.com/',
            width=1200,
            height=900,
            resizable=True
        )
        
        # Script para intentar forzar la activación de sonidos y notificaciones
        def on_loaded(win):
            # Inyectar script para habilitar permisos si el navegador lo permite
            # y simular una interacción para desbloquear el autoplay de audio
            win.evaluate_js("""
                console.log('Inyectando script de activación...');
                // Simular un clic silencioso en el body para desbloquear audio
                document.body.click();
                
                // Intentar pedir permiso de notificación proactivamente
                if (window.Notification && Notification.permission !== 'granted') {
                    Notification.requestPermission();
                }
            """)

        # storage_path define dónde se guardará el perfil del navegador (caché, cookies, etc)
        # private_mode=False es crucial para que la sesión NO se borre al salir
        # Esto incluye caché, cookies y configuraciones de notificaciones/sonido
        webview.start(
            func=on_loaded,
            args=window,
            storage_path=session_dir, 
            user_agent=user_agent,
            private_mode=False,
            debug=False
        )
    except Exception as e:
        with open('error_log.txt', 'a') as f:
            f.write(f"\nError en whatsapp_launcher.py: {str(e)}")
    finally:
        # Limpiar el archivo de bloqueo al cerrar
        if os.path.exists(lock_file):
            try: os.remove(lock_file)
            except: pass

if __name__ == '__main__':
    open_whatsapp()
