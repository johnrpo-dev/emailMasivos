# Auditoría funcional — SEMS Pro

| | |
| :-- | :-- |
| **Estado** | **CERRADA** — todos los hallazgos corregidos, salvo uno descartado por regla de negocio |
| **Correcciones** | 19/07/2026, commit `89fae44` |
| **Última verificación contra el código** | 24/10/2026, versión 1.2.1 — 54 pruebas automáticas en verde |

## Alcance

Revisión de que cada función y cada botón de la aplicación haga lo que promete. Se cubrió la
lógica de negocio (`src/core/`), toda la capa de interfaz tras el rediseño, configuración,
utilidades, el arranque (`main.py`), las pruebas y el empaquetado.

## Resumen

| Severidad | Encontrados | Corregidos | Descartados |
| :-- | :--: | :--: | :--: |
| Críticos / altos | 2 | 2 | — |
| Medios | 10 | 9 | 1 |
| Menores | 8 | 8 | — |

---

## Hallazgos críticos

### A. Sin candado de proceso en ejecución — envío duplicado

**Problema.** Iniciar un envío y reintentar lotes no verificaba si ya había otro proceso en curso.
Mientras corría un reintento, el operador podía abrir el historial y reintentar los mismos
registros desde un lote anterior: dos envíos simultáneos al mismo paciente. Era el error reportado
por el usuario.

**Corrección.** `WorkflowController` lleva un indicador de proceso activo (`is_busy()`).
`start_process` y `retry_batch` se niegan a arrancar si hay un envío en curso, y la ventana de
detalle de lote deshabilita sus botones de reintento mientras tanto.

**Prueba:** `tests/test_retry_purge.py` → `TestWorkflowLock`.

### B. Un hilo de envío que falla pierde destinatarios

**Problema.** Si uno de los hilos de envío terminaba con una excepción no controlada, los
registros pendientes de su lote no quedaban como fallidos: se contaban como éxitos y no se podían
reintentar.

**Corrección.** `WorkflowOrchestrator._register_chunk_failures` registra cada registro pendiente
como fallido reintentable, tanto si el hilo no logra conectar como si falla a mitad del lote.

**Prueba:** sin prueba dedicada.

---

## Hallazgos medios

| # | Problema | Corrección | Prueba |
| :-- | :-- | :-- | :-- |
| 1 | Un destinatario recuperado en un reintento seguía como "Fallido" en el historial, y el lote seguía ofreciendo correcciones ya aplicadas | La depuración de recuperados lo marca como **Recuperado**, actualiza el contador y poda las correcciones aplicadas | `test_retry_purge.py` → `TestPurgeRecoveredFailures` |
| 2 | El historial y el monitor en vivo contaban los éxitos de forma distinta | El lote usa los contadores reales de los hilos como única fuente | Sin prueba dedicada |
| 3 | Dos filas iguales del CSV producen dos correos | **Descartado** (ver abajo) | — |
| 4 | `usuario@gmail.con` se aceptaba como válido | Validación de terminación de dominio en proveedores conocidos, con sugerencia de corrección | `test_email_validator_tld.py` |
| 5 | Un `config.json` dañado ocultaba la contraseña del correo guardada en el Administrador de credenciales | La lectura de credenciales es independiente del archivo de configuración | `test_config_manager.py` |
| 6 | Los nombres de los PDF, que suelen contener el nombre del paciente, quedaban completos en el registro | Enmascarado con `mask_filename` | Sin prueba dedicada |
| 7 | Riesgo de error de fuentes al pasar de la activación al aviso de período de gracia | Se reinicia la caché de fuentes antes de crear la ventana temporal | Sin prueba dedicada |
| 8 | La detección de retroceso del reloj era débil | La marca de último uso solo avanza, se refresca cada 10 minutos y su ausencia queda registrada | `test_license_last_run.py` |
| 9 | El archivo de compilación de PyInstaller quedaba fuera del repositorio | Excepción explícita en `.gitignore` | — |
| 10 | Faltaban pruebas de configuración, licencias, reintentos y validación | Se agregaron los archivos de prueba citados en esta tabla | — |

### Descartado: filas duplicadas en el CSV

El hallazgo 3 se descartó porque **no es un error**: un paciente con varios procesos el mismo día
(por ejemplo, rayos X y audiometría) aparece en varias filas y debe recibir un correo por cada
documento. La regla quedó documentada en `CLAUDE.md` para que ninguna revisión futura intente
"corregirla".

---

## Hallazgos menores

| Problema | Corrección | Prueba |
| :-- | :-- | :-- |
| Un reintento consumía un intento aunque terminara en "no hay correcciones para aplicar" | El intento solo se cuenta cuando el envío realmente arranca | `test_retry_purge.py` |
| Un fallo grave mostraba "-1 exitosos" en la consola | El contador nunca baja de cero | — |
| Un CSV sin filas mostraba "finalizado con éxito sin errores" | Muestra "El archivo CSV no contiene registros para procesar" | — |
| El destinatario del correo no pasaba por el saneamiento de cabeceras | Se sanea igual que el remitente y el asunto | — |
| Código sin uso duplicado en el orquestador | Eliminado | — |
| `mask_email` devolvía intacto un texto sin `@` | También lo enmascara | — |
| La vista previa abría una ventana vacía antes de validar el CSV | Valida el archivo antes de crear la ventana | — |
| La depuración de recuperados podía descartar un pendiente legítimo con clave repetida | Las claves repetidas quedan fuera de la depuración | `test_retry_purge.py` |

---

## Cambios posteriores relacionados

Correcciones hechas después de la auditoría que tocan las mismas áreas:

| Commit | Fecha | Cambio |
| :-- | :-- | :-- |
| `d138ba8` | 11/08/2026 | El directorio temporal con el PDF cifrado ya no sobrevive si falla el borrado seguro (`test_temp_cleanup.py`) |
| `bcdc09d` | 13/08/2026 | Empaquetado correcto del almacén de credenciales en el ejecutable; la aplicación deja de sugerir nombres de PDF parecidos para no revelar el contenido del directorio |
| `4c2a50b` | 29/08/2026 | La aplicación confía en varias llaves públicas de licencia (`test_license_multikey.py`) |
| `0d6b21a` | 11/10/2026 | Llave activa real y licencia perpetua inmune a cambios del reloj |

---

## Fortalezas verificadas

Controles revisados que funcionaban correctamente y no requirieron cambios:

- Validación estricta de certificados TLS, con protección contra la degradación de STARTTLS.
- Defensa contra rutas maliciosas en los nombres de archivo del CSV.
- Borrado seguro de los PDF temporales en todos los caminos de ejecución.
- Pausa global entre envíos compartida por todos los hilos.
- Conservación de la contraseña guardada cuando el campo muestra el marcador oculto.
- Búsqueda del historial por hash HMAC, consistente con el registro de envíos.
- Configuración y llaves de firma excluidas del repositorio.

## Cobertura pendiente

Los hallazgos B, 2, 6 y 7 y la mayoría de los menores están corregidos y verificados en el
código, pero no tienen prueba automática propia. Agregarlas protegería esas correcciones de
regresiones en cambios futuros.

## Cómo verificar

```bash
python -m unittest discover tests -v
```

Archivos de prueba que respaldan esta auditoría: `test_retry_purge.py`, `test_config_manager.py`,
`test_license_last_run.py`, `test_email_validator_tld.py`, `test_temp_cleanup.py` y
`test_license_multikey.py`.
