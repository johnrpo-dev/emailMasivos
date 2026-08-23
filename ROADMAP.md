# Plan de trabajo — 3 meses

Punto de partida: **v1.1.0** entregada, un cliente en producción, contrato de soporte mensual.

El plan prioriza en este orden: **(1)** que no se caiga la operación del negocio, **(2)** que cada
mes lleguen menos llamadas, **(3)** que el cliente vea valor que justifique la mensualidad.

> **Supuesto de capacidad:** ~2 días de trabajo por semana. Si es menos, se recorta por el final
> de cada mes (los ítems están ordenados por prioridad dentro de cada bloque).

---

## Mes 1 — Blindar la operación

El incidente de las llaves de licencia demostró que el riesgo mayor no está en el código que usa
el cliente, sino en las herramientas con las que se opera el negocio.

| # | Tarea | Esfuerzo | Por qué |
| :-- | :-- | :-- | :-- |
| 1.1 | **Herramienta única de licencias.** Fusionar `generar_licencia.py` y `rotar_y_generar.py` en un solo script que: verifique la llave cargada contra el `PUBLIC_KEY_HEX` de la app y avise si no coinciden; se niegue a continuar si falta `private_key.pem` (hoy genera un par nuevo en silencio); respalde antes de cualquier rotación; y exija confirmación explícita para rotar. | 1 día | Estuvo a punto de costar el cliente. Hoy es posible emitir 12 licencias inservibles sin ninguna alerta. |
| 1.2 | **Respaldo de llaves fuera del equipo** + procedimiento escrito de recuperación. Passphrase en gestor de contraseñas. | 2 h | Si se pierde el disco, se pierde la capacidad de emitir licencias para todos los clientes. |
| 1.3 | **Aviso anticipado de vencimiento.** Hoy la app solo avisa cuando la licencia *ya venció*. Mostrar aviso desde 10 días antes, con la fecha visible en la interfaz. | 3 h | Convierte la renovación mensual en algo planificado, en vez de una llamada urgente el día que deja de funcionar. |
| 1.4 | **Cerrar la verificación pendiente**: guardar credenciales SMTP desde el ejecutable empaquetado y hacer un envío real de punta a punta. | 2 h | Son los dos caminos que nunca se probaron sobre el `.exe`, solo sobre el código. |
| 1.5 | **Reenvío individual.** Enviar a un paciente puntual sin preparar un CSV completo. | 1–2 días | Es la petición operativa más previsible: “se equivocaron en un correo, mándalo otra vez”. Hoy obliga a armar un archivo para una sola fila. |

**Resultado del mes:** la operación de licencias deja de ser frágil y el soporte del día a día no
depende de trámites manuales.

---

## Mes 2 — Reducir la carga de soporte

Cada ítem aquí elimina una categoría entera de llamadas. Es el mes que más horas devuelve.

| # | Tarea | Esfuerzo | Por qué |
| :-- | :-- | :-- | :-- |
| 2.1 | **Aceptar Excel (.xlsx) directamente.** Hoy solo lee CSV, así que el laboratorio debe hacer “Guardar como CSV” cada vez. | ½ día | Ese paso manual es fuente constante de errores: separadores, codificación, columnas corridas. |
| 2.2 | **Validación previa del lote (simulacro).** Antes de enviar: verificar que todos los PDF existan, que los correos sean válidos y que no falten datos. Mostrar un resumen y permitir corregir *antes* de empezar. | 1–2 días | Hoy los problemas se descubren a mitad del envío, con parte de los correos ya despachados. |
| 2.3 | **Constancia de envío exportable.** Botón para guardar el resultado del lote en PDF o CSV, con fecha, destinatarios enmascarados y estado. | 1–2 días | Responde “el paciente dice que no le llegó” con evidencia. Hoy el historial se borra al cerrar y solo existe *Copiar Reporte* al portapapeles. Se mantiene el diseño sin datos en reposo: el archivo se genera solo si el operador lo pide. |
| 2.4 | **Mensajes de error accionables.** Que cada error diga qué hacer, no solo qué pasó. | ½ día | Reduce el escalamiento por mensajes que el usuario no sabe interpretar. |

**Resultado del mes:** menos llamadas por errores de archivo y capacidad de responder reclamos con
evidencia.

---

## Mes 3 — Valor visible y preparación para el segundo cliente

| # | Tarea | Esfuerzo | Por qué |
| :-- | :-- | :-- | :-- |
| 3.1 | **Varios documentos en un solo correo.** Un paciente con tres exámenes recibe hoy tres correos; agruparlos en uno con tres adjuntos. | 2–3 días | Mejora la experiencia del paciente y reduce el consumo de la cuota diaria del proveedor de correo. Requiere cambiar el agrupamiento del lote. |
| 3.2 | **Plantillas por tipo de servicio.** Un mensaje distinto según el examen. | 2 días | Diferenciador comercial y petición natural de un laboratorio con varias líneas de servicio. |
| 3.3 | **Firma digital del instalador (code signing).** | 1 día + costo del certificado | Elimina las alertas de antivirus y de SmartScreen. En clientes institucionales es casi un requisito de compra; hoy la guía de TI pide agregar una exclusión de antivirus, lo cual muchas áreas de seguridad no aceptan. |
| 3.4 | **Reporte mensual de actividad** para entregar al cliente. | 1 día | Hace tangible la mensualidad: cuántos envíos, tasa de éxito, incidencias atendidas. |

**Resultado del mes:** producto vendible a un segundo cliente sin fricción y mensualidad
justificada con entregables visibles.

---

## Rutina mensual de soporte

Independiente del desarrollo, cada mes:

1. Emitir y entregar la licencia del mes **contra pago confirmado**.
2. Verificar el respaldo de llaves y que la passphrase siga accesible.
3. Revisar `app.log` del cliente si hubo incidencias.
4. Compilar y entregar la versión del mes (`compilar.bat`), con nota de cambios.
5. Enviar el reporte de actividad (desde el mes 3).

---

## Lo que conviene NO hacer

- **No migrar a web ni a servidor.** El diferenciador es que los datos de pacientes nunca salen del
  equipo. Un backend introduce responsabilidad legal sobre datos sensibles.
- **No agregar base de datos persistente.** Rompería el argumento de privacidad que sostiene la
  venta.
- **No atar la licencia al equipo.** Ya se decidió: el cliente necesita usarla en varios
  computadores y ataría cada cambio de disco a una solicitud de reemisión.
- **No acumular funciones sin cobrarlas.** Cada bloque mensual debería corresponder a una entrega
  concreta comunicada al cliente.

---

## Riesgos a vigilar

| Riesgo | Mitigación |
| :-- | :-- |
| Pérdida de la passphrase o del par de llaves | Tarea 1.2, primera semana |
| El proveedor de correo bloquea la cuenta por volumen | La pausa entre envíos ya lo mitiga; vigilar el límite diario del plan contratado |
| Falsos positivos de antivirus tras cada compilación | Tarea 3.3 (firma digital) |
| Crecimiento del CSV por encima de 10.000 filas | Límite actual; revisar si el laboratorio crece |
| Dependencia de una sola persona para operar licencias | Documentar el procedimiento (tarea 1.2) |
