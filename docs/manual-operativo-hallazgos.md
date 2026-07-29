# Manual operativo - Modulo Hallazgos

## Objetivo

Este manual explica el uso del modulo de hallazgos del Portal SGC para registrar, validar, tratar, hacer seguimiento y cerrar hallazgos del Sistema de Gestion de Calidad.

El modulo busca asegurar trazabilidad, responsables definidos, control de plazos, evidencias y cierre formal de cada situacion detectada.

## Roles principales

### Colaborador

Puede registrar un hallazgo desde el portal. Debe describir la situacion detectada con claridad y adjuntar evidencia cuando exista.

### Representante de la Gerencia

Valida si el hallazgo aplica o no aplica para tratamiento. Si aplica, clasifica el hallazgo, asigna responsables, revisa las etapas y decide el cierre.

### Responsable de Correccion

Ejecuta la correccion inmediata de una No Conformidad. Esta etapa controla o corrige el efecto detectado.

### Responsable de Accion Correctiva

Realiza el analisis de causa raiz, define la accion correctiva y registra evidencia. Aplica para No Conformidades.

### Responsable de Oportunidad de Mejora

Propone el plan de accion para implementar una Oportunidad de Mejora.

### Responsable de Seguimiento

Realiza la verificacion de eficacia o seguimiento. Debe registrar tecnica, criterio, resultado, porcentaje de efectividad y evidencia cuando corresponda.

## Nomenclatura

Cuando se registra un hallazgo, el sistema asigna un codigo inicial:

- `H001`, `H002`, `H003`, etc.

Cuando el Representante de la Gerencia valida y clasifica el hallazgo:

- No Conformidad: `NC001`, `NC002`, etc.
- Oportunidad de Mejora: `OM001`, `OM002`, etc.

## Flujo general

1. Registro del hallazgo.
2. Validacion por Representante de la Gerencia.
3. Clasificacion como No Conformidad u Oportunidad de Mejora.
4. Tratamiento segun clasificacion.
5. Revision por Representante de la Gerencia.
6. Seguimiento y verificacion de eficacia.
7. Cierre.

## Registro del hallazgo

El colaborador debe completar:

- Descripcion del hallazgo.
- Fecha de deteccion.
- Fuente.
- Area.
- Proceso.
- Evidencia objetiva.
- Archivo de evidencia, si existe.
- Datos del informante.

Recomendacion: registrar hechos verificables, evitando opiniones generales. Mientras mas clara sea la descripcion, mas rapida sera la validacion.

Al guardar, el sistema:

- Crea el hallazgo con codigo `H`.
- Lo deja en estado `Ingresado`.
- Lo deja disponible para validacion del Representante de la Gerencia.

## Validacion inicial

El Representante de la Gerencia revisa el hallazgo y define si aplica tratamiento.

### Si no aplica

Debe registrar el motivo. El hallazgo queda cerrado como `Cerrado no aplica`.

### Si aplica

Debe clasificarlo como:

- No Conformidad Mayor.
- No Conformidad Menor.
- Oportunidad de Mejora.

Tambien puede indicar clausula normativa o documento relacionado.

## Flujo para No Conformidad

### 1. Asignar correccion

El Representante de la Gerencia asigna un responsable de correccion y registra la accion solicitada.

La correccion corresponde a la accion inmediata para controlar el efecto detectado.

### 2. Registrar correccion

El responsable de correccion debe registrar:

- Detalle de la correccion aplicada.
- Evidencia de la correccion, si corresponde.

No debe quedar en blanco. El sistema exige registrar el detalle de la correccion.

### 3. Revisar correccion

El Representante de la Gerencia revisa si la correccion esta conforme.

- Si esta conforme, continua a accion correctiva.
- Si no esta conforme, debe registrar observaciones y devolver la etapa al responsable.

### 4. Asignar accion correctiva

El Representante de la Gerencia asigna un responsable para la accion correctiva.

La accion correctiva busca eliminar la causa raiz para evitar recurrencia.

### 5. Registrar accion correctiva

El responsable debe registrar:

- Metodo de analisis.
- Conclusion o causa raiz.
- Accion correctiva definida.
- Medio de verificacion.
- Analisis de riesgo, si aplica.
- Recursos HH y/o M$, si aplica.

Metodos disponibles:

- `5 Por que`: requiere al menos una pregunta y respuesta completas.
- `Libre`: permite registrar otro analisis, por ejemplo Ishikawa.

### 6. Revisar accion correctiva

El Representante de la Gerencia define si la accion esta conforme.

- Si esta conforme, asigna seguimiento.
- Si no esta conforme, registra observaciones y devuelve al responsable.

## Flujo para Oportunidad de Mejora

Cuando el hallazgo se clasifica como Oportunidad de Mejora, no se asigna correccion.

El Representante de la Gerencia asigna un responsable para proponer el plan de accion.

### 1. Registrar plan de accion

El responsable debe registrar:

- Plan de accion propuesto.
- Medio de verificacion de la implementacion.
- Observaciones o analisis complementario, si aplica.
- Recursos HH y/o M$, si aplica.

### 2. Revisar plan de accion

El Representante de la Gerencia revisa el plan.

- Si esta conforme, autoriza continuar a seguimiento.
- Si no esta conforme, registra observaciones y devuelve al responsable.

## Seguimiento y verificacion de eficacia

El Representante de la Gerencia asigna un responsable del seguimiento y define el plazo.

El responsable de seguimiento debe registrar:

- Tecnica de seguimiento.
- Criterio de medicion de eficacia.
- Resultado.
- Porcentaje de efectividad.
- Si corresponde seguimiento adicional.
- Responsable y plazo de segundo seguimiento, si aplica.

El seguimiento no debe registrarse en blanco. El sistema exige tecnica, criterio, resultado y porcentaje.

## Revision del seguimiento y cierre

El Representante de la Gerencia revisa si el seguimiento fue eficaz.

### Si fue eficaz

Puede cerrar el hallazgo. El estado queda `Cerrado`.

### Si no fue eficaz

Debe registrar observaciones. El sistema impide cerrar el hallazgo si el seguimiento no fue eficaz.

Segun el caso, se debe revisar nuevamente el plan de accion, la accion correctiva o definir un seguimiento adicional.

## Estados principales

- `Ingresado`: hallazgo registrado, pendiente de validacion.
- `En validacion`: en revision por el Representante de la Gerencia.
- `Cerrado no aplica`: el hallazgo no requiere tratamiento.
- `Clasificado`: aplica tratamiento y ya fue clasificado.
- `Correccion asignada`: responsable de correccion definido.
- `En correccion`: correccion en ejecucion.
- `Correccion en revision`: correccion enviada al Representante.
- `Correccion aprobada`: correccion conforme.
- `Accion correctiva asignada`: responsable de accion correctiva o plan de accion definido.
- `Accion correctiva en revision`: accion o plan enviado a revision.
- `Accion correctiva aprobada`: accion o plan conforme.
- `Seguimiento asignado`: responsable de seguimiento definido.
- `Seguimiento en revision`: seguimiento enviado al Representante.
- `Cerrado`: hallazgo finalizado.

## Evidencias

Las evidencias pueden cargarse en las etapas correspondientes:

- Registro inicial.
- Correccion.
- Accion correctiva o plan de accion.
- Seguimiento.

Solo deben cargar evidencia los usuarios autorizados para la etapa o el Representante de la Gerencia.

## Plazos

El sistema administra plazos para:

- Validacion.
- Correccion.
- Revision de correccion.
- Accion correctiva o plan de accion.
- Revision de accion correctiva o plan.
- Seguimiento y verificacion de eficacia.

Los plazos se definen desde mantenedores y se calculan en dias habiles segun la etapa.

## Recomendaciones de uso

- Registrar hechos concretos y verificables.
- Adjuntar evidencia siempre que sea posible.
- No cerrar hallazgos sin revisar eficacia.
- Registrar observaciones cuando una etapa no este conforme.
- Usar `Mis tareas` para revisar pendientes personales.
- Usar `Vencidos` para controlar atrasos.
- Usar reportes para seguimiento gerencial.
