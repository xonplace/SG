# Plan de pruebas - Salida productiva Modulo Hallazgos

## Objetivo

Validar que el modulo de hallazgos funciona correctamente antes de su salida a produccion.

Este plan debe ejecutarse en ambiente de pruebas o en la MV productiva antes de liberar acceso a todos los usuarios.

## Alcance

Incluye:

- Registro de hallazgos.
- Validacion inicial.
- Flujo No Conformidad.
- Flujo Oportunidad de Mejora.
- Evidencias.
- Mis tareas.
- Bandeja.
- Vencidos.
- Reportes.
- Permisos por rol.
- Modo inicial solo Hallazgos.

No incluye:

- SMTP productivo.
- SSO.
- Biblioteca documental.
- Formularios.
- Procesos.
- Capacitaciones.

## Roles de prueba

Crear o validar usuarios de prueba:

| Rol | Usuario sugerido | Objetivo |
| --- | --- | --- |
| Administrador | admin | Configuracion general y permisos |
| Representante de la Gerencia | representante | Validar, clasificar, asignar, revisar y cerrar |
| Responsable de Correccion | correccion | Registrar correccion |
| Responsable de Accion Correctiva | accion | Registrar causa raiz y accion correctiva |
| Responsable de Seguimiento | seguimiento | Registrar seguimiento y eficacia |
| Usuario estandar | usuario | Registrar hallazgo y consultar lo permitido |

## Datos iniciales requeridos

- Areas cargadas.
- Procesos cargados.
- Fuentes cargadas.
- Plazos configurados.
- Roles configurados.
- Representante de la Gerencia configurado.
- Modulo Hallazgos visible.
- Modulos no liberados ocultos.

## Matriz de pruebas

| ID | Caso | Rol | Pasos | Resultado esperado | Estado |
| --- | --- | --- | --- | --- | --- |
| H-001 | Registrar hallazgo | Usuario estandar | Ingresar a Nuevo Hallazgo, completar datos obligatorios y guardar | Hallazgo creado con codigo `H`, estado `Ingresado` | Pendiente |
| H-002 | Validar hallazgo no aplica | Representante | Abrir hallazgo ingresado, marcar que no aplica, registrar motivo y guardar | Hallazgo queda `Cerrado no aplica` | Pendiente |
| H-003 | Validar hallazgo como NC | Representante | Abrir hallazgo ingresado, marcar aplica, clasificar como NC y guardar | Codigo cambia de `H` a `NC`, estado `Clasificado` | Pendiente |
| H-004 | Validar hallazgo como OM | Representante | Abrir hallazgo ingresado, marcar aplica, clasificar como OM y guardar | Codigo cambia de `H` a `OM`, estado `Clasificado` | Pendiente |
| H-005 | Asignar correccion NC | Representante | En NC clasificada, asignar responsable de correccion y accion solicitada | Estado `Correccion asignada`, aparece en Mis tareas del responsable | Pendiente |
| H-006 | Registrar correccion | Responsable Correccion | Abrir Mis tareas, registrar detalle y evidencia | Estado `Correccion en revision` | Pendiente |
| H-007 | Rechazar correccion | Representante | Revisar correccion, marcar no conforme y registrar observaciones | Vuelve a responsable con observaciones | Pendiente |
| H-008 | Aprobar correccion | Representante | Revisar correccion, marcar conforme | Estado `Correccion aprobada` | Pendiente |
| H-009 | Asignar accion correctiva | Representante | Asignar responsable de accion correctiva | Estado `Accion correctiva asignada`, aparece en Mis tareas | Pendiente |
| H-010 | Registrar accion correctiva con 5 Por que | Responsable Accion Correctiva | Seleccionar 5 Por que, completar al menos una pregunta/respuesta, causa raiz y accion | Estado `Accion correctiva en revision` | Pendiente |
| H-011 | Validar obligatoriedad 5 Por que | Responsable Accion Correctiva | Seleccionar 5 Por que y guardar sin preguntas/respuestas | Sistema muestra error de validacion | Pendiente |
| H-012 | Registrar accion correctiva libre | Responsable Accion Correctiva | Seleccionar Libre, completar analisis, causa raiz y accion | Estado `Accion correctiva en revision` | Pendiente |
| H-013 | Rechazar accion correctiva | Representante | Marcar no conforme y registrar observaciones | Vuelve a responsable con observaciones | Pendiente |
| H-014 | Aprobar accion correctiva | Representante | Marcar conforme | Estado `Accion correctiva aprobada` | Pendiente |
| H-015 | Asignar oportunidad de mejora | Representante | En OM clasificada, asignar responsable de plan de accion | Estado relacionado a plan de accion, no debe pedir correccion | Pendiente |
| H-016 | Registrar plan OM | Responsable Accion Correctiva / OM | Registrar plan y medio de verificacion | Estado `Accion correctiva en revision` o equivalente de plan en revision | Pendiente |
| H-017 | Rechazar plan OM | Representante | Marcar plan no conforme y registrar observaciones | Vuelve al responsable del plan | Pendiente |
| H-018 | Aprobar plan OM | Representante | Marcar plan conforme | Queda listo para asignar seguimiento | Pendiente |
| H-019 | Asignar seguimiento | Representante | Asignar responsable y plazo de seguimiento | Estado `Seguimiento asignado`, aparece en Mis tareas | Pendiente |
| H-020 | Registrar seguimiento | Responsable Seguimiento | Completar tecnica, criterio, resultado y porcentaje | Estado `Seguimiento en revision` | Pendiente |
| H-021 | Validar seguimiento en blanco | Responsable Seguimiento | Intentar guardar seguimiento sin datos | Sistema muestra errores de campos obligatorios | Pendiente |
| H-022 | Rechazar seguimiento | Representante | Marcar no eficaz y registrar observaciones | No permite cerrar, queda pendiente de accion o revision | Pendiente |
| H-023 | Cerrar hallazgo | Representante | Marcar seguimiento eficaz y cerrar | Estado `Cerrado`, fecha de cierre registrada | Pendiente |
| H-024 | Cargar evidencia por responsable correcto | Responsable asignado | Cargar evidencia en etapa asignada | Evidencia queda asociada a etapa correcta | Pendiente |
| H-025 | Bloquear evidencia a usuario no asignado | Usuario no asignado | Intentar cargar evidencia en hallazgo ajeno | Sistema no debe permitir la accion | Pendiente |
| H-026 | Bandeja ordenada | Usuario autorizado | Abrir Bandeja de Hallazgos | Abiertos aparecen arriba, cerrados abajo, ordenados por fecha | Pendiente |
| H-027 | Columna Asignado a | Usuario autorizado | Revisar bandeja con hallazgos en distintas etapas | Muestra responsable actual o Representante cuando corresponde | Pendiente |
| H-028 | Filtro por estado | Usuario autorizado | Filtrar por estado especifico | Lista muestra solo hallazgos del estado seleccionado | Pendiente |
| H-029 | Vista Vencidos | Usuario autorizado | Crear o ajustar hallazgo vencido, abrir Vencidos | Hallazgo vencido aparece correctamente | Pendiente |
| H-030 | Reporte de hallazgos | Representante/Admin | Abrir Reportes | Dashboard carga totales, estados y graficos sin error | Pendiente |
| H-031 | Permisos usuario estandar | Usuario estandar | Iniciar sesion y revisar menu/acciones | No ve acciones administrativas ni etapas no asignadas | Pendiente |
| H-032 | Permisos Representante | Representante | Iniciar sesion y revisar Mis tareas y acciones | Ve pendientes RG y puede validar/revisar/cerrar | Pendiente |
| H-033 | Modo solo Hallazgos | Admin | Ejecutar `configure_findings_only` y revisar menu | Solo queda visible Hallazgos y mantenedores permitidos | Pendiente |
| H-034 | Subida de archivo | Usuario/responsable | Adjuntar archivo en registro o etapa | Archivo queda disponible y descargable | Pendiente |
| H-035 | Cierre no permitido sin eficacia | Representante | Intentar cerrar con seguimiento no eficaz | Sistema bloquea el cierre | Pendiente |
| H-036 | Inicio en modo solo Hallazgos | Usuario autenticado | Iniciar sesion con solo Hallazgos activo | El sistema carga directamente la Bandeja de Hallazgos | Pendiente |

## Criterio de aprobacion

La salida productiva se considera aprobada si:

- Todos los casos criticos se aprueban.
- No existen errores de permisos.
- No existen errores al cargar evidencias.
- El flujo NC y OM se completa correctamente.
- Los modulos no liberados permanecen ocultos.
- La bandeja, Mis tareas, Vencidos y Reportes cargan sin errores.

## Casos criticos obligatorios

Antes de liberar, deben aprobarse al menos:

- H-001
- H-003
- H-004
- H-005
- H-006
- H-008
- H-010
- H-015
- H-016
- H-019
- H-020
- H-023
- H-025
- H-031
- H-032
- H-033

## Registro de ejecucion

| Fecha | Responsable prueba | Ambiente | Resultado general | Observaciones |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Observaciones previas a produccion

Registrar aqui cualquier desviacion encontrada durante las pruebas:

| ID caso | Observacion | Responsable correccion | Estado |
| --- | --- | --- | --- |
|  |  |  |  |
