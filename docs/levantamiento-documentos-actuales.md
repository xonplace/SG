# Levantamiento desde documentos actuales

Este documento resume la informacion extraida desde:

- `SGC-F4-AC_v2 Formulario Accion Correctiva.xlsx`
- `SGC-PG-AC_v3 Accion Correctiva.docx`

La finalidad es ajustar la arquitectura del software al procedimiento y formulario que Tecnodata utiliza actualmente.

## Procedimiento actual

El procedimiento establece la metodologia para el registro, analisis y tratamiento de hallazgos que deriven en acciones correctivas y oportunidades de mejora dentro del Sistema de Gestion de Calidad.

### Alcance

Aplica a acciones producto de:

- No conformidades.
- Oportunidades de mejora.
- Reclamos.
- Salidas no conformes.
- Detecciones internas.
- Detecciones externas.

### Regla de aviso inicial

Toda desviacion al SGC debe informarse a la brevedad al Representante de la Gerencia, aportando evidencia objetiva.

Regla relevante para el software:

- Entre la deteccion y la notificacion no deben transcurrir mas de 2 dias habiles.

Esto sugiere que el sistema debe guardar:

- Fecha de deteccion.
- Fecha de registro/notificacion.
- Indicador de aviso fuera de plazo.

### Inicio del proceso

El proceso inicia cuando se identifica una no conformidad u oportunidad de mejora. El origen puede ser:

- Auditoria interna.
- Auditoria externa.
- Reclamo.
- Salida no conforme.
- Revision por la gerencia.
- Fiscalizacion.
- Deteccion interna del personal.

### Evaluacion inicial

Una vez registrado el hallazgo, se evalua si aplica tratamiento.

Si no aplica:

- Se informa a las partes interesadas.
- Se cierra el registro.
- De igual forma debe quedar registrada la revision de riesgos.

Si aplica:

- Se determina el tipo de hallazgo.
- Se selecciona el tratamiento correspondiente.

Regla relevante:

- Todo hallazgo implica revision de riesgos, incluso si no se realiza tratamiento.

## Tipificacion de hallazgos

El procedimiento incluye la siguiente tipificacion:

### No Conformidad

Incumplimiento de un requisito ISO, de un proceso interno de Tecnodata o de un compromiso contractual.

Para el software, la No Conformidad debe poder clasificarse como:

- No Conformidad Mayor.
- No Conformidad Menor.

Ejemplos:

- Atraso en plazos.
- Producto cambiado.
- No realizar tareas segun proceso interno.

### Salida No Conforme

Producto o servicio que no cumple, directamente relacionado con procesos de negocio y con posible impacto al cliente.

Ejemplos:

- Impresora no imprime.
- Software no instalado.
- Producto danado.

### Queja o Reclamo

Insatisfaccion comunicada por externos a Tecnodata respecto del servicio, productos o sistema de tratamiento de quejas.

### Requerimiento

Solicitud o peticion.

Ejemplos:

- Pedir toner.
- Solicitar cotizacion.
- Conocer un producto o servicio.

## Flujo para Oportunidad de Mejora

1. Representante de la Gerencia revisa y analiza la propuesta.
2. Determina si se implementa segun costo, riesgos y beneficios esperados.
3. Si no se implementa, informa a las partes interesadas y cierra.
4. Si se implementa, asigna responsable.
5. Responsable prepara plan de accion.
6. Representante de la Gerencia revisa el plan.
7. Si no esta conforme, devuelve para correccion.
8. Si esta conforme, autoriza implementacion.
9. Se asigna responsable de seguimiento.
10. Responsable realiza seguimiento dentro de plazo.
11. Si no esta conforme, vuelve a revisar plan de accion.
12. Si esta conforme, se cierra la oportunidad de mejora.

## Flujo para No Conformidad / Accion Correctiva

Este flujo debe entenderse como tres etapas separadas, que pueden tener responsables distintos:

1. Tratamiento de la correccion.
2. Tratamiento de la accion correctiva.
3. Seguimiento y verificacion de eficacia.

La correccion busca resolver el problema detectado. La accion correctiva busca eliminar o controlar la causa para evitar que el problema vuelva a ocurrir. El seguimiento busca medir si la accion correctiva fue eficaz.

1. Representante de la Gerencia clasifica el hallazgo como No Conformidad Mayor o Menor.
2. Representante de la Gerencia asigna responsable de correccion inmediata.
3. Responsable realiza e informa la correccion.
4. Representante de la Gerencia revisa la correccion.
5. Si no esta conforme, solicita ajustes a la correccion.
6. Si esta conforme, asigna responsable de accion correctiva.
7. Responsable de accion correctiva realiza analisis de causa raiz, por ejemplo 5 Por que o Ishikawa.
8. Responsable de accion correctiva sube evidencia y determina la accion para evitar recurrencia.
9. Representante de la Gerencia revisa la propuesta.
10. Si no esta conforme, devuelve observaciones.
11. Si esta conforme, aprueba la accion correctiva.
12. Representante de la Gerencia asigna responsable de seguimiento/verificacion de eficacia.
13. Representante de la Gerencia define plazo o tiempo de medicion de eficacia.
14. Responsable de seguimiento mide e informa resultado.
15. Representante de la Gerencia analiza seguimiento y verifica eficacia.
16. Si no es eficaz o requiere ajuste, vuelve a accion correctiva.
17. Si esta conforme, cierra la No Conformidad.

## Campos actuales del formulario SGC-F4-AC

### Datos documentales

- Codigo: SGC-F4-AC.
- Version: 2.
- Fecha: 16-12-2024.
- Pagina 1 de 1.

### Antecedentes

Campos:

- Hallazgo N.
- Fecha deteccion.
- Fuente.
- Informado por.
- Cargo.
- Proceso.
- Descripcion del Hallazgo.
- Evidencia objetiva.
- Clausula normativa / documento.
- Clasificacion.
- Aplica tratamiento.
- Aprobado por.
- Existe un hallazgo similar previo.
- Identificacion de AC.
- Cerrado.
- Tiene un riesgo real o potencial.
- Identificacion de Riesgo.
- Tratado.

### Correccion

Seccion asignada por el Representante de la Gerencia.

Campos:

- Asignado a.
- Fecha.
- Accion.

Interpretacion para el software:

- Esta es la primera fase de tratamiento.
- Tiene un responsable propio.
- Su objetivo es corregir el problema detectado.
- Puede ser ejecutada por una persona distinta al responsable de la accion correctiva.

### Analisis causa raiz

Seccion asociada a la accion correctiva.

Campos:

- Asignado a.
- Fecha.
- Tecnica de analisis.
- Metodo sugerido: 5 Por que.

Interpretacion para el software:

- El responsable de la accion correctiva realiza el analisis de causa raiz.
- El sistema debe soportar al menos 5 Por que e Ishikawa como tecnicas de analisis.
- Debe permitir subir evidencia.
- Debe permitir registrar la accion definida para evitar recurrencia.

### Accion correctiva / Oportunidad de Mejora

Seccion asignada por el Representante de la Gerencia.

Campos:

- Asignado a.
- Fecha.
- Descripcion de accion emprendida.
- Plazo en dias habiles.
- Medio de verificacion.
- Revision de matriz de riesgos.
- Recursos empleados HH.
- Recursos empleados M$.

### Seguimiento y verificacion de efectividad

Seccion asignada por el Representante de la Gerencia a un responsable de seguimiento y verificacion de eficacia.

Campos:

- Asignado a.
- Fecha.
- Tecnica de seguimiento y verificacion.
- Requiere seguimiento adicional.
- Responsable.
- Porcentaje de efectividad.
- Notas, observaciones y comentarios.

Interpretacion para el software:

- Esta es una tercera etapa independiente.
- Debe tener responsable propio.
- Debe tener plazo o tiempo de medicion.
- Su objetivo es medir la eficacia de la accion correctiva, no ejecutar la accion.

### Ejecucion de analisis causa raiz

Campos:

- Asignado a.
- Metodo de analisis.
- P1.
- R1.
- P2.
- R2.
- P3.
- R3.
- P4.
- R4.
- P5.
- R5.
- Conclusion.

## Ajustes recomendados al software

### Entidades principales

El modelo de datos deberia separar el hallazgo en etapas:

- Hallazgo.
- Evaluacion inicial.
- Correccion.
- Accion correctiva, incluyendo analisis causa raiz, evidencia y accion para evitar recurrencia.
- Seguimiento/verificacion.
- Cierre.
- Evidencias.
- Historial.

### Campos criticos que deben existir

- Fecha deteccion.
- Fecha registro.
- Fuente.
- Proceso.
- Clausula normativa o documento.
- Evidencia objetiva.
- Clasificacion.
- Aplica tratamiento.
- Aprobado por.
- Hallazgo similar previo.
- Accion correctiva asociada.
- Riesgo real o potencial.
- Identificacion de riesgo.
- Revision de matriz de riesgos.
- Recursos HH.
- Recursos monetarios.
- Medio de verificacion.
- Porcentaje de efectividad.

### Reglas de plazo

El software debe soportar plazos en dias habiles, no solo dias corridos.

Reglas sugeridas:

- Maximo 2 dias habiles entre deteccion y notificacion.
- Plazo configurable para validacion del hallazgo.
- Plazo configurable para correccion.
- Plazo configurable para accion correctiva, incluyendo analisis causa raiz y definicion de accion.
- Plazo configurable para seguimiento/verificacion de eficacia.
- El sistema debe enviar alerta por correo 24 horas antes de que se cumpla cada plazo.
- Las alertas de 24 horas aplican a validacion, correccion, accion correctiva y verificacion de eficacia.
- Cada alerta enviada debe quedar registrada para evitar duplicidad.

### Reglas de notificacion por correo

- Cada vez que una persona genere un hallazgo, el sistema debe enviar correo al colaborador que lo genero y al Representante de la Gerencia.
- Cada vez que se asigne un responsable de fase, el sistema debe enviar correo al responsable asignado y al Representante de la Gerencia.
- Cada vez que se complete una fase del tratamiento, el sistema debe enviar correo al Representante de la Gerencia.
- Las fases que requieren notificacion son validacion, correccion, accion correctiva y seguimiento/verificacion de eficacia.
- Al crear un hallazgo, el sistema debe informar automaticamente al Encargado de Calidad / Representante de la Gerencia.
- Cuando se asignen responsables de correccion, accion correctiva o verificacion de eficacia, el sistema debe informar automaticamente a la persona asignada.

### Reglas de trazabilidad

Cada etapa debe registrar:

- Responsable asignado.
- Fecha de asignacion.
- Fecha compromiso.
- Fecha de ejecucion.
- Resultado.
- Revision del Representante de la Gerencia o rol equivalente.
- Observaciones.
- Evidencia asociada.

Regla importante:

- El responsable de correccion, el responsable de accion correctiva y el responsable de seguimiento/verificacion pueden ser personas distintas.

### Roles ajustados

- Colaborador informante.
- Representante de la Gerencia / Encargado de Calidad.
- Responsable de correccion.
- Responsable de accion correctiva.
- Responsable de seguimiento y verificacion de eficacia.
- Administrador.
- Consulta/Auditor.

## Decisiones confirmadas

- El sistema reemplazara por completo el uso operativo del formulario `SGC-F4-AC`.
- El registro `SGC-F5-CAC Control de Accion Correctiva` debe quedar dentro del software como tabla de base de datos consultable.
- El rol se debe mantener como Representante de la Gerencia.
- El Auditor Lider participa solo en algunos casos, no debe ser obligatorio para todo seguimiento.
- Salida No Conforme, Reclamo y Requerimiento se usaran solo como fuentes al momento de declarar el hallazgo.
- Los plazos se calcularan con calendario de dias habiles chileno.
- Las notificaciones automaticas del flujo son internas: Calidad y responsables asignados.
- Se deben enviar alertas por correo cada vez que se asignen responsables y cuando se complete cada fase del tratamiento.
- Se deben enviar alertas 24 horas antes del vencimiento de validacion, correccion, accion correctiva y verificacion de eficacia.
