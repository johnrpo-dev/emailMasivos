# Plan de trabajo — 3 meses

Punto de partida: **v1.1.0** entregada, contrato firmado el 6 de agosto de 2026 con Clínica
Cardio VID, modalidad *Licencia + Soporte Mensual*.

Este plan está alineado con las obligaciones reales del contrato, no con una lista de deseos.

---

## Bloque 0 — Obligación pendiente del contrato

### Licencia perpetua del mes 6

Cumplido el primer semestre de soporte y estando el cliente a paz y salvo, la licencia se vuelve
**perpetua e irrevocable** (cláusula Décima Segunda, segundo). Pero el software exige una clave con
vencimiento: si se dejan de emitir mensualidades, deja de funcionar y se incumpliría ese derecho.

> **Acción:** al consolidar, emitir una **licencia perpetua** (el generador ya tiene esa opción, con
> vencimiento simbólico en 2099). Agendarlo a seis meses de la FECHA DE INICIO, que es el día en que
> el cliente pagó la licencia.

Es la única obligación contractual que hoy el software no puede cumplir sin una acción manual
programada con antelación.

## Qué obliga y qué no obliga el contrato

Distinción que define la naturaleza de todo lo que sigue (cláusula Quinta):

| El soporte mensual SÍ obliga a | El soporte mensual NO obliga a |
| :-- | :-- |
| Atender consultas técnicas | Desarrollar funcionalidades nuevas |
| Corregir errores atribuibles al software | Soporte de hardware, sistema operativo o red |
| Entregar las actualizaciones que se desarrollen | Configurar DNS, SPF, DKIM o DMARC del cliente |
| **Responder en máximo 24 horas hábiles** | Recuperar información por uso indebido |

En consecuencia: **el Mes 1 es obligatorio** (cierra riesgos propios y sostiene el SLA). Los meses
2 y 3 son **discrecionales**: no están obligados por contrato, pero reducen las consultas que sí
hay que atender en 24 horas, y son la base para cobrar desarrollos aparte.

---

## Mes 1 — Cumplir sin riesgo

| # | Tarea | Esfuerzo | Por qué |
| :-- | :-- | :-- | :-- |
| 1.1 | **Herramienta única de licencias.** Verificar la llave contra el `PUBLIC_KEY_HEX` de la app y avisar si no coinciden; negarse a continuar si falta `private_key.pem` (hoy genera un par nuevo en silencio); respaldo automático antes de rotar. | 1 día | El incidente de la rotación estuvo a punto de costar el cliente. Hoy es posible emitir 12 licencias inservibles sin una sola alerta. |
| 1.2 | **Respaldo de llaves fuera del equipo** y passphrase en gestor de contraseñas, con procedimiento escrito. | 2 h | Sin la llave no se pueden emitir licencias: ni las mensuales ni la perpetua del mes 6. |
| 1.3 | **Registro de solicitudes de soporte** con fecha y hora de recepción y de respuesta. Basta una hoja de cálculo. | 3 h | El contrato compromete respuesta en 24 horas hábiles. Hoy el canal es WhatsApp, sin trazabilidad para demostrar cumplimiento ante un reclamo. |
| 1.4 | **Aviso anticipado de vencimiento** en la aplicación, desde 10 días antes y con la fecha visible. | 3 h | Convierte la renovación mensual en algo planificado en vez de una urgencia el día que deja de funcionar. |
| 1.5 | **Cerrar la verificación pendiente**: guardar credenciales SMTP desde el ejecutable y un envío real de punta a punta. | 2 h | Son los dos caminos nunca probados sobre el `.exe`, solo sobre el código. |

---

## Mes 2 — Reducir la carga de soporte

Cada ítem elimina una categoría de consultas que hay obligación de atender en 24 horas hábiles.

| # | Tarea | Esfuerzo | Por qué |
| :-- | :-- | :-- | :-- |
| 2.1 | **Aceptar Excel (.xlsx) directamente.** Hoy solo lee CSV. | ½ día | El paso manual "Guardar como CSV" es fuente constante de errores de separador y codificación. |
| 2.2 | **Validación previa del lote.** Verificar que existan todos los PDF y que los correos sean válidos antes de empezar a enviar. | 1–2 días | Hoy los problemas aparecen a mitad del envío, con parte de los correos ya despachados. |
| 2.3 | **Constancia de envío exportable** en PDF o CSV, con destinatarios enmascarados. | 1–2 días | Responde el reclamo "el paciente dice que no le llegó". Hoy el historial se borra al cerrar. Se conserva el diseño sin datos en reposo: el archivo se genera solo si el operador lo pide. |
| 2.4 | **Mensajes de error accionables**: que digan qué hacer, no solo qué pasó. | ½ día | Menos escalamientos por mensajes que el usuario no sabe interpretar. |

---

## Mes 3 — Consolidación y segundo cliente

| # | Tarea | Esfuerzo | Por qué |
| :-- | :-- | :-- | :-- |
| 3.1 | **Preparar la consolidación del mes 6**: emitir y probar la licencia perpetua antes de que llegue la fecha. | 2 h | Obligación contractual (ver Bloque 0). Si falla ese día, el cliente queda sin servicio teniendo derecho perpetuo. |
| 3.2 | **Documento de conformidad de seguridad** que mapee los controles del software a OWASP Top 10 2021, NIST SP 800-53 y NIST SP 800-88. | 1 día | La cláusula Octava declara que el software fue auditado bajo esos estándares. Si el área de seguridad de la clínica pide evidencia, hoy no existe el documento que la sustente. |
| 3.3 | **Firma digital del instalador (code signing).** | 1 día + costo del certificado | Elimina alertas de antivirus y SmartScreen. Hoy la guía de TI pide agregar una exclusión de antivirus, algo que muchas áreas de seguridad institucionales no aceptan. |
| 3.4 | **Funciones de valor** (varios adjuntos en un correo, plantillas por tipo de servicio). | 4–5 días | No obligatorias por contrato: cotizar como desarrollo aparte o usarlas como argumento de renovación del semestre. |

---

## Calendario de fechas críticas

| Momento | Qué ocurre | Acción |
| :-- | :-- | :-- |
| Pago de la licencia | Ese día es la **FECHA DE INICIO** | Registrarlo: de ahí se cuentan los seis meses |
| Mismo día de cada mes | Se causa la mensualidad de soporte | Emitir la licencia del mes contra pago confirmado |
| Mes 6 desde FECHA DE INICIO | La licencia se consolida como perpetua | Emitir licencia perpetua (tarea 3.1) |
| Mes 6, 30 días antes | Vence el período semestral | Decidir prórroga o renegociación de cláusulas |

---

## Rutina mensual de soporte

1. Emitir y entregar la licencia del mes **contra pago confirmado**.
2. Verificar el respaldo de llaves y el acceso a la passphrase.
3. Revisar el registro de solicitudes: ninguna por fuera de las 24 horas hábiles.
4. Compilar y entregar la versión del mes con nota de cambios (`compilar.bat`).
5. Revisar `app.log` del cliente si hubo incidencias.

---

## Lo que conviene NO hacer

- **No migrar a web ni a servidor.** La cláusula Octava declara que el proveedor no accede, no
  recolecta ni trata datos personales de los pacientes. Un backend rompería esa declaración y
  trasladaría responsabilidad frente a la Ley 1581 de 2012 y la Superintendencia de Industria y
  Comercio.
- **No agregar base de datos persistente.** Mismo motivo: el modelo sin persistencia en disco está
  declarado en el contrato.
- **No regalar desarrollos.** El soporte no obliga a construir funciones nuevas; entregarlas sin
  cobrar erosiona el margen y fija un precedente.

---

## Riesgos a vigilar

| Riesgo | Mitigación |
| :-- | :-- |
| Pérdida de la passphrase o del par de llaves | Tareas 1.1 y 1.2, primera semana |
| Llegar el mes 6 sin licencia perpetua lista | Tarea 3.1, agendada con antelación |
| Incumplir el SLA de 24 horas hábiles por falta de registro | Tarea 1.3 |
| Que pidan evidencia de la auditoría declarada | Tarea 3.2 |
| Suspensión de la cuenta de correo por volumen | La pausa entre envíos lo mitiga; vigilar el límite diario del plan contratado |
