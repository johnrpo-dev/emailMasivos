# Bitácora de Cambios — SEMS Pro

---

## 2026-05-27

### 🐛 Bug: Botones de corrección y reintento eliminados por error
- **Commit causante:** `e949dfb` — *"ui: redesign results modal header, KPI cards and shrink-wrap suggestion frame to look extremely premium"*
- **Archivo afectado:** `src/ui/modals/results_modal.py`
- **Descripción:** Durante el rediseño visual del modal de resultados, se eliminaron accidentalmente los botones condicionales **"✨ Corregir y Reintentar"** y **"🔄 Reintentar Fallidos"**. Los callbacks (`on_retry`, `on_correct_and_retry`) seguían siendo recibidos por el constructor pero ya no se conectaban a ningún elemento de la UI.
- **Impacto:** Los usuarios no podían corregir typos de correo ni reintentar envíos fallidos desde el reporte de resultados.
- **Corrección:** Botones restaurados manteniendo el estilo visual del rediseño.

### ⚙️ Ajuste final: Eliminación del selector de Delay en la UI de Configuración (manteniendo su lógica interna) y preservación de los botones de Reintento
- **Archivos afectados:** `src/ui/views/config_view.py`, `src/ui/modals/results_modal.py`
- **Descripción:** Tras la clarificación del usuario, se comprendió que el elemento a remover de la UI era el control/botón (dropdown) del **Retardo de envíos (delay)** para que el cliente final no pueda cambiarlo, pero **manteniendo intacta la lógica interna del retardo de 2 segundos** (y los valores guardados en config). Los botones condicionales **"✨ Corregir y Reintentar"** y **"🔄 Reintentar Fallidos"** del modal de resultados deben permanecer completamente funcionales.
- **Cambios realizados:**
  1. Se restauraron y conservaron intactos los botones **"✨ Corregir y Reintentar"** y **"🔄 Reintentar Fallidos"** en el reporte de resultados (`ResultsModal`).
  2. Se eliminó de la interfaz de usuario (`ConfigView`) la opción visual de **Retardo entre Envíos (s)**.
  3. Se garantizó que la propiedad interna de retardo (`send_delay`, cargada por defecto en 2 segundos o el valor configurado previamente) siga persistiendo y aplicando su tiempo de espera sleep en el orquestador durante los envíos masivos.

### 🌐 Ocultación del selector de Proveedor SMTP en la UI de Configuración
- **Archivo afectado:** `src/ui/views/config_view.py`
- **Descripción:** Dado que este cliente en particular utilizará **Gmail** de forma fija, se removió de la interfaz gráfica el dropdown de **"Proveedor de Correo"** para evitar manipulaciones innecesarias, pero **se preservó intacto todo el código interno de app y lógica SMTP**. Esto permite que en el futuro o para otros clientes que requieran otro proveedor, la funcionalidad pueda volver a habilitarse en la UI de forma inmediata.
- **Cambios realizados:**
  1. Se eliminó visualmente la etiqueta y el control de menú desplegable de *Proveedor de Correo* de la tarjeta de credenciales de `ConfigView`.
  2. El campo *Nombre del Remitente* se colocó en la fila 2 de la rejilla para ocupar el espacio liberado y mantener el diseño limpio.
  3. Toda la infraestructura interna que procesa múltiples hosts y puertos sigue cargando y guardando correctamente el proveedor por defecto.

### 🔄 Ampliación del Límite de Reintentos de Envío por Seguridad
- **Archivo afectado:** `src/ui/controllers/workflow_controller.py`
- **Descripción:** El límite de seguridad original de 2 reintentos máximos resultaba muy restrictivo para lotes con varios fallos. Se amplió para dar mayor flexibilidad de recuperación en caliente.
- **Cambios realizados:**
  1. Se incrementó la constante `MAX_RETRIES` de `2` a `10` en `WorkflowController`. Esto permite a los usuarios realizar hasta 10 intentos consecutivos de reenvío de registros fallidos antes de tener que reiniciar el flujo.

### 🖼️ Incorporación de Logo de Empresa Dinámico Local e Inline (100% Seguro)
- **Archivos afectados:** `src/ui/views/config_view.py`, `src/config/config_manager.py`, `src/ui/app.py`, `src/core/email_service.py`
- **Descripción:** Por motivos de seguridad y para evitar vulnerabilidades de inyección o secuestro de URLs remotas, se implementó una solución de logo local embebido. La imagen del logo se adjunta de forma cifrada/inline (Content-ID/CID) en el cuerpo del correo, funcionando de forma 100% offline y segura sin realizar peticiones HTTP a servidores externos.
- **Cambios realizados:**
  1. **Selector de Archivo en la UI:** Se reemplazó el campo de URL de logo por una entrada con un botón interactivo **"📁 Buscar"** en la sección *Card Plantilla* de la UI, permitiendo buscar y seleccionar archivos de imagen locales (`.png`, `.jpg`, `.jpeg`, etc.) a través de un diálogo del sistema operativo.
  2. **Persistencia de Ruta Local:** Se configuró el almacenamiento del campo `logo_path` con la ruta absoluta del archivo local en el archivo `config.json`.
  3. **Adjunto Inline Seguro (Content-ID):** En `email_service.py`, al procesar el correo:
     - Se leen los bytes del archivo local de logo si está configurado y existe.
     - Se adjunta de manera inline como una sub-parte `MIMEImage` con una cabecera `Content-ID: <logo_image>`.
     - En la plantilla HTML se referencia de manera segura como `<img src="cid:logo_image" />`, evitando la descarga de recursos remotos externos y garantizando inmunidad a inyecciones.
     - Se mantiene el fallback automático que muestra el Nombre del Remitente si no se configura un logo.

---

### ✨ Mejora: Entregabilidad de correos (anti-spam)
- **Archivo modificado:** `src/core/email_service.py`
- **Cambios realizados:**
  1. **Nombre de remitente visible:** El header `From` ahora muestra `"SEMS Pro" <correo@gmail.com>` en lugar del correo crudo, usando `formataddr`.
  2. **Correo HTML + texto plano (multipart/alternative):** La estructura del mensaje cambió de `MIMEMultipart()` a `MIMEMultipart('mixed')` con un sub-bloque `multipart/alternative` que incluye:
     - `text/plain` — versión básica para clientes de correo sin soporte HTML.
     - `text/html` — plantilla profesional con header indigo, tipografía limpia y footer institucional.
- **Motivo:** Los correos enviados desde una cuenta Gmail nueva caían en la carpeta de spam del receptor. Estas mejoras reducen la probabilidad de ser clasificados como spam por los filtros de los proveedores.
