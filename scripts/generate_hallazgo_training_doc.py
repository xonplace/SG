from __future__ import annotations

import html
import zipfile
from datetime import UTC, datetime
from pathlib import Path


OUT = Path("docs/capacitaciones/instrucciones-capacitacion-tratamiento-hallazgos.docx")

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def r(text: str, bold: bool = False, color: str | None = None, size: int | None = None) -> str:
    props = []
    if bold:
        props.append("<w:b/>")
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    if size:
        props.append(f'<w:sz w:val="{size}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f"<w:r>{rpr}<w:t>{esc(text)}</w:t></w:r>"


def p(text: str = "", style: str | None = None, bold: bool = False, color: str | None = None,
      size: int | None = None, spacing_after: int | None = None) -> str:
    parts = []
    if style:
        parts.append(f'<w:pStyle w:val="{style}"/>')
    if spacing_after is not None:
        parts.append(f'<w:spacing w:after="{spacing_after}"/>')
    ppr = f"<w:pPr>{''.join(parts)}</w:pPr>" if parts else ""
    return f"<w:p>{ppr}{r(text, bold=bold, color=color, size=size)}</w:p>"


def bullet(text: str, level: int = 0) -> str:
    return (
        "<w:p><w:pPr>"
        '<w:numPr><w:ilvl w:val="%d"/><w:numId w:val="1"/></w:numPr>'
        '<w:spacing w:after="80"/><w:ind w:left="540" w:hanging="270"/>'
        "</w:pPr>"
        f"{r(text)}"
        "</w:p>"
    ) % level


def numbered(text: str, level: int = 0) -> str:
    return (
        "<w:p><w:pPr>"
        '<w:numPr><w:ilvl w:val="%d"/><w:numId w:val="2"/></w:numPr>'
        '<w:spacing w:after="80"/><w:ind w:left="540" w:hanging="270"/>'
        "</w:pPr>"
        f"{r(text)}"
        "</w:p>"
    ) % level


def cell(content: str, width: int, fill: str | None = None, bold: bool = False) -> str:
    shading = f'<w:shd w:fill="{fill}"/>' if fill else ""
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shading}'
        '<w:tcMar><w:top w:w="100" w:type="dxa"/><w:left w:w="140" w:type="dxa"/>'
        '<w:bottom w:w="100" w:type="dxa"/><w:right w:w="140" w:type="dxa"/></w:tcMar>'
        "</w:tcPr>"
        f"{p(content, bold=bold)}"
        "</w:tc>"
    )


def table(headers: list[str], rows: list[list[str]], widths: list[int]) -> str:
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    out = [
        '<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/>'
        '<w:tblInd w:w="120" w:type="dxa"/>'
        '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="D9E2F3"/>'
        '<w:left w:val="single" w:sz="4" w:color="D9E2F3"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="D9E2F3"/>'
        '<w:right w:val="single" w:sz="4" w:color="D9E2F3"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="D9E2F3"/>'
        '<w:insideV w:val="single" w:sz="4" w:color="D9E2F3"/></w:tblBorders>'
        "</w:tblPr>",
        f"<w:tblGrid>{grid}</w:tblGrid>",
        "<w:tr>" + "".join(cell(h, w, fill="E8EEF5", bold=True) for h, w in zip(headers, widths)) + "</w:tr>",
    ]
    for row in rows:
        out.append("<w:tr>" + "".join(cell(v, w) for v, w in zip(row, widths)) + "</w:tr>")
    out.append("</w:tbl>")
    return "".join(out) + p("")


def callout(title: str, body: str) -> str:
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:tblInd w:w="120" w:type="dxa"/>'
        '<w:tblBorders><w:top w:val="single" w:sz="6" w:color="B4C7E7"/>'
        '<w:left w:val="single" w:sz="6" w:color="B4C7E7"/>'
        '<w:bottom w:val="single" w:sz="6" w:color="B4C7E7"/>'
        '<w:right w:val="single" w:sz="6" w:color="B4C7E7"/></w:tblBorders></w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="9360"/></w:tblGrid><w:tr>'
        '<w:tc><w:tcPr><w:tcW w:w="9360" w:type="dxa"/><w:shd w:fill="F4F8FF"/>'
        '<w:tcMar><w:top w:w="160" w:type="dxa"/><w:left w:w="180" w:type="dxa"/>'
        '<w:bottom w:w="160" w:type="dxa"/><w:right w:w="180" w:type="dxa"/></w:tcMar></w:tcPr>'
        f'{p(title, bold=True, color="1F4D78")}{p(body)}'
        "</w:tc></w:tr></w:tbl>"
        + p("")
    )


def styles_xml() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{NS_W}">
  <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr><w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/><w:rPr><w:b/><w:color w:val="1F4D78"/><w:sz w:val="38"/></w:rPr><w:pPr><w:spacing w:after="160"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:qFormat/><w:rPr><w:color w:val="555555"/><w:sz w:val="23"/></w:rPr><w:pPr><w:spacing w:after="200"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:qFormat/><w:rPr><w:b/><w:color w:val="2E74B5"/><w:sz w:val="32"/></w:rPr><w:pPr><w:spacing w:before="360" w:after="200"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:qFormat/><w:rPr><w:b/><w:color w:val="2E74B5"/><w:sz w:val="26"/></w:rPr><w:pPr><w:spacing w:before="280" w:after="140"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:qFormat/><w:rPr><w:b/><w:color w:val="1F4D78"/><w:sz w:val="24"/></w:rPr><w:pPr><w:spacing w:before="200" w:after="100"/></w:pPr></w:style>
</w:styles>'''


def numbering_xml() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="{NS_W}">
  <w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="hybridMultilevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="540" w:hanging="270"/></w:pPr></w:lvl></w:abstractNum>
  <w:abstractNum w:abstractNumId="2"><w:multiLevelType w:val="hybridMultilevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="540" w:hanging="270"/></w:pPr></w:lvl></w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num>
  <w:num w:numId="2"><w:abstractNumId w:val="2"/></w:num>
</w:numbering>'''


def document_xml() -> str:
    body: list[str] = []
    body.append(p("Instrucciones de capacitación", style="Title"))
    body.append(p("Tratamiento de hallazgos en el Sistema de Gestión", style="Subtitle"))
    body.append(callout(
        "Propósito del documento",
        "Entregar una guía clara para capacitar a colaboradores, responsables asignados y Representante de la Gerencia en el flujo completo de registro, tratamiento, seguimiento y cierre de hallazgos del SGC.",
    ))
    body.append(table(
        ["Dato", "Descripción"],
        [
            ["Empresa", "Tecnodata S.A."],
            ["Sistema", "Portal del Sistema de Gestión de Calidad"],
            ["Norma de referencia", "ISO 9001:2015"],
            ["Duración sugerida", "30 a 45 minutos de capacitación, más ejercicio práctico"],
            ["Resultado esperado", "Que el usuario sepa registrar un hallazgo, comprender su flujo y cargar evidencia en la etapa que le corresponde."],
        ],
        [2200, 7160],
    ))

    body.append(p("1. Objetivo de aprendizaje", style="Heading1"))
    body.append(p("Al finalizar la capacitación, los participantes deberán ser capaces de:"))
    for item in [
        "Distinguir entre hallazgo, No Conformidad y Oportunidad de Mejora.",
        "Registrar un hallazgo con información verificable y evidencia objetiva.",
        "Comprender qué hace el Representante de la Gerencia en la validación, clasificación, revisión y cierre.",
        "Identificar las responsabilidades de corrección, acción correctiva, oportunidad de mejora y verificación de eficacia.",
        "Consultar sus tareas pendientes, cargar evidencia y responder observaciones cuando una etapa sea devuelta.",
    ]:
        body.append(bullet(item))

    body.append(p("2. Mensaje central para la capacitación", style="Heading1"))
    body.append(callout(
        "Idea clave",
        "Un hallazgo no es solo un registro. Es un flujo controlado que permite validar una situación, corregirla cuando corresponde, analizar causa raíz, definir acciones, verificar eficacia y cerrar con trazabilidad.",
    ))

    body.append(p("3. Roles principales", style="Heading1"))
    body.append(table(
        ["Rol", "Responsabilidad dentro del sistema"],
        [
            ["Colaborador", "Reporta el hallazgo, describe la situación detectada y adjunta evidencia cuando exista."],
            ["Representante de la Gerencia", "Valida si aplica tratamiento, clasifica como NC u OM, asigna responsables, revisa conformidad y cierra."],
            ["Responsable de corrección", "Ejecuta la acción inmediata para controlar el efecto detectado en una No Conformidad."],
            ["Responsable de acción correctiva", "Analiza causa raíz, define la acción correctiva y carga evidencia para evitar recurrencia."],
            ["Responsable de oportunidad de mejora", "Propone y documenta el plan de acción cuando el hallazgo se clasifica como OM."],
            ["Responsable de seguimiento", "Verifica eficacia, registra el resultado, observaciones y evidencia de seguimiento."],
        ],
        [2600, 6760],
    ))

    body.append(p("4. Flujo general del tratamiento", style="Heading1"))
    steps = [
        "Registro: el colaborador informa una situación verificable. El sistema asigna un código inicial H001, H002, etc.",
        "Validación: el Representante de la Gerencia decide si el hallazgo aplica o no aplica para tratamiento.",
        "Clasificación: si aplica, se clasifica como No Conformidad u Oportunidad de Mejora. El código cambia a NC001 u OM001.",
        "Asignación: si es No Conformidad se asigna corrección; si es Oportunidad de Mejora se asigna responsable del plan de acción.",
        "Tratamiento: se registran acciones, análisis, plan o causa raíz según corresponda, siempre con evidencia.",
        "Seguimiento y verificación: se mide si la acción implementada fue eficaz.",
        "Cierre: el Representante de la Gerencia revisa conformidad, evidencia y decide el cierre o devolución.",
    ]
    for item in steps:
        body.append(numbered(item))

    body.append(p("5. Registro inicial del hallazgo", style="Heading1"))
    body.append(p("El registro inicial debe ser simple, pero suficientemente claro para permitir la validación. La recomendación para los usuarios es describir hechos, no opiniones."))
    for item in [
        "Descripción del hallazgo: qué ocurrió, dónde ocurrió y cómo fue detectado.",
        "Fecha de detección.",
        "Datos del informante.",
        "Área y proceso asociado.",
        "Fuente del hallazgo, por ejemplo auditoría, reclamo o detección interna.",
        "Evidencia objetiva en texto y, si corresponde, archivo adjunto.",
    ]:
        body.append(bullet(item))
    body.append(callout(
        "Consejo para el relator",
        "Muestre un ejemplo bueno y uno débil. Ejemplo débil: 'hubo problemas'. Ejemplo bueno: 'El 06-07-2026 se detectó una nota de venta despachada sin número de contrato asociado, en el proceso de habilitación'.",
    ))

    body.append(p("6. Validación por el Representante de la Gerencia", style="Heading1"))
    body.append(p("El Representante de la Gerencia revisa el registro y decide si corresponde tratamiento dentro del SGC."))
    body.append(table(
        ["Decisión", "Resultado esperado"],
        [
            ["No aplica", "Se cierra el hallazgo indicando respuesta o justificación. Queda trazabilidad de la decisión."],
            ["Aplica como No Conformidad", "Se genera código NC y se inicia tratamiento con corrección, acción correctiva y verificación."],
            ["Aplica como Oportunidad de Mejora", "Se genera código OM y se asigna un responsable para proponer plan de acción."],
        ],
        [2600, 6760],
    ))

    body.append(p("7. Tratamiento cuando es No Conformidad", style="Heading1"))
    body.append(p("Una No Conformidad requiere tratar el efecto detectado y luego trabajar sobre la causa para evitar recurrencia."))
    body.append(table(
        ["Etapa", "Responsable", "Qué debe registrar"],
        [
            ["Corrección", "Responsable de corrección", "Acción inmediata realizada, fecha, observaciones y evidencia."],
            ["Revisión de corrección", "Representante de la Gerencia", "Aprobación o devolución con observaciones."],
            ["Acción correctiva", "Responsable de acción correctiva", "Método de análisis, causa raíz, acción correctiva determinada, medio de verificación, recursos y evidencia."],
            ["Revisión de acción correctiva", "Representante de la Gerencia", "Conformidad del análisis y autorización para seguimiento."],
        ],
        [2300, 2600, 4460],
    ))
    body.append(p("Para el análisis de causa raíz, el sistema permite usar 5 Por Qué o un método libre, por ejemplo Ishikawa. Si se usa 5 Por Qué, al menos una pregunta y respuesta debe quedar documentada."))

    body.append(p("8. Tratamiento cuando es Oportunidad de Mejora", style="Heading1"))
    body.append(p("Una Oportunidad de Mejora no requiere corrección inicial. El foco está en proponer, revisar, implementar y verificar un plan de acción."))
    body.append(table(
        ["Etapa", "Responsable", "Qué debe registrar"],
        [
            ["Asignación de OM", "Representante de la Gerencia", "Responsable del plan y plazo definido."],
            ["Plan de acción", "Responsable de oportunidad de mejora", "Plan propuesto, medio de verificación, recursos, observaciones y evidencia."],
            ["Revisión del plan", "Representante de la Gerencia", "Aprobación o devolución con observaciones."],
            ["Seguimiento", "Responsable de seguimiento", "Resultado de implementación, eficacia, evidencia y comentarios."],
        ],
        [2300, 2600, 4460],
    ))

    body.append(p("9. Seguimiento y verificación de eficacia", style="Heading1"))
    body.append(p("El seguimiento permite comprobar si la acción fue efectiva. No basta con declarar que se hizo; se debe demostrar el resultado."))
    for item in [
        "El Representante de la Gerencia asigna responsable y plazo.",
        "El responsable registra técnica de seguimiento y criterio de medición de eficacia.",
        "Se adjunta evidencia del seguimiento.",
        "Si el resultado no es eficaz, el Representante puede devolver el flujo a la etapa que corresponda para ajustar acciones.",
    ]:
        body.append(bullet(item))

    body.append(p("10. Cierre del hallazgo", style="Heading1"))
    body.append(p("El cierre lo realiza el Representante de la Gerencia una vez revisada la conformidad del tratamiento, la evidencia y el resultado de la verificación. Si la evidencia no es suficiente o el tratamiento no fue eficaz, el hallazgo no debe cerrarse: se devuelve con observaciones para corregir el flujo."))

    body.append(p("11. Uso de evidencias", style="Heading1"))
    body.append(p("La evidencia debe cargarse en la etapa correcta. El sistema identifica la etapa para evitar confusiones y mantener trazabilidad."))
    for item in [
        "Registro inicial: evidencia objetiva del hallazgo.",
        "Corrección: evidencia de la acción inmediata ejecutada.",
        "Acción correctiva: evidencia del análisis, definición o implementación de la acción.",
        "Oportunidad de mejora: evidencia del plan de acción o de su implementación.",
        "Seguimiento: evidencia de la medición de eficacia.",
    ]:
        body.append(bullet(item))

    body.append(p("12. Errores frecuentes que se deben evitar", style="Heading1"))
    for item in [
        "Registrar descripciones demasiado generales.",
        "Confundir corrección con acción correctiva.",
        "Cerrar sin evidencia suficiente.",
        "Asignar corrección en una Oportunidad de Mejora.",
        "Registrar seguimiento en blanco o sin criterio de eficacia.",
        "Subir evidencia en una etapa que no corresponde.",
    ]:
        body.append(bullet(item))

    body.append(p("13. Ejercicio práctico sugerido", style="Heading1"))
    body.append(p("Durante la capacitación, se recomienda simular el siguiente caso:"))
    body.append(callout(
        "Caso de práctica",
        "Se detecta que un despacho a cliente fue realizado sin contar con el número de contrato asociado. El participante debe registrar el hallazgo, clasificarlo como No Conformidad, proponer corrección, realizar análisis 5 Por Qué y definir evidencia para la verificación.",
    ))

    body.append(p("14. Evaluación rápida", style="Heading1"))
    body.append(p("Para validar comprensión, usar las siguientes preguntas. La aprobación sugerida es 60%."))
    body.append(table(
        ["Pregunta", "Respuesta esperada"],
        [
            ["¿Qué información debe registrar inicialmente un colaborador?", "Descripción verificable, fecha, proceso/fuente y evidencia objetiva."],
            ["¿Qué define el Representante de la Gerencia en la validación?", "Si aplica tratamiento y si se clasifica como NC u OM."],
            ["Si el hallazgo es NC, ¿qué se asigna inicialmente?", "Un responsable de corrección."],
            ["¿Qué realiza el responsable de acción correctiva?", "Analiza causa raíz y define la acción correctiva."],
            ["¿Qué busca la verificación de eficacia?", "Comprobar si la acción fue efectiva y dejar evidencia."],
        ],
        [4300, 5060],
    ))

    body.append(p("15. Cierre sugerido para el relator", style="Heading1"))
    body.append(p("El tratamiento de hallazgos fortalece el Sistema de Gestión de Calidad porque convierte cada situación detectada en una oportunidad controlada de corrección, aprendizaje, mejora y prevención."))

    sect = (
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" '
        'w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{NS_W}" xmlns:r="{NS_R}">
  <w:body>
    {''.join(body)}
    {sect}
  </w:body>
</w:document>'''


def content_types_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''


def rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def document_rels_xml() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="{NS_R}/styles" Target="styles.xml"/>
  <Relationship Id="rId2" Type="{NS_R}/numbering" Target="numbering.xml"/>
</Relationships>'''


def core_xml() -> str:
    created = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Instrucciones de capacitación - Tratamiento de hallazgos</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>'''


def app_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
</Properties>'''


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml())
        z.writestr("_rels/.rels", rels_xml())
        z.writestr("word/document.xml", document_xml())
        z.writestr("word/_rels/document.xml.rels", document_rels_xml())
        z.writestr("word/styles.xml", styles_xml())
        z.writestr("word/numbering.xml", numbering_xml())
        z.writestr("docProps/core.xml", core_xml())
        z.writestr("docProps/app.xml", app_xml())
    print(OUT.resolve())


if __name__ == "__main__":
    main()
