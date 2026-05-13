import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from email.utils import make_msgid, formatdate
from src.config.config_manager import ConfigManager
from src.utils.logger import logger, mask_email

class EmailService:
    """Clase para el envío de correos electrónicos vía SMTP."""
    
    def __init__(self):
        # Leemos configuración dinámica
        config = ConfigManager.get_config()
        self.host = config.get("smtp_host", "smtp.gmail.com")
        self.port = int(config.get("smtp_port", 587))
        self.user = config.get("smtp_user", "")
        self.password = config.get("smtp_password", "")
        self.email_body = config.get("email_body", "")
        self.server = None
        
    def connect(self):
        """Abre la conexión SMTP con el servidor."""
        if not self.user or not self.password:
            raise ValueError("Las credenciales SMTP no están configuradas correctamente en el archivo .env")
        self.server = smtplib.SMTP(self.host, self.port, timeout=30)
        self.server.starttls() # TLS 1.2
        self.server.login(self.user, self.password)
        
    def disconnect(self):
        """Cierra la conexión SMTP."""
        if self.server:
            self.server.quit()
            self.server = None

    def send_email_with_attachment(self, to_email: str, subject: str, attachment_path: str, filename_override: str = None):
        """Envía un correo con el archivo PDF adjunto."""
        try:
            if not self.user or not self.password:
                raise ValueError("Las credenciales SMTP no están configuradas correctamente en el archivo .env")

            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = to_email
            msg['Subject'] = Header(subject, 'utf-8')
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid()
            
            # Cuerpo del correo (Dinámico desde configuración)
            body = self.email_body
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Adjuntar PDF
            if os.path.exists(attachment_path):
                filename = filename_override if filename_override else os.path.basename(attachment_path)
                with open(attachment_path, "rb") as f:
                    part = MIMEApplication(f.read())
                # Usamos una tupla (CHARSET, LANGUAGE, VALUE) para evitar el error de codec ascii
                part.add_header('Content-Disposition', 'attachment', filename=('utf-8', '', filename))
                msg.attach(part)
            else:
                raise FileNotFoundError(f"No se encontró el adjunto: {attachment_path}")
            
            # Envío utilizando la conexión persistente
            if not self.server:
                raise ConnectionError("No hay una conexión SMTP activa. Llama a connect() primero.")
                
            self.server.send_message(msg)
                
            logger.info(f"Correo enviado exitosamente a {mask_email(to_email)}")
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar correo a {mask_email(to_email)}: {str(e)}")
            raise e
