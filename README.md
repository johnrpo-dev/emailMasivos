# SEMS Pro — Sistema de Envíos Masivos Seguros

SEMS Pro es una aplicación de escritorio para Windows diseñada para laboratorios clínicos y organizaciones que necesitan **entregar documentos confidenciales por correo de forma masiva y segura**: cifra localmente cada PDF con AES-256 (PDF 2.0 / R6) usando la cédula del destinatario como clave, y lo envía por SMTP con STARTTLS/SSL.

Construida bajo principios de **Privacidad por Diseño (Privacy by Design)**, con arquitectura de seguridad auditada e interfaz clínica moderna (modo claro/oscuro).

---

## 🚀 Características Clave

* **Cifrado AES-256 local por destinatario**: cada PDF se cifra con la cédula del destinatario, opcionalmente fortalecida con un prefijo/sufijo configurable. La owner-password es aleatoria por envío (el destinatario no puede quitar la protección).
* **Interfaz clínica con modo claro/oscuro**: tema centralizado (`src/ui/theme.py`), componentes reutilizables y diálogos propios; paleta teal sanitaria con contrastes WCAG AA.
* **Validación previa de destinatarios**: formato, typos de dominio (`gmial.com`, `hotmail.con`...) con **corrección automática sugerida**, y verificación DNS de dominios desconocidos — antes de conectar al SMTP.
* **Monitor en tiempo real y reintentos inteligentes**: contadores en vivo, consola de operación estilo terminal, reporte de fallos clasificado (PDF faltante / typo / dominio / SMTP) con reintento y auto-corrección en un clic.
* **Candado de concurrencia**: imposible lanzar dos envíos en paralelo (evita duplicados); los registros recuperados en reintentos se marcan como "Recuperados" en el historial.
* **Historial "Zero-Footprint"**: la trazabilidad de envíos vive solo en RAM durante la sesión, con PII enmascarada y búsqueda por HMAC-SHA256; nada persiste en disco.
* **Seguridad de credenciales**: las credenciales SMTP viven únicamente en el Administrador de Credenciales de Windows (Keyring) y se consultan *just-in-time*; resilientes incluso ante un `config.json` corrupto.
* **Licenciamiento criptográfico (Ed25519)**: firmas asimétricas, fechas UTC-aware, periodo de gracia de renovación, detección de retroceso de reloj con ancla monotónica y latido periódico, y anti-bruteforce en la activación (5 intentos, bloqueo de 5 min).
* **Mitigación de bloqueos SMTP (Throttling global)**: marcapasos compartido entre hilos con retardo configurable desde la UI; reconexión automática ante desconexiones y Message-ID idempotente.
* **Defensa anti-Path Traversal** y sanitización de nombres de archivo del CSV.
* **Logs sin PII**: correos y nombres de archivo enmascarados, cédulas redactadas por filtro automático.

---

## 🛠️ Requisitos Previos

* Python 3.10+ (solo desarrollo; el cliente final usa el instalador)
* Windows (requerido: integración con el Administrador de Credenciales)
* Cuenta de correo habilitada para SMTP con **Contraseña de Aplicación** (Gmail, Outlook/Hotmail, Yahoo, Zoho o iCloud — seleccionables desde la app)

---

## 📦 Instalación y Setup de Desarrollo

1. Clona este repositorio.
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

### Ejecutar la Suite de Pruebas
41 pruebas unitarias cubren sanitización, Path Traversal, validación de dominios y TLDs, cifrado PDF, purga de reintentos, candado de concurrencia, resiliencia de configuración y licencias:
```bash
python -m unittest discover tests -v
```

---

## 💻 Ejecución

```bash
python src/main.py
```

---

## 🧭 Arquitectura

```
src/
├── main.py                  # Arranque: licencia → (activación) → App
├── core/                    # Lógica de negocio (sin dependencias de UI)
│   ├── workflow_orchestrator.py   # Flujo completo en hilos: validar → cifrar → enviar
│   ├── data_manager.py            # Carga y validación del CSV
│   ├── pdf_crypto.py              # Cifrado AES-256 + borrado seguro de temporales
│   ├── email_service.py           # SMTP con TLS estricto (anti STARTTLS-stripping)
│   └── license_manager.py         # Licencias Ed25519, gracia, anti-retroceso de reloj
├── ui/                      # Capa CustomTkinter
│   ├── theme.py                   # Tokens de color/tipografía (fuente única de verdad)
│   ├── components.py              # Card, StatBox, StatusBadge, botones, etc.
│   ├── dialogs.py                 # Diálogos modales temáticos (reemplazan messagebox)
│   ├── app.py                     # Ventana principal, navegación, toggle claro/oscuro
│   ├── views/                     # Home (envíos), Configuración, Historial
│   ├── modals/                    # Activación, Vista Previa, Reporte, Detalle de Lote
│   └── controllers/               # Puente UI ↔ orquestador (callbacks vía after)
├── config/                  # config.json en %APPDATA% + credenciales en Keyring
└── utils/                   # Logger con enmascarado de PII, validador de emails
```

---

## 🔑 Gestión de Licencias (Solo Desarrollador)

1. **Generar una licencia** (clave Base64 firmada; las llaves Ed25519 viven fuera del repo en `%APPDATA%/SEMS_Pro/keys/`, con la llave privada cifrada por passphrase):
   ```bash
   python generar_licencia.py
   ```
   *Si rotas las llaves, actualiza `PUBLIC_KEY_HEX` en `src/core/license_manager.py`.*

2. **Restablecer la licencia local** (pruebas/soporte):
   ```bash
   python reset_licencia.py
   ```

---

## 📊 Estructura del CSV

Columnas requeridas (el orden es indiferente):

| Columna | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `email` | Correo electrónico del destinatario | `usuario@empresa.com` |
| `id_archivo` | Nombre exacto del PDF a cifrar y enviar (dentro del directorio de PDFs) | `resultado_001.pdf` |
| `id_servicio` | Identificador del servicio (se usa en el asunto dinámico) | `LAB-901` |
| `cedula` | Documento de identidad (clave base para abrir el PDF) | `12345678` |

> **Nota de negocio**: un mismo destinatario puede aparecer en varias filas (varios documentos el mismo día, ej. rayos X y audiometría) — recibirá un correo por cada documento. Es el comportamiento esperado.

---

## 🏗️ Empaquetado para Distribución (.exe)

Build onedir (evita falsos positivos de antivirus del modo onefile; UPX desactivado):
```bash
pyinstaller Envio_Masivo_Seguro.spec
```
Resultado: `dist/Envio_Masivo_Seguro/` (ejecutable + `_internal`; deben distribuirse juntos).

## 📀 Generar Instalador Windows (Inno Setup)

1. Compilar con PyInstaller (paso anterior).
2. Generar el instalador:
   ```bash
   iscc installer.iss
   ```
Resultado: `dist/installer/SEMS_Pro_Setup_<versión>.exe` — es el artefacto que se entrega al cliente (instala la app, EULA, accesos directos y desinstalador).
