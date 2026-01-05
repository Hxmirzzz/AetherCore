import pystray
from PIL import Image, ImageDraw
from threading import Thread
import webbrowser

class AetherCoreTrayApp:
    """Aplicación de system tray que muestra notificaciones"""
    
    def __init__(self):
        self.icon = None
        self.running = True

    def create_icon(self, color="blue"):
        """Crea un ícono de sistema simple para la aplicación"""
        width, height = 64, 64
        image = Image.new('RGBA', (width, height), color)
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            (width // 4, height // 4, width * 3 // 4, height * 3 // 4),
            fill='white'
        )
        return image

    def on_quit(self, icon, item):
        """Cierra la aplicación cuando se selecciona 'Salir' en el menú de tray"""
        self.running = False
        icon.stop()

    def open_dashboard(self, icon, item):
        """Abre el dashboard en el navegador"""
        webbrowser.open("http://localhost:8000")

    def show_notification(self, title, message):
        """Muestra una notificación en el system tray"""
        if self.icon:
            self.icon.notify(message, title)

    def run(self):
        """Inicia la aplicación de system tray"""
        menu = pystray.Menu(
            pystray.MenuItem('Abrir Dashboard', self.open_dashboard),
            pystray.MenuItem('Salir', self.on_quit)
        )
            
        self.icon = pystray.Icon("AetherCore", self.create_icon(), "AetherCore", menu)
        self.icon.run()