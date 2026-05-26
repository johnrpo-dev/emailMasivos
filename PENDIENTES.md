# Pendientes y Mejoras Futuras - Envió Masivo Seguro (SEMS Pro)

Este documento registra el estado de las mejoras y deudas técnicas identificadas a futuro para el software.

---
*Última actualización: 2026-05-23*

## ⏳ Próximos Pasos (Mejoras a Futuro para Nivel 9.5/10)

Estas tareas han sido identificadas en la evaluación final como las únicas deudas técnicas abiertas para elevar el proyecto al estándar de excelencia absoluta:

### 1. Suite de Pruebas Unitarias Automatizadas
*   **Estado:** `[Completado]`
*   **Descripción:** Implementar un suite de pruebas automáticas (utilizando `pytest` o `unittest`) para validar el motor principal de forma aislada: sanitización de nombres de archivo y path traversal en `WorkflowOrchestrator`, cifrado robusto en `PDFCrypto`, y lógica de typos sintácticos en `email_validator.py`.
*   **Meta:** Eliminar la dependencia de verificaciones exclusivamente manuales y anular el riesgo de regresiones ante cambios en dependencias.

### 2. Documentación Formal de Retención de Datos (`PRIV-001`)
*   **Estado:** `[Pendiente]`
*   **Descripción:** Redactar y formalizar un documento descriptivo de protección de la información (`PRIVACY.md` o anexo técnico en el repositorio) que detalle el modelo Zero-Footprint implementado: retención efímera en RAM, ofuscación activa de PII y borrado físico seguro anti-forense.
*   **Meta:** Cumplir formalmente con normativas de protección de datos personales ante auditorías de cumplimiento.

### 3. Desacoplamiento de la Coordinación de Flujo en `app.py`
*   **Estado:** `[Completado]`
*   **Descripción:** Migrar la inicialización del flujo de reintentos y el método `_execute_workflow` desde la ventana principal a un presentador o controlador de UI dedicado (`WorkflowController` o similar).
*   **Meta:** Limitar la responsabilidad de `app.py` únicamente a la construcción de contenedores y navegación de CustomTkinter.