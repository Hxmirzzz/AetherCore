from dataclasses import dataclass
from typing import List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

@dataclass
class EmailConfig:
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    from_email: str
    admin_emails: List[str]

class EmailNotifier:
    def __init__(self, config: EmailConfig):
        self._config = config
        self._logger = logging.getLogger(__name__)

    def enviar_alerta_error(self, error: Exception, contexto: str):
        """Envía email cuando hay errores críticos"""
        subject = f"🔴 ALERTA: Error en AetherCore - {contexto}"
        body = f"""
        <h2>Error Detectado en AetherCore</h2>
        <p><strong>Contexto:</strong> {contexto}</p>
        <p><strong>Error:</strong> {str(error)}</p>
        <p><strong>Tipo:</strong> {type(error).__name__}</p>
        <hr>
        <p><em>Este es un mensaje automático del sistema AetherCore</em></p>
        """
        self._enviar_email(subject, body)

    def enviar_alerta_bd_caida(self):
        """Envía email cuando hay caída en la base de datos"""
        subject = "🔴 ALERTA: Caída en Base de Datos AetherCore"
        body = """
        <h2>Caída Detectada en Base de Datos</h2>
        <p>El sistema ha detectado una interrupción en la conexión a la base de datos.</p>
        <p>Por favor, revisar inmediatamente el estado del servidor de base de datos.</p>
        <hr>
        <p><em>Este es un mensaje automático del sistema AetherCore</em></p>
        """
        self._enviar_email(subject, body)

    def enviar_resumen_procesamiento(self, stats: dict):
        """Envía resumen diario/semanal"""
        subject = "📊 Resumen de Procesamiento AetherCore"
        body = f"""
        <h2>Resumen de Procesamiento</h2>
        <ul>
            <li>Archivos procesados: {stats['total']}</li>
            <li>Exitosos: {stats['exitosos']} ✅</li>
            <li>Fallidos: {stats['fallidos']} ❌</li>
            <li>Órdenes generadas: {stats['ordenes']}</li>
        </ul>
        """
        self._enviar_email(subject, body)

    def _enviar_email(self, subject: str, body: str):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self._config.from_email
            msg['To'] = ', '.join(self._config.admin_emails)

            msg.attach(MIMEText(body, 'html'))

            with smtplib.SMTP(self._config.smtp_server, self._config.smtp_port) as server:
                server.starttls()
                server.login(self._config.username, self._config.password)
                server.send_message(msg)
            
            self._logger.info(f"Email enviado exitosamente a {msg['To']}")
        except Exception as e:
            self._logger.error(f"Error al enviar email: {e}")