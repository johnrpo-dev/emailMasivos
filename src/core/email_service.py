import smtplib
import os
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from email.utils import make_msgid, formatdate, formataddr
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
        self.sender_name = config.get("sender_name", "SEMS Pro")
        self.logo_path = config.get("logo_path", "")
        self.email_body = config.get("email_body", "")
        self.server = None
        
    def connect(self):
        """Abre la conexión SMTP con el servidor de forma segura.
        
        Soporta SMTPS (implícito en puerto 465) y STARTTLS (explícito en puerto 587/otros),
        con validación estricta de certificados SSL/TLS para prevenir ataques MITM y stripping.
        """
        if not self.user or not self.password:
            raise ValueError("Las credenciales SMTP no están configuradas correctamente en el archivo de configuración.")
        
        # Crear contexto SSL seguro por defecto (valida certificados de CA y hostname)
        context = ssl.create_default_context()
        
        try:
            if self.port == 465:
                logger.info("Estableciendo conexión cifrada implícita SMTPS (puerto 465)...")
                self.server = smtplib.SMTP_SSL(self.host, self.port, context=context, timeout=30)
            else:
                logger.info(f"Estableciendo conexión SMTP estándar (puerto {self.port})...")
                self.server = smtplib.SMTP(self.host, self.port, timeout=30)
                
                # Handshake inicial EHLO
                self.server.ehlo()
                
                # Mitigación STARTTLS Stripping: Verificar que el servidor soporte STARTTLS
                if not self.server.has_extn("starttls"):
                    self.server.quit()
                    raise ConnectionError("El servidor SMTP no anuncia soporte para STARTTLS. Conexión abortada por seguridad.")
                
                # Actualizar el canal a cifrado SSL/TLS de forma segura con el contexto verificado
                self.server.starttls(context=context)
                self.server.ehlo()  # Re-identificar sobre el canal seguro
                
            self.server.login(self.user, self.password)
            logger.info("Conexión SMTP autenticada de forma segura.")
        except Exception as e:
            logger.error(f"Fallo al conectar al servidor SMTP seguro ({self.host}:{self.port}): {str(e)}")
            if self.server:
                try:
                    self.server.quit()
                except Exception:
                    pass
                self.server = None
            raise e
        
    def disconnect(self):
        """Cierra la conexión SMTP."""
        if self.server:
            self.server.quit()
            self.server = None

    def send_email_with_attachment(self, to_email: str, subject: str, attachment_path: str, filename_override: str = None):
        """Envía un correo con el archivo PDF adjunto."""
        try:
            if not self.user or not self.password:
                raise ValueError("Las credenciales SMTP no están configuradas correctamente en el archivo de configuración.")

            # Crear mensaje
            msg = MIMEMultipart('mixed')
            msg['From'] = formataddr((self.sender_name, self.user))
            msg['To'] = to_email
            msg['Subject'] = Header(subject, 'utf-8')
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid()
            
            # Adjuntar logo local inline si existe (100% seguro y offline)
            has_logo = False
            if self.logo_path and os.path.exists(self.logo_path):
                try:
                    with open(self.logo_path, 'rb') as f:
                        img_data = f.read()
                    from email.mime.image import MIMEImage
                    logo_part = MIMEImage(img_data)
                    logo_part.add_header('Content-ID', '<logo_image>')
                    logo_part.add_header('Content-Disposition', 'inline', filename=os.path.basename(self.logo_path))
                    msg.attach(logo_part)
                    has_logo = True
                except Exception as e:
                    logger.error(f"No se pudo adjuntar el logo local inline: {e}")

            # Cuerpo del correo: multipart/alternative (texto plano + HTML)
            body = self.email_body
            alternative = MIMEMultipart('alternative')
            alternative.attach(MIMEText(body, 'plain', 'utf-8'))
            alternative.attach(MIMEText(self._build_html_body(body, has_logo), 'html', 'utf-8'))
            msg.attach(alternative)
            
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

    def _build_html_body(self, plain_text: str, has_logo: bool) -> str:
        """Convierte el texto plano del cuerpo en una plantilla HTML profesional."""
        # Escapar caracteres HTML y convertir saltos de línea
        import html
        escaped = html.escape(plain_text)
        paragraphs = escaped.split('\n\n')
        html_paragraphs = ''.join(
            f'<p style="margin:0 0 12px 0;line-height:1.6;color:#334155;">{p.replace(chr(10), "<br>")}</p>'
            for p in paragraphs if p.strip()
        )
        
        # Cabecera dinámica (Logo de empresa inline o en su defecto texto con nombre)
        header_content = f'<img src="cid:logo_image" alt="{self.sender_name}" style="max-height: 50px; max-width: 240px; display: block; border:0;" />' if has_logo else f'<h1 style="margin:0;font-size:20px;color:#ffffff;font-weight:600;">{self.sender_name}</h1>'
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;padding:32px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);overflow:hidden;">
  <tr><td style="background:linear-gradient(135deg,#4f46e5,#6366f1);padding:24px 32px;">
    {header_content}
  </td></tr>
  <tr><td style="padding:32px;">
    {html_paragraphs}
  </td></tr>
  <tr><td style="padding:16px 32px;background-color:#f8fafc;border-top:1px solid #e2e8f0;">
    <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center;">Este correo fue generado automáticamente por {self.sender_name}.</p>
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
