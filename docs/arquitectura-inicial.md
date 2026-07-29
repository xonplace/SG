# Software ISO - Arquitectura inicial

## Objetivo

Construir una aplicacion web llamada **Sistema de gestion** para administrar hallazgos del Sistema de Gestion de Calidad, cubriendo el ciclo completo:

1. Registro del hallazgo por cualquier colaborador.
2. Validacion del hallazgo por el Representante de la Gerencia.
3. Cierre por no aplicar, o clasificacion como No Conformidad (menor - mayor) u Oportunidad de Mejora.
4. Asignacion de responsable de correccion inmediata.
5. Tratamiento de la correccion, cuando corresponda.
6. Asignacion de responsable de la accion correctiva.
7. Tratamiento de la accion correctiva, con analisis de causa raiz y definicion de accion para evitar recurrencia.
8. Asignacion de responsable del seguimiento y verificacion de eficacia.
9. Seguimiento/verificacion de eficacia y cierre.
10. Consulta historica y operacional por estado, responsable, tipo, fechas y plazos.

La arquitectura queda ajustada al procedimiento actual `SGC-PG-AC_v3 Accion Correctiva` y al formulario `SGC-F4-AC_v2 Formulario Accion Correctiva`.

## Recomendacion tecnologica

### Opcion recomendada para iniciar: Django + PostgreSQL

Django es una buena base para este caso porque el sistema tendra formularios, usuarios, roles, flujos de aprobacion, reportes, administracion interna y reglas de negocio. Permite avanzar rapido con una aplicacion monolitica ordenada, sin partir con una arquitectura demasiado compleja.

Componentes sugeridos:

- Backend y frontend inicial: Django.
- Base de datos: PostgreSQL.
- UI: plantillas Django con Bootstrap o Tailwind.
- Tareas programadas/notificaciones: Celery + Redis, o inicialmente Django management commands + cron.
- Correos: SMTP corporativo o Microsoft 365.
- Autenticacion: usuarios internos con Django Auth; luego se puede integrar SSO/Microsoft Entra ID.
- Despliegue: Docker Compose para desarrollo y servidor interno/cloud para produccion.

### Alternativa moderna: FastAPI + React

FastAPI + React es una buena opcion si se quiere una experiencia de usuario mas rica desde el inicio o una API separada para integraciones futuras. Sin embargo, exige mas decisiones iniciales: frontend, autenticacion, permisos, panel administrativo y manejo de formularios.

Para la primera version, recomendaria Django. La necesidad principal es flujo, trazabilidad, formularios, reportes y administracion. Django entrega mucho de eso de fabrica.

## Lineamientos UI/UX

El sitio debe tener una interfaz minimalista, tomando como referencia visual general el sitio web de H&M Chile (`https://cl.hm.com/`).

Principios de diseno:

- Usar el logo corporativo de alta resolucion ubicado en `assets/brand/tecnodata-logo-alta.png` como marca principal del sitio.
- Fondo predominantemente blanco.
- Alto uso de espacio en blanco.
- Tipografia sans serif limpia, sobria y legible.
- Navegacion superior simple, con pocas opciones visibles.
- Uso de negro, blanco y grises como base visual.
- Color de acento reservado para estados importantes, alertas, vencimientos o acciones primarias.
- Evitar exceso de bordes, sombras, degradados o decoracion.
- Formularios limpios, con campos bien separados y etiquetas claras.
- Tablas densas pero ordenadas para consulta de hallazgos.
- Botones simples, preferentemente texto negro/blanco y una sola accion primaria destacada por pantalla.
- Indicadores de estado discretos, por ejemplo chips o etiquetas con color suave.

Pantallas clave:

- Inicio tipo tablero simple, con resumen de hallazgos abiertos, vencidos, por vencer y cerrados.
- Bandeja de hallazgos con filtros claros y tabla principal.
- Formulario de registro de hallazgo en una sola pantalla, sin sobrecargar al colaborador.
- Vista de detalle del hallazgo con secciones por etapa: validacion, correccion, accion correctiva y seguimiento.
- Historial visible como linea de tiempo simple.

Consideraciones:

- Aunque la referencia sea H&M, el sistema debe mantener tono corporativo y funcional, porque sera una herramienta interna de gestion de calidad.
- El diseno debe priorizar claridad, rapidez de uso y trazabilidad antes que elementos comerciales o promocionales.

## Arquitectura logica

```text
Usuarios internos
      |
      v
Sitio web ISO
      |
      +-- Modulo publico/interno de reporte de hallazgos
      +-- Modulo Hallazgos: validacion, clasificacion y cierre.
      +-- Modulo Correccion: responsable, accion inmediata y evidencias.
      +-- Modulo Accion Correctiva: causa raiz, accion preventiva de recurrencia y evidencias.
      +-- Modulo Seguimiento: medicion de eficacia, verificacion y cierre.
      +-- Modulo Consultas/Reportes
      |
      v
Backend Django
      |
      +-- Reglas de negocio y flujo de estados
      +-- Permisos por rol
      +-- Notificaciones por correo
      +-- Auditoria de cambios
      +-- Plazos por accion (validacion, correccion, accion correctiva y seguimiento).
      |
      v
PostgreSQL
```

## Roles iniciales

- Colaborador: registra hallazgos y puede consultar sus propios reportes.
- Encargado de Calidad: valida si aplica, clasifica, asigna responsable, verifica y cierra.
- Representante de la Gerencia: rol definido en el procedimiento actual para registrar, evaluar, asignar, revisar y cerrar.
- Responsable de Correccion: ejecuta la primera accion de tratamiento, orientada a corregir el problema detectado.
- Responsable de Accion Correctiva: ejecuta la segunda accion de tratamiento; realiza el analisis de causa raiz, por ejemplo 5 Por que o Ishikawa, sube evidencia y define la accion para evitar que el problema vuelva a ocurrir.
- Responsable de Seguimiento y Verificacion de Eficacia: mide la eficacia de la accion correctiva dentro del plazo asignado por el Representante de la Gerencia.
- Administrador: mantiene usuarios, areas, categorias, parametros y permisos.
- Auditor/Consulta: acceso de solo lectura a reportes y trazabilidad.

## Flujo de estados del hallazgo

```text
Reportado
  |
  v
En validacion
  |
  +-- No aplica --> Cerrado no aplica
  |
  +-- Aplica --> Clasificado
                  |
                  v
              Responsable de correccion asignado
                  |
                  v
              Tratamiento correccion
                  |
                  v
              Responsable de accion correctiva asignado
                  |
                  v
              Accion correctiva / causa raiz
                  |
                  v
              Responsable de seguimiento/verificacion asignado
                  |
                  v
              En seguimiento / verificacion
                  |
                  +-- No eficaz / requiere ajuste --> Accion correctiva / causa raiz
                  |
                  +-- Conforme --> Cerrado
```

Estados sugeridos:

- ingresado
- en_validacion
- cerrado_no_aplica
- clasificado
- correccion_asignada
- en_correccion
- correccion_en_revision
- correccion_aprobada
- accion_correctiva_asignada
- en_accion_correctiva
- accion_correctiva_en_revision
- accion_correctiva_aprobada
- seguimiento_asignado
- en_seguimiento
- seguimiento_en_revision
- cerrado

Tipos de hallazgo:

- No Conformidad Mayor
- No Conformidad Menor
- Oportunidad de Mejora

## Nomenclatura de codigos

El sistema debe manejar una nomenclatura correlativa por etapa y tipo:

- Al declarar un hallazgo, el sistema asigna un codigo temporal correlativo con prefijo `H`, por ejemplo `H001`, `H002`, `H003`.
- Cuando el Representante de la Gerencia valida que el hallazgo aplica tratamiento y lo clasifica como No Conformidad, el codigo cambia a un correlativo definitivo con prefijo `NC`, por ejemplo `NC001`, `NC002`.
- Cuando el Representante de la Gerencia valida que el hallazgo aplica tratamiento y lo clasifica como Oportunidad de Mejora, el codigo cambia a un correlativo definitivo con prefijo `OM`, por ejemplo `OM001`, `OM002`.
- Si el hallazgo no aplica tratamiento, mantiene su codigo `H###` y se cierra como no aplica.
- Cada prefijo mantiene su propia secuencia independiente para evitar duplicidades y mantener trazabilidad.
- El cambio de codigo debe quedar registrado en el historial del hallazgo.

## Modelo de datos inicial

### Hallazgo

Campos principales:

- id 
- codigo correlativo automatico, con nomenclatura `H###`, `NC###` u `OM###`
- codigo documental/formulario
- descripcion
- fecha_reporte
- fecha_deteccion
- reportado_por
- cargo_reportante
- area_origen
- proceso_asociado
- fuente, por ejemplo auditoria, reclamo, proceso interno, inspeccion, otro
- clausula_normativa_o_documento
- evidencia_objetiva
- estado
- aplica, si/no/null
- motivo_no_aplica
- tipo_clasificacion
- prioridad
- aprobado_por
- hallazgo_similar_previo
- identificacion_accion_correctiva
- existe_riesgo_real_o_potencial
- identificacion_riesgo
- riesgo_tratado
- representante de la Gerencia
- responsable_correccion
- responsable_accion_correctiva
- responsable_seguimiento
- fecha_limite_validacion
- alerta_validacion_24h_enviada
- fecha_limite_correccion
- alerta_correccion_24h_enviada
- fecha_limite_accion_correctiva
- alerta_accion_correctiva_24h_enviada
- fecha_limite_seguimiento
- alerta_seguimiento_24h_enviada
- fecha_cierre
- created_at
- updated_at

### Correccion

Campos principales:

- hallazgo
- asignado_a
- fecha_asignacion
- plazo_dias_habiles
- fecha_limite
- accion
- resultado
- evidencia
- revisado_por
- conforme
- observaciones_revision

### AccionCorrectiva

Campos principales:

- hallazgo
- asignado_a
- fecha_asignacion
- plazo_dias_habiles
- fecha_limite
- tecnica_analisis
- tecnica_analisis_otro
- pregunta_1
- respuesta_1
- pregunta_2
- respuesta_2
- pregunta_3
- respuesta_3
- pregunta_4
- respuesta_4
- pregunta_5
- respuesta_5
- conclusion
- descripcion_accion_correctiva
- accion_para_evitar_recurrencia
- evidencia
- medio_verificacion
- revision_matriz_riesgos
- recursos_hh
- recursos_monetarios
- revisado_por
- conforme
- observaciones_revision

### OportunidadMejora

Campos principales:

- hallazgo
- asignado_a
- fecha_asignacion
- descripcion_oportunidad
- analisis_costo_riesgo_beneficio
- accion_de_mejora
- evidencia
- fecha_compromiso
- fecha_realizacion
- plazo_dias_habiles
- medio_verificacion
- revision_matriz_riesgos
- recursos_hh
- recursos_monetarios
- resultado
- estado

### Seguimiento

Campos principales:

- hallazgo
- asignado_a
- fecha_asignacion
- plazo_dias_habiles
- fecha_limite
- verificado_por
- fecha_verificacion
- tecnica_seguimiento
- criterio_medicion_eficacia
- comentario
- resultado_verificacion
- requiere_nueva_accion
- porcentaje_efectividad

### Evidencia

Campos principales:

- hallazgo
- tratamiento, opcional
- archivo
- descripcion
- subido_por
- fecha

### Historial / Auditoria

Campos principales:

- hallazgo
- usuario
- fecha
- accion
- estado_anterior
- estado_nuevo
- comentario

### Parametros maestros

- Areas
- Procesos
- Fuentes de hallazgo
- Prioridades
- Categorias
- Usuarios y roles

## Modulos funcionales

### 1. Registro de hallazgos

- Formulario simple para colaboradores.
- Campos minimos obligatorios: descripcion del hallazgo, area/proceso, fuente y datos del reportante.
- Creacion automatica de codigo temporal `H###`.
- Notificacion por correo al colaborador que genero el hallazgo y al Representante de la Gerencia.

### 2. Validacion de calidad

- Bandeja de hallazgos pendientes.
- Accion "No aplica", con motivo obligatorio.
- Accion "Aplica", con clasificacion obligatoria.
- Cambio automatico de codigo a `NC###` u `OM###` segun la clasificacion aprobada.
- Asignacion de responsable y plazos.

### 3. Tratamiento de la correccion

- Es la primera fase de tratamiento.
- El Representante de la Gerencia asigna un responsable de correccion.
- El responsable ejecuta la accion para corregir el problema detectado.
- Carga evidencias.
- El Representante de la Gerencia revisa si la correccion queda conforme.

### 4. Tratamiento de la accion correctiva

- Es la segunda fase de tratamiento y puede tener un responsable distinto al responsable de correccion.
- El Representante de la Gerencia asigna el responsable de accion correctiva.
- El responsable realiza analisis de causa raiz, por ejemplo 5 Por que o Ishikawa.
- El responsable sube evidencias del analisis y de la accion definida.
- El responsable determina la accion para evitar que el hallazgo vuelva a ocurrir.
- El Representante de la Gerencia revisa y aprueba la accion correctiva.

### 5. Seguimiento y verificacion de eficacia

- Es una tercera etapa independiente.
- El Representante de la Gerencia asigna un responsable de seguimiento y verificacion.
- Se define un plazo o tiempo de medicion para evaluar la eficacia de la accion correctiva.
- El responsable mide y registra la eficacia.
- Calidad puede aprobar cierre o devolver a accion correctiva.
- Cierre con comentario final obligatorio.

### 6. Consultas y reportes

Filtros iniciales:

- Estado
- Tipo
- Area
- Proceso
- Responsable
- Rango de fechas
- Hallazgos vencidos
- Hallazgos por vencer

Indicadores iniciales:

- Total de hallazgos abiertos.
- Total cerrados.
- Total vencidos.
- Tiempo promedio de cierre.
- Hallazgos por area.
- Hallazgos por tipo.
- Cumplimiento de plazos.

Reportes/documentos iniciales:

- Registro digital del hallazgo reemplazando por completo el uso operativo del formulario `SGC-F4-AC`.
- Registro consolidado `SGC-F5-CAC Control de Accion Correctiva` como tabla consultable y reporte maestro del sistema.
- Listado de hallazgos vencidos o por vencer segun calendario de dias habiles.
- Listado de hallazgos por responsable, estado y vencimiento.

## Reglas de negocio iniciales

- Todo cambio de estado debe quedar registrado en historial.
- Entre la deteccion y la notificacion del hallazgo no deben transcurrir mas de 2 dias habiles.
- No se puede cerrar un hallazgo aplicable sin seguimiento/verificacion.
- No se puede marcar "No aplica" sin justificacion.
- Si se clasifica como No Conformidad u Oportunidad de Mejora, debe tener responsable y plazo.
- El codigo inicial del hallazgo debe ser `H###`.
- Al aprobar una No Conformidad, el codigo debe transformarse a `NC###`.
- Al aprobar una Oportunidad de Mejora, el codigo debe transformarse a `OM###`.
- El cambio de codigo debe quedar registrado en el historial del hallazgo.
- Todo hallazgo debe registrar revision de riesgos, incluso cuando no aplique tratamiento.
- Si el hallazgo es No Conformidad, el sistema debe separar dos fases de tratamiento: correccion y accion correctiva.
- La correccion debe tener responsable, plazo, accion ejecutada, evidencia y revision de conformidad.
- La accion correctiva debe poder tener un responsable distinto; debe incluir analisis de causa raiz, evidencia y accion para evitar recurrencia.
- La verificacion de eficacia debe ser una tercera etapa, con responsable y plazo de medicion asignados por el Representante de la Gerencia.
- Si el hallazgo es Oportunidad de Mejora, debe evaluarse costo, riesgos y beneficios antes de implementar.
- El sistema debe detectar vencimientos segun fechas limite.
- Los plazos deben poder calcularse en dias habiles.
- Los dias habiles deben considerar fines de semana y feriados chilenos configurables.
- El sistema debe enviar alertas por correo 24 horas antes del vencimiento de los plazos de validacion, correccion, accion correctiva y seguimiento/verificacion de eficacia.
- Cada alerta de 24 horas debe quedar registrada para evitar envios duplicados.
- Las evidencias deben quedar asociadas al hallazgo y al usuario que las subio.
- Los colaboradores no deben poder modificar un hallazgo despues de reportado, salvo que Calidad solicite aclaracion.
- El rol Representante de la Gerencia / Encargado de Calidad debe ser parametrizable para adaptarse al nombre interno usado por la empresa.
- El Auditor Lider puede participar en seguimiento, pero el sistema no debe obligar a que siempre sea ese rol; el Representante de la Gerencia debe poder asignar otro responsable competente.
- Salida No Conforme, Queja/Reclamo y Requerimiento se manejaran inicialmente dentro del mismo modulo como fuente o tipo de hallazgo.

## Notificaciones

Eventos sugeridos:

- Nuevo hallazgo reportado: enviar correo al Encargado de Calidad / Representante de la Gerencia.
- Hallazgo no aplica: notificar al reportante.
- Hallazgo validado y clasificado: notificar al reportante y al Representante de la Gerencia.
- Responsable de correccion asignado: notificar automaticamente al responsable de correccion y al Representante de la Gerencia.
- Correccion completada o enviada a revision: notificar al Representante de la Gerencia.
- Responsable de accion correctiva asignado: notificar automaticamente al responsable de accion correctiva y al Representante de la Gerencia.
- Accion correctiva completada o enviada a revision: notificar al Representante de la Gerencia.
- Responsable de seguimiento/verificacion asignado: notificar automaticamente al responsable de seguimiento y al Representante de la Gerencia.
- Seguimiento/verificacion completado o enviado a revision: notificar al Representante de la Gerencia.
- Alerta 24 horas antes del vencimiento de validacion: notificar al Representante de la Gerencia.
- Alerta 24 horas antes del vencimiento de correccion: notificar al responsable de correccion y al Representante de la Gerencia.
- Alerta 24 horas antes del vencimiento de accion correctiva: notificar al responsable de accion correctiva y al Representante de la Gerencia.
- Alerta 24 horas antes del vencimiento de seguimiento/verificacion de eficacia: notificar al responsable de seguimiento y al Representante de la Gerencia.
- Plazo vencido: notificar al responsable correspondiente, al Representante de la Gerencia y a jefatura si aplica.
- Hallazgo cerrado: notificar al reportante y responsable.

Consideracion tecnica:

- Las alertas de vencimiento requieren un proceso programado diario o frecuente.
- Para una primera version se puede usar un comando programado de Django ejecutado por cron o el programador de tareas del servidor.
- Si el volumen crece, se recomienda Celery + Redis para gestionar envios, reintentos y cola de correos.

## Seguridad y permisos

- Acceso autenticado para usuarios internos.
- Formulario de reporte puede ser autenticado o semi-publico interno, segun politica de la empresa.
- Permisos por rol.
- Auditoria de cambios obligatoria.
- Backups automaticos de base de datos.
- Adjuntos con control de acceso.
- HTTPS en produccion.

## Estructura de proyecto sugerida

```text
software-iso/
  backend/
    manage.py
    config/
      settings.py
      urls.py
    apps/
      accounts/
      findings/
      workflows/
      notifications/
      reports/
  docs/
    arquitectura-inicial.md
    modelo-datos.md
    flujo-hallazgos.md
  docker-compose.yml
  README.md
```

## Primera version viable

La primera version deberia enfocarse en:

1. Login y roles basicos.
2. Registro de hallazgos.
3. Bandeja de Calidad.
4. Validacion aplica/no aplica.
5. Clasificacion y asignacion.
6. Tratamiento por responsable.
7. Seguimiento y cierre.
8. Listado con filtros basicos.
9. Historial de cambios.
10. Notificaciones por correo.
11. Registro digital que reemplaza SGC-F4-AC.
12. Tabla/reporte maestro equivalente a SGC-F5-CAC.
13. Alertas automaticas 24 horas antes de vencimientos.

## Fases de desarrollo

### Fase 1 - Definicion funcional

- Confirmar campos del formulario.
- Confirmar roles.
- Confirmar estados del flujo.
- Confirmar plazos y reglas de vencimiento.
- Confirmar reportes requeridos.

### Fase 2 - MVP

- Crear aplicacion Django.
- Crear modelos principales.
- Crear formularios y vistas.
- Crear panel de gestion.
- Crear historial.
- Crear notificaciones basicas.

### Fase 3 - Reportes y control

- Dashboard.
- Exportacion Excel/PDF.
- Indicadores por area, tipo y plazo.
- Alertas de vencimiento.

### Fase 4 - Integraciones y mejoras

- SSO corporativo.
- Firma/aprobacion formal, si aplica.
- API para integraciones.
- Control documental.
- Gestion de auditorias.
- Reclamos de clientes/proveedores.
- Riesgos y acciones preventivas.

## Decisiones pendientes

- Si el formulario sera solo para usuarios autenticados o abierto dentro de la red.
- Si se integrara con Microsoft 365 para usuarios y correos.
- Si los archivos adjuntos se guardaran en servidor, SharePoint o almacenamiento cloud.
- Si se requiere firma electronica o aprobacion formal.
- Si el flujo cambia segun tipo de hallazgo.
- Si cada area tendra un responsable de calidad propio.
- Confirmar plantilla y destinatarios internos de notificaciones automaticas.
- Confirmar si se requiere una salida PDF/Excel solo para auditorias o respaldo documental, aunque el sistema reemplace el formulario SGC-F4-AC.

## Propuesta de stack final para partir

- Python
- Django
- PostgreSQL
- Bootstrap o Tailwind
- Docker Compose
- Git
- SMTP/Microsoft 365 para notificaciones

Esta combinacion permite construir rapido, mantener trazabilidad y dejar espacio para crecer hacia otros modulos del Sistema de Gestion de Calidad.
