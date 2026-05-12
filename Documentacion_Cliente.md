# Documentación Técnica y Operativa
## Sistema de Envío Masivo Seguro (SEMS)

---

### 1. Resumen Ejecutivo
El **Sistema de Envío Masivo Seguro** es una aplicación de escritorio diseñada a la medida para resolver el problema de distribución masiva de documentos altamente sensibles (ej. resultados médicos, nóminas, informes financieros). Su objetivo principal es garantizar que la información confidencial llegue a su destinatario legítimo, aplicando los más altos estándares de cifrado y privacidad, sin depender de servidores de terceros en la nube.

---

### 2. ¿Cómo funciona la plataforma? (Flujo Operativo)
La herramienta fue diseñada con un enfoque en la usabilidad y la eficiencia (UX/UI), permitiendo a operadores no técnicos realizar envíos masivos en pocos clics:

1. **Configuración de Plantilla:** A través de una interfaz gráfica moderna, el administrador ingresa sus credenciales de correo (mediante un token de seguridad de aplicación, protegiendo su contraseña real) y define la plantilla del asunto y cuerpo del correo.
2. **Carga de Datos:** El usuario carga un archivo Excel/CSV estandarizado que contiene los correos electrónicos, el nombre del documento PDF a enviar, y la cédula del destinatario.
3. **Procesamiento Masivo Automatizado:** Al presionar "Iniciar", el sistema procesa miles de registros de forma secuencial. La interfaz muestra una barra de progreso en tiempo real.
4. **Sistema de Reintentos Inteligentes:** Si ocurre un error local (ej. se olvidó colocar un PDF en la carpeta), el sistema no se detiene. Al final, genera un reporte detallado. El administrador puede simplemente agregar el archivo faltante y presionar **"Reintentar Fallidos"**. El sistema detecta y procesa *únicamente* esos registros pendientes, evitando enviar correos duplicados (Spam) a los clientes que ya recibieron su documento.

---

### 3. Tecnologías Utilizadas
Para garantizar el rendimiento, la compatibilidad y la seguridad del sistema, se ha desarrollado utilizando una pila tecnológica (Tech Stack) moderna y robusta:

* **Lenguaje Base:** Python 3.10+ (Escogido por su excelente rendimiento en manipulación de datos y cifrado).
* **Interfaz Gráfica:** `CustomTkinter` (Framework de renderizado moderno para una experiencia visual limpia, fluida y escalable).
* **Cifrado y Manipulación PDF:** `Pikepdf` (Librería basada en QPDF, estándar de la industria, que permite inyectar algoritmos criptográficos directamente en la estructura de los PDF).
* **Protocolo de Transmisión:** Librerías nativas SMTP/TLS de Python para conexión directa y segura con servidores de correo institucionales (como Google Workspace/Gmail).
* **Despliegue:** `PyInstaller` (Empaquetamiento del código en un único binario ejecutable `.exe` para Windows, sin necesidad de que el cliente instale dependencias de programación).

---

### 4. Arquitectura de Seguridad (Protección de la Información)
El mayor valor de la herramienta es su blindaje de seguridad, diseñado bajo el principio de "Zero-Knowledge" (Cero Conocimiento) y "Privacy by Design" (Privacidad desde el Diseño). Así protegemos los archivos desde su origen hasta la pantalla del cliente:

#### A. Procesamiento Local (Air-Gapped Logic)
A diferencia de servicios web de envío masivo (como Mailchimp o plataformas de facturación) que requieren subir todos los PDFs de los clientes a la nube de un tercero, **esta aplicación funciona de manera 100% local**. Los archivos crudos jamás abandonan la computadora del emisor. El cifrado ocurre en la memoria local y solo sale de la computadora cuando ya está fuertemente encriptado.

#### B. Cifrado de Grado Militar (AES-256)
Durante la fase de procesamiento, cada PDF individual es reescrito utilizando el algoritmo de cifrado **AES-256** (Advanced Encryption Standard a 256 bits), el estándar de encriptación avalado por el gobierno de EE. UU. para datos "Top Secret" y soportado por la especificación PDF 2.0. Un archivo cifrado con AES-256 es matemáticamente imposible de vulnerar mediante ataques de fuerza bruta en un tiempo de vida humano.

#### C. Llave Dinámica y Única (Protección contra Intercepción)
La contraseña asignada a cada PDF no es genérica ni predecible por atacantes; el sistema utiliza dinámicamente la **Cédula de Identidad** de cada cliente como llave de apertura. 
* **Riesgo Mitigado:** Si, por un error de digitación en la base de datos, un PDF confidencial se envía al correo electrónico de una persona equivocada, o si el correo es interceptado por un hacker, **el archivo es inútil**. Sin conocer el número de identificación exacto del destinatario original, el documento jamás podrá abrirse.

#### D. Transmisión Segura (TLS / En tránsito)
Una vez el archivo es cifrado y atado al correo del destinatario, el sistema negocia una conexión TLS (Transport Layer Security) con el servidor de correo. Esto crea un "túnel" seguro en internet, impidiendo que intermediarios (como proveedores de internet) puedan leer los correos mientras viajan desde la computadora hacia la bandeja de entrada.

#### E. Destrucción Segura de Archivos Temporales
Durante el proceso, el sistema crea versiones cifradas temporales de los PDFs para adjuntarlas al correo. Inmediatamente después de recibir la confirmación de entrega por parte del servidor SMTP, el sistema ejecuta una subrutina de "Secure Cleanup" que elimina y sobreescribe de la memoria física estos archivos temporales, no dejando rastros ni basura digital vulnerable en la computadora.

---

### 5. Transparencia y Auditoría Técnica
Para garantizar la total transparencia sobre el manejo de los datos y certificar las arquitecturas de seguridad mencionadas, el código fuente completo de esta solución está disponible para auditoría.

El equipo técnico o de seguridad informática de la empresa puede revisar el repositorio oficial en el siguiente enlace:
🔗 **[Repositorio de Código - Sistema de Envío Masivo Seguro](https://github.com/johnrpo-dev/emailMasivos)**
