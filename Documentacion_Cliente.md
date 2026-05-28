# SEMS Pro — Sistema de Envío Masivo Seguro
### Ficha Técnica y Comercial — v2.1

---

## 1. Resumen Ejecutivo

**SEMS Pro** es una solución de software de escritorio diseñada para la **distribución masiva y segura de documentos confidenciales** (nóminas, resultados médicos, informes financieros, contratos, etc.).

Su diseño permite que un operador sin conocimientos técnicos envíe cientos o miles de documentos PDF protegidos individualmente, garantizando que solo el destinatario legítimo pueda abrir su archivo.

> **Propuesta de Valor:** Elimina el riesgo legal y operativo de enviar información sensible por correo electrónico sin protección, cumpliendo estrictamente con la **Ley 1581 de 2012 (Habeas Data)** y estándares internacionales de cifrado.

---

## 2. ¿Cómo Funciona?

El flujo operativo ha sido diseñado para completarse en **menos de 5 minutos**, sin importar el volumen de documentos:

| Paso | Acción | Tiempo Estimado |
|------|--------|-----------------|
| **1** | El administrador configura sus credenciales de correo y selecciona su proveedor (Gmail, Outlook, Yahoo, etc.) desde un menú desplegable. | Una sola vez |
| **2** | Carga un archivo Excel/CSV con los datos de los destinatarios (correo, cédula, nombre del archivo PDF). | 30 segundos |
| **3** | Selecciona la carpeta donde están los archivos PDF. | 10 segundos |
| **4** | Presiona **"Iniciar Proceso"**. El sistema cifra, envía y limpia automáticamente. | Automático |

### Gestión de Errores
Si un archivo falta o un correo no se puede enviar, el sistema **no se detiene**. Al finalizar genera un reporte visual con el detalle de los envíos fallidos para que el operador pueda realizar las correcciones necesarias en el archivo origen de datos.

---

## 3. Capas de Seguridad

SEMS Pro implementa un modelo de seguridad de **5 capas** diseñado bajo los principios de *"Privacy by Design"* (Privacidad desde el Diseño):

### 🔒 Capa 1 — Procesamiento 100% Local
Los documentos **nunca se suben a la nube** ni pasan por servidores de terceros. Todo el cifrado y la preparación ocurren dentro de la computadora del emisor. Esto elimina la exposición a hackeos de plataformas externas.

### 🔐 Capa 2 — Cifrado Individual AES-256
Cada documento PDF es cifrado individualmente con el algoritmo **AES-256** (Advanced Encryption Standard a 256 bits), el mismo estándar utilizado por el gobierno de los Estados Unidos para proteger información clasificada como "Top Secret". Un archivo protegido con AES-256 es **matemáticamente imposible de vulnerar** mediante fuerza bruta.

### 🔑 Capa 3 — Contraseña Única por Destinatario
La contraseña de cada PDF es la **cédula de identidad** del destinatario. Esto significa que:
- Si un correo llega a la persona equivocada por error de digitación, **no podrá abrir el archivo**.
- Si un hacker intercepta el correo, el PDF es completamente **inútil** sin conocer el número de identificación.

### 🌐 Capa 4 — Canal de Transmisión Cifrado (TLS)
La conexión entre el software y el servidor de correo se establece a través de un **túnel TLS** (Transport Layer Security), impidiendo que cualquier intermediario (proveedores de internet, redes Wi-Fi públicas) pueda leer los correos en tránsito.

### 🧹 Capa 5 — Destrucción Segura y Zero-Footprint (RAM)
El sistema opera bajo un estricto modelo de **"Zero-Footprint"**. Los lotes e historiales de auditoría se conservan de manera efímera únicamente en la memoria RAM y se destruyen de forma irrevocable al cerrar la aplicación. Además, una vez enviado cada correo, el sistema **sobrescribe los archivos temporales con datos aleatorios de alta entropía** antes de eliminarlos físicamente del disco. Esta técnica anti-forense garantiza que no queden rastros recuperables de los documentos procesados en el almacenamiento persistente.

---

## 4. Enmascaramiento Activo de PII en Pantalla

Para evitar la fuga de información sensible mediante capturas de pantalla involuntarias, espionaje físico ("shoulder surfing") o acceso no autorizado visual, SEMS Pro aplica un control dinámico de enmascaramiento en la interfaz de usuario:

- **Vista Previa de Correo**: Oculta la dirección real de la cuenta de remitente del operador mostrando únicamente `"Cuenta SMTP configurada"`. Adicionalmente, enmascara la dirección del destinatario (ej. `johnsod8729@gmail.com` se muestra como `j***9@gmail.com`), garantizando el tratamiento de datos personales de terceros de conformidad con la Ley 1581 de 2012.
- **Ajustes SMTP**: El campo "Correo Remitente" implementa un enmascaramiento dinámico interactivo. Al cargar la configuración o al perder el foco (`FocusOut`), el correo se muestra enmascarado. Al hacer clic o enfocar el campo para editarlo (`FocusIn`), se revela el correo real de forma temporal, permitiendo una gestión cómoda y segura.
- **Búsqueda en Historial**: Toda búsqueda de registros y auditoría se gestiona a través de hashes criptográficos robustos **HMAC-SHA256**, evitando exponer datos PII en texto plano durante las consultas de auditoría.

---

## 5. Almacenamiento Seguro de Credenciales

Las contraseñas de correo electrónico del administrador **no se guardan en archivos de texto** ni en bases de datos locales. SEMS Pro utiliza el **Administrador de Credenciales de Windows** (Windows Credential Manager), la misma bóveda de seguridad que utiliza el sistema operativo para proteger las contraseñas de inicio de sesión.

---

## 6. Compatibilidad

| Característica | Detalle |
|---|---|
| **Sistema Operativo** | Windows 10 / 11 (64 bits) |
| **Proveedores de Correo** | Gmail, Outlook/Hotmail, Yahoo, Zoho, iCloud |
| **Instalación** | No requiere instalación. Ejecutable portátil (.exe) |
| **Dependencias** | Ninguna. El software es autocontenido |
| **Volumen** | Sin límite técnico de envíos por sesión |

---

## 7. Tecnologías Certificadas

SEMS Pro ha sido desarrollado utilizando tecnologías de grado industrial:

| Componente | Tecnología | Propósito |
|---|---|---|
| Motor de Cifrado | **AES-256 (PDF 2.0 / R6)** | Protección de documentos |
| Transporte Seguro | **TLS 1.2+** | Cifrado del canal de comunicación |
| Almacén de Credenciales | **Windows Credential Manager** | Protección de contraseñas del sistema |
| Protección de Pantalla y Logs | **Ofuscación Activa de PII** | Enmascaramiento dinámico de correos en UI y archivos de log |
| Limpieza de Datos | **Overwrite + Delete** | Destrucción anti-forense de archivos temporales |

---

## 8. Cumplimiento Normativo

| Normativa | Cumplimiento |
|---|---|
| **Ley 1581 de 2012** (Habeas Data - Colombia) | ✅ Datos personales cifrados y enmascarados activamente en pantalla e historial efímero sin almacenamiento persistente. |
| **Ley 1273 de 2009** (Delitos Informáticos - Colombia) | ✅ Medidas técnicas de protección física y lógica implementadas. |
| **Principio de Minimización de Datos** | ✅ Los logs e interfaces enmascaran de forma dinámica los correos electrónicos. |
| **OWASP Top 10** | ✅ Validación estricta de entrada, mitigación de Path Traversal, gestión segura de secretos. |

---

## 9. Soporte Técnico y Actualizaciones

| Servicio | Detalle |
|---|---|
| **Puesta en Marcha** | Sesión de configuración y transferencia de conocimiento (25 min) |
| **Soporte** | Asistencia técnica remota para resolución de incidentes |
| **Actualizaciones** | Parches de seguridad y mejoras funcionales según plan contratado |
| **Auditoría** | Código fuente disponible para revisión por el equipo de seguridad informática del cliente, bajo acuerdo de confidencialidad (NDA) |

---

## 10. Contacto

**Desarrollado por:** John R.  
**Correo:** johnsod8729@gmail.com  
**Repositorio Técnico (bajo NDA):** Disponible previa solicitud.

---

*Documento confidencial. Prohibida su reproducción total o parcial sin autorización expresa.*
