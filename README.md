# SEMS Pro — Sistema de Envíos Masivos Seguros

SEMS Pro es una aplicación de escritorio premium diseñada para automatizar el cifrado local de archivos PDF en estándar AES-256 (PDF 2.0 / R6) y enviarlos masivamente a través de un servidor SMTP con soporte STARTTLS/SSL cifrado.

Esta solución está diseñada bajo principios de **Privacidad por Diseño (Privacy by Design)** y cuenta con una arquitectura de seguridad auditada.

---

## 🚀 Características Clave

* **Cifrado AES-256 en Repositorio Local**: Cifra PDFs de forma nativa utilizando la cédula del destinatario y opcionalmente un prefijo/sufijo configurable para fortalecer la entropía de la clave.
* **Seguridad de Datos y RAM**: Las credenciales SMTP críticas se almacenan en la bóveda de credenciales de Windows (Credential Manager / Keyring) y se consultan *just-in-time* al enviar, garantizando la eliminación de secretos en claro de la RAM.
* **Licenciamiento Criptográfico (DRM)**: Validación asimétrica Ed25519 con marcas de tiempo conscientes en UTC para evitar desincronización horaria o DST.
* **Mitigación de Bloqueos (Throttling)**: Sistema de cola y retardo configurable entre envíos para proteger la reputación SMTP corporativa y evitar suspensiones por Gmail/Workspace.
* **Defensa anti-Path Traversal**: Chequeo estricto de rutas físicas reales de archivos para evitar fuga de archivos del sistema por inyecciones en el CSV.
* **Rate Limiting y Lockout**: Protección anti-bruteforce en la activación de licencias (máximo 5 intentos, bloqueo temporal de 5 minutos y delay de validación).

---

## 🛠️ Requisitos Previos

* Python 3.10+
* Sistema operativo Windows (requerido por la integración de Windows Credential Manager).
* Una cuenta de correo electrónico habilitada para SMTP (ej. Google Workspace / Gmail con Contraseña de Aplicación de 16 caracteres).

---

## 📦 Instalación y Setup de Desarrollo

1. Clona este repositorio.
2. Instala las dependencias necesarias de Python:
   ```bash
   pip install -r requirements.txt
   ```

### Ejecutar Suite de Pruebas Unitarias
El proyecto cuenta con un motor de pruebas unitarias automatizadas para certificar la sanitización de nombres, prevención de Path Traversal y validador de dominios:
```bash
python -m unittest discover tests -v
```

---

## 💻 Ejecución

Para iniciar la aplicación gráfica principal:
```bash
python src/main.py
```

---

## 🔑 Gestión de Licencias (Solo Desarrollador)

Para la administración del software y licenciamiento a clientes, se incluyen scripts auxiliares:

1. **Generar una nueva Licencia**:
   Genera una clave Base64 firmada criptográficamente para un cliente. Las llaves Ed25519 se gestionan de forma segura fuera del repositorio en la carpeta `%APPDATA%/SEMS_Pro/keys/`.
   ```bash
   python generar_licencia.py
   ```
   *Nota: Recuerda configurar la llave pública hex impresa en la variable `PUBLIC_KEY_HEX` de `src/core/license_manager.py` si rotas las llaves.*

2. **Desactivar o restablecer Licencia local**:
   Elimina las credenciales de licencia activas del Keyring local para pruebas de desarrollo o soporte técnico.
   ```bash
   python reset_licencia.py
   ```

---

## 📊 Estructura del CSV
El archivo CSV cargado en la aplicación debe contener exactamente las siguientes columnas (el orden de las columnas es indiferente):

| Columna | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `email` | Correo electrónico del destinatario | `usuario@empresa.com` |
| `id_archivo` | Nombre exacto del PDF a cifrar y enviar (dentro del directorio de PDFs) | `factura_001.pdf` |
| `id_servicio` | Identificador del servicio (se usará en el asunto dinámico) | `FAC-901` |
| `cedula` | Documento de identidad (clave base para abrir el PDF) | `12345678` |

---

## 🏗️ Empaquetado para Distribución (.exe)
Para compilar la aplicación a un ejecutable portable de Windows utilizando PyInstaller:
```bash
pyinstaller Envio_Masivo_Seguro.spec
```
El archivo ejecutable resultante se ubicará en la carpeta `dist/`.

## 📀 Generar Instalador Windows (Inno Setup)
Para generar el instalador formal con asistente de instalación, accesos directos y desinstalador:

1. Compilar el ejecutable con PyInstaller (paso anterior).
2. Generar el instalador con Inno Setup 6:
   ```bash
   iscc installer.iss
   ```
El instalador resultante se ubicará en `dist/installer/SEMS_Pro_Setup_1.0.1.exe`.
