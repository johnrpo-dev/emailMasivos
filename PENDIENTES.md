# Pendientes y Mejoras Futuras - Envió Masivo Seguro (SEMS Pro)

Este documento registra el estado de las mejoras identificadas y desarrolladas para el software. 

¡Todas las mejoras prioritarias planificadas han sido implementadas con éxito!

## 🚀 Mejoras Implementadas

### 1. Implementación de Multithreading (Envío en Paralelo)
*   **Estado:** `[Completado]`
*   **Solución:** Distribución del lote de envíos en un pool de hilos (`ThreadPoolExecutor`) con conexiones SMTP concurrentes y seguras.
*   **Impacto:** Reducción del tiempo total de procesamiento en más del 70% sin saturar el servidor.

### 2. Optimización del Borrado Seguro
*   **Estado:** `[Completado]`
*   **Solución:** Traslado del borrado físico y aleatorio de archivos temporales (`PDFCrypto.secure_cleanup`) a hilos secundarios independientes, evitando retrasos o bloqueos en la cola principal.

### 3. Historial de Envíos Efímero en RAM (Zero-Footprint por Diseño)
*   **Estado:** `[Completado]`
*   **Solución:** Registro exclusivo de la trazabilidad detallada en estructuras volátiles de RAM (`self.session_batches`) con ofuscación activa de PII (enmascaramiento de email, ofuscación parcial de cédula, y remoción de rutas absolutas mediante `os.path.basename` para prevenir Path Traversal). La memoria se libera de forma inalterable al cerrar el proceso. La trazabilidad histórica duradera se delega en la carpeta "Enviados" del proveedor SMTP (Gmail).

### 4. Vista Previa (Preview)
*   **Estado:** `[Completado]`
*   **Solución:** Botón interactivo **🔍 VISTA PREVIA** en el panel de control principal, que muestra un desglose formateado del remitente, destinatario, asunto y cuerpo dinámico para el primer registro cargado en el archivo CSV antes de procesar el lote.

### 5. Notificaciones de Escritorio
*   **Estado:** `[Completado]`
*   **Solución:** Envío automatizado y seguro de notificaciones en el sistema operativo Windows a través de PowerShell cuando el proceso principal finaliza (activo cuando la ventana de la aplicación se encuentra minimizada).

### 6. Desacoplamiento Arquitectónico (Orquestador de Negocio y Concurrencia)
*   **Estado:** `[Completado]`
*   **Solución:** Extracción completa de la lógica de cifrado, SMTP, pre-validación de correos y pool de hilos (`ThreadPoolExecutor`) hacia el componente orquestador `WorkflowOrchestrator`. La interfaz gráfica en `app.py` actúa como una vista pura y actualiza sus controles mediante llamadas seguras e independientes de hilos (`self.after(0, ...)`).

---
*Última actualización: 2026-05-23*

## 🚀 Mejoras Estructurales y de Estabilidad (Sprint 3)
¡Todas las tareas arquitectónicas y de estabilidad del Sprint 3 han sido completadas con éxito!

### 1. Extracción de `show_results_modal`
*   **Estado:** `[Completado]`
*   **Solución:** Se extrajo el diálogo a una clase pura e independiente `ResultsModal` en `src/ui/modals/results_modal.py`, comunicándose de forma desacoplada con el controller principal usando callbacks.

### 2. Estandarización a Carpeta de Modales (`modals/`)
*   **Estado:** `[Completado]`
*   **Solución:** Se agruparon todos los diálogos en el directorio semánticamente correcto `src/ui/modals/`, removiendo la carpeta `components/`.

### 3. Homologación de Nombres (`lote_modal.py`)
*   **Estado:** `[Completado]`
*   **Solución:** Se renombró `history_detail_modal.py` a `lote_modal.py` para coincidir semánticamente con la definición del diseño propuesto.

### 4. Minimización de `app.py`
*   **Estado:** `[Completado]`
*   **Solución:** Limpieza de clases auxiliares de `app.py`, reduciendo su tamaño a escasas **225 líneas** y limitando su responsabilidad únicamente al enrutamiento de vistas y ciclo de vida.

### 5. Sanitización Robustecida de Nombres de Archivos
*   **Estado:** `[Completado]`
*   **Solución:** Modificación del regex de sanitización en el orquestador a `r'[^\w.\- ]'` permitiendo procesar archivos con espacios en blanco en su nombre de forma normal.

### 6. Localización e Integridad de Notificaciones
*   **Estado:** `[Completado]`
*   **Solución:** Ampliación del set de sanitización de notificaciones para admitir caracteres acentuados del español y la letra "ñ" (`áéíóúüñÁÉÍÓÚÜÑ`), asegurando la correcta ortografía en las alertas de Windows.

### 7. Prevención de Concurrencia en Historial
*   **Estado:** `[Completado]`
*   **Solución:** Aplicación de copias superficiales rápidas `list(lote.get("envios", []))` al iterar en caliente sobre el historial desde el hilo principal de la interfaz visual, anulando riesgos de `RuntimeError` por modificaciones paralelas.

## ⏳ Próximos Pasos (Mejoras a Futuro para Nivel 9.5/10)

Estas tareas han sido identificadas en la evaluación final como las únicas deudas técnicas abiertas para elevar el proyecto al estándar de excelencia absoluta:

### 1. Suite de Pruebas Unitarias Automatizadas
*   **Estado:** `[Pendiente]`
*   **Descripción:** Implementar un suite de pruebas automáticas (utilizando `pytest` o `unittest`) para validar el motor principal de forma aislada: sanitización de nombres de archivo y path traversal en `WorkflowOrchestrator`, cifrado robusto en `PDFCrypto`, y lógica de typos sintácticos en `email_validator.py`.
*   **Meta:** Eliminar la dependencia de verificaciones exclusivamente manuales y anular el riesgo de regresiones ante cambios en dependencias.

### 2. Documentación Formal de Retención de Datos (`PRIV-001`)
*   **Estado:** `[Pendiente]`
*   **Descripción:** Redactar y formalizar un documento descriptivo de protección de la información (`PRIVACY.md` o anexo técnico en el repositorio) que detalle el modelo Zero-Footprint implementado: retención efímera en RAM, ofuscación activa de PII y borrado físico seguro anti-forense.
*   **Meta:** Cumplir formalmente con normativas de protección de datos personales ante auditorías de cumplimiento.

### 3. Desacoplamiento de la Coordinación de Flujo en `app.py`
*   **Estado:** `[Pendiente]`
*   **Descripción:** Migrar la inicialización del flujo de reintentos y el método `_execute_workflow` desde la ventana principal a un presentador o controlador de UI dedicado (`WorkflowController` o similar).
*   **Meta:** Limitar la responsabilidad de `app.py` únicamente a la construcción de contenedores y navegación de CustomTkinter.

******************************************************************


Rol: Actúa como un Lead Application Security Engineer y Red Teamer Senior con más de 15 años de experiencia rompiendo sistemas críticos en entornos financieros y gubernamentales. Tu enfoque no es teórico; es puramente analítico, implacable, escéptico y técnico. No asumas que el código es seguro, asume que está roto y que tu trabajo es encontrar el hilo suelto para colapsar la arquitectura.

Contexto Técnico del Target:
- Stack Tecnológico: [Especificar: Ej. Node.js/Express, SQLite, JavaScript ES6]
- Arquitectura/Propósito: [Especificar: Ej. Backend de una plataforma SaaS de gestión de entregas y logística]
- Modelo de Confianza: Se asume que los inputs de red y de la base de datos están potencialmente comprometidos.

Instrucciones de Análisis (Vector de Ataque):
No me des definiciones de diccionario sobre qué es OWASP. Analiza el código fuente proporcionado buscando fallas de nivel arquitectónico, lógico y de implementación. Debes enfocarte prioritariamente en:

1. Fallas en la Lógica de Negocio y Control de Flujo:
   - Condiciones de carrera (Race Conditions) en operaciones críticas (ej. transacciones, actualizaciones de estado).
   - Evasión de flujo (Bypasses): ¿Cómo puede un atacante saltarse pasos del proceso lógico manipulando variables, estados o IDs?
   - Fallas de consistencia: Manejo de transacciones en la base de datos que queden a medias ante errores forzados.

2. Autorización Rompimiento a Nivel de Objeto/Función (BOLA / BFLA):
   - Verifica minuciosamente cómo se validan las relaciones de propiedad de los recursos. ¿Un ID de recurso (como el ID de un pedido o usuario) es directamente modificable en los parámetros o payload sin que el backend valide que pertenece al token/sesión activa?

3. Inyecciones Exóticas y Sanitización Deficiente:
   - No te limites a SQLi básico. Busca inyecciones en queries dinámicas, manejo inadecuado de ORMs/Query Builders, inyección de comandos o manipulación de rutas de archivos (Path Traversal).

4. Gestión de Estado, Criptografía y Secretos:
   - Hardcoding de entropía débil (claves, sales, tokens).
   - Implementación manual de algoritmos criptográficos o uso de funciones de hash obsoletas.
   - Fuga de memoria o de datos sensibles en logs de error expuestos al cliente.

Reglas Estrictas de Respuesta:
1. Sin preámbulos, cumplidos ni conclusiones corporativas. Ve directo al grano.
2. Si un riesgo es teórico porque depende de la infraestructura, indícalo claramente, pero no lo descartes.
3. Si el código implementa una defensa robusta, descríbela técnicamente y justifica por qué es segura.

Formato Obligatorio para cada Hallazgo:

## [ID_HALLAZGO] [NIVEL DE RIESGO: CRÍTICO | ALTO | MEDIO | BAJO] - [Nombre Técnico del Fallo]
- **Ubicación:** [Archivo, función, líneas de código afectadas]
- **Análisis del Vector:** Explicación técnica y profunda de la mecánica del fallo. Por qué la lógica actual falla bajo estrés o manipulación adversarial.
- **Explotación (PoC Teórica):** Describe el payload exacto, la petición HTTP o la secuencia de acciones que un atacante ejecutaría para explotar la vulnerabilidad.
- **Remediación de Grado de Producción:** Código corregido aplicando principios de "Securidad por Diseño". Debe sustituir la sección vulnerable por completo, utilizando las librerías nativas o de terceros estándar más seguras.