# Reporte de Seguridad y Mitigación: Envíos Masivos con Gmail
**Proyecto:** Envió Masivo Seguro (SEMS Pro)  
**Documento de Control y Garantía:** `pdfs_uy.md`  
**Estado:** Implementado y Mitigado  

---

## 1. ¿Qué pasó? (El Incidente de Bloqueo)

Durante las pruebas iniciales de envío masivo utilizando cuentas estándar de Gmail (`@gmail.com`), la cuenta del remitente sufrió un **bloqueo temporal / suspensión** por parte de Google. 

### Análisis Técnico del Incidente:
* **Causa Raíz:** El motor del software ejecutaba envíos en hilos concurrentes en paralelo sin ningún tipo de espaciamiento temporal (*throttling*). Esto provocaba que decenas de conexiones SMTP y envíos de correo se completaran en fracciones de segundo.
* **Mecanismo de Detección de Google:** Los filtros automáticos de Gmail identificaron este patrón de ráfaga masiva y concurrente como una anomalía de seguridad. Lo catalogaron bajo la alerta **"Uso Inusual" (*Unusual Usage*)** o comportamiento automatizado sospechoso de spam (bots), lo cual desencadenó el bloqueo preventivo del acceso SMTP de la cuenta para proteger la infraestructura y evitar spam saliente.

---

## 2. ¿Qué se hizo? (La Mitigación Implementada)

Para neutralizar este riesgo de forma definitiva y garantizar la continuidad operativa, se diseñó e implementó un sistema de **regulación de velocidad SMTP (*Throttling*)** que permite espaciar los envíos de manera inteligente.

### Cambios de Ingeniería Realizados:
1. **Persistencia en Configuración (`src/config/config_manager.py`):**
   * Se incorporó el parámetro `"send_delay"` en la estructura de configuración por defecto del sistema (con un valor base recomendado de `2` segundos).
   * Se modificó el guardado del archivo `config.json` para dar soporte persistente a este valor.

2. **Controlador del Flujo de Trabajo (`src/core/workflow_orchestrator.py`):**
   * Se integró la lectura dinámica del parámetro `send_delay` de la configuración.
   * Se inyectó el retardo dentro de la lógica concurrente de los hilos de trabajo (`_process_chunk_worker`).
   * Se implementó una suspensión temporal activa (`time.sleep(send_delay)`) tras cada envío exitoso de correo electrónico, suavizando la carga del servidor de salida de forma lineal.

3. **Panel de Control UI (`src/ui/app.py` y `src/ui/views/config_view.py`):**
   * Se creó la variable reactiva en CustomTkinter `self.config_delay`.
   * Se integró un selector de tipo menú desplegable (`CTkOptionMenu`) en la pestaña de configuración bajo la etiqueta **"Retardo entre Envíos (s)"**, permitiendo al operador elegir retardos entre `0` (sin retardo) y `10` segundos de manera visual.
   * Se conectó este menú al guardado directo de la configuración de la aplicación.

---

## 3. ¿Qué se debe hacer? (Garantía para el Cliente Corporativo)

Dado que tu cliente operará con **Gmail Corporativo (Google Workspace)**, cuenta con una infraestructura más robusta pero regida por las mismas políticas anti-spam básicas de Google. Para garantizar una operación 100% segura, libre de bloqueos y con máxima entregabilidad, se debe implementar el siguiente protocolo técnico:

### Paso 1: Configurar el Retardo Óptimo en la Aplicación
> [!IMPORTANT]
> **Recomendación de Uso Obligatorio:**
> Para envíos masivos corporativos, el cliente **debe configurar el "Retardo entre Envíos" en un rango de 2 a 5 segundos** desde la pestaña de configuración del software. Esto asegura un flujo continuo, profesional y seguro que Google Workspace no catalogará como un ataque de spam automatizado.

### Paso 2: Autenticación Correcta del Dominio Corporativo
Para que los correos no solo salgan sin bloquear la cuenta, sino que además lleguen con éxito a la **Bandeja de Entrada** (y no a la carpeta de Spam) de los destinatarios, el departamento de TI del cliente debe asegurar la correcta configuración de los registros DNS de su dominio corporativo (ej. `tuempresa.com`):

1. **SPF (Sender Policy Framework):**
   * Un registro TXT en el DNS del dominio que autoriza a Google a enviar correos en su nombre.
   * *Ejemplo de Registro TXT:* `v=spf1 include:_spf.google.com ~all`
2. **DKIM (DomainKeys Identified Mail):**
   * Añade una firma criptográfica a las cabeceras de cada correo, garantizando que el mensaje no ha sido alterado en tránsito. Se genera desde la consola de administración de Google Workspace.
3. **DMARC (Domain-based Message Authentication, Reporting, and Conformance):**
   * Política que define qué hacer si el correo no supera las pruebas de SPF o DKIM.
   * *Ejemplo de Registro TXT Inicial:* `v=DMARC1; p=none; rua=mailto:dmarc-reports@tuempresa.com`

### Paso 3: Uso de Contraseñas de Aplicación
* Si el correo del cliente tiene activa la **Verificación en Dos Pasos (2FA)** (lo cual es altamente recomendable por seguridad corporativa), no se debe utilizar la contraseña maestra de acceso en el software.
* En su lugar, el cliente debe ingresar a la configuración de seguridad de su cuenta Google, ir a la sección **"Contraseñas de aplicación"**, generar una clave de 16 dígitos exclusiva para el software y configurarla en la aplicación.

### Paso 4: Higiene de Datos
* Evitar enviar correos a direcciones inexistentes o con errores sintácticos severos. Un alto índice de rebotes (*bounce rate*) daña severamente la reputación del dominio corporativo.
* Afortunadamente, el software cuenta con un **validador de correos integrado con corrección automática de typos comunes** (ej. corregir automáticamente `@gmial.com` a `@gmail.com`), lo cual disminuye este riesgo significativamente de forma pasiva.

---

## 4. Bitácora de Refactorización de Arquitectura: Desacoplamiento de Coordinación

Como parte del compromiso por alcanzar un estándar de excelencia técnica absoluta (Punto 3 de la lista de pendientes), se ejecutó la separación de la lógica de coordinación de flujos de la interfaz de usuario en la ventana principal.

### Detalles de la Reestructuración:
* **Problema Original:** La clase visual principal `App` (`src/ui/app.py`) acumulaba múltiples responsabilidades: construir y navegar los contenedores gráficos, inicializar y validar flujos de envío, gestionar las variables de conteo de reintentos, y configurar los diálogos de resultados. Esto sobrecargaba la clase y reducía la modularidad.
* **Solución Implementada (Patrón MVC / Presenter):**
  1. Se creó un controlador dedicado: **`WorkflowController`** (`src/ui/controllers/workflow_controller.py`).
  2. Se encapsuló en este controlador el estado local de reintentos (`_retry_count`, `MAX_RETRIES`), el disparo de la orquestación en segundo plano (`execute_workflow`), y la inicialización e interacción con el modal de resultados fallidos (`show_results_modal`).
  3. Se modificó `app.py` para instanciar al controlador al arrancar la sesión, delegando a él la ejecución de la orquestación mediante `self.workflow_controller.start_process()`.
* **Beneficio para el Cliente:** Esta arquitectura modular garantiza que cualquier actualización futura en la lógica de despacho, reintentos o control de errores se pueda realizar de forma totalmente aislada, sin afectar ni comprometer la visualización de la interfaz ni arriesgar la estabilidad del sistema gráfico.

---

## 5. Bitácora de Pruebas Unitarias Automatizadas y Seguridad

Como parte del compromiso por alcanzar un estándar de excelencia absoluta (Punto 1 de la lista de pendientes), se desarrolló e integró un suite de pruebas unitarias automatizadas nativas para certificar de forma aislada la seguridad, robustez y calidad de los motores principales de la aplicación.

### Detalle de las Pruebas Implementadas:
1. **Validación de Destinatarios ([test_email_validator.py](file:///c:/Users/johns/proyectos/cript/tests/test_email_validator.py)):**
   * Valida formatos estándar y rechaza aquellos con estructura inválida (RFC 5322).
   * Verifica la detección y corrección automática de typos de dominio comunes (ej. `@gmial.com` -> `@gmail.com`).
   * Evalúa la resolución DNS/MX (con timeouts estrictos de 2 segundos) y la tolerancia defensiva a caídas temporales de red para evitar falsos negativos en el flujo de envío del cliente.
   * Comprueba que los envíos en lote agrupen correctamente los correos según su estado de validez.
2. **Cifrado y Borrado de Archivos ([test_pdf_crypto.py](file:///c:/Users/johns/proyectos/cript/tests/test_pdf_crypto.py)):**
   * Verifica que el cifrado AES-256 se aplique correctamente al PDF y restrinja su visualización si no se ingresa la clave asignada.
   * Valida el comportamiento ante errores (PDFs rotos o archivos inexistentes).
   * Certifica el protocolo de **Borrado Seguro Anti-forense** (`secure_cleanup`), el cual sobrescribe físicamente el PDF con bytes aleatorios en disco mediante buffers forzados (`fsync`) antes de ejecutar su eliminación física de manera garantizada mediante bloques `finally`.
3. **Robustez y Seguridad del Orquestador ([test_workflow_orchestrator.py](file:///c:/Users/johns/proyectos/cript/tests/test_workflow_orchestrator.py)):**
   * Valida la sanitización automática y eliminación de caracteres no seguros en nombres de archivo (ej. `doc<>|:?*#1.xyz` -> `doc_______1.xyz.pdf`).
   * Valida y certifica que los ataques de inyección de rutas (**Path Traversal**) tales como `../../etc/passwd` sean bloqueados por el filtro perimetral de resolución de rutas reales (`os.path.realpath`), impidiendo la lectura fuera del directorio permitido, anulando el envío por SMTP y marcando de manera segura la fila con error en el historial.

### Instrucciones para la Ejecución de Pruebas:
Para correr la suite de pruebas unitarias de manera nativa sin requerir instalar dependencias externas, ejecuta el siguiente comando desde la consola en la raíz del proyecto:
```powershell
python -m unittest discover -s tests -v
```
Todas las pruebas unitarias pasan con éxito, garantizando la robustez y resiliencia del aplicativo para producción.


