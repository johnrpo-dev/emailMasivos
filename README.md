# Sistema de Envío Masivo Seguro

Sistema para el envío masivo de documentos PDF sensibles con cifrado AES-256 local y automatización de correo mediante SMTP.

## Requisitos Previos

- Python 3.10+
- Cuenta de Google con Verificación en 2 Pasos y Contraseña de Aplicación de 16 caracteres.

## Instalación

1. Clona el repositorio.
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Abre la aplicación y dirígete a la pestaña de **Configuración** para ingresar tus credenciales y ajustar la plantilla del correo.

## Ejecución

Ejecuta el archivo principal para abrir la interfaz gráfica:

```bash
python src/main.py
```

## Estructura del CSV
El archivo CSV debe contener las siguientes columnas (el orden no importa, pero los nombres sí):
- `email`: Correo destino.
- `id_archivo`: Nombre del archivo PDF (ej. `documento.pdf`).
- `id_servicio`: Asunto del correo.
- `cedula`: Número de documento de identidad del usuario (se usará como contraseña para cifrar el PDF).
