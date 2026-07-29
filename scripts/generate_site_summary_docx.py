from __future__ import annotations

import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import get_resolver

from apps.core.models import AuditLog, CompanyProfile, RolePermission, SystemHelpContent
from apps.findings.models import Finding
from apps.findings.permissions import PERMISSION_DEFINITIONS
from apps.sgc.models import (
    IsoCertificate,
    SgcDocument,
    SgcImportantDates,
    SgcOfficialForm,
    SgcProcess,
    SgcUpdate,
)


BASE_DIR = Path(settings.BASE_DIR)
OUTPUT = BASE_DIR / "docs" / "Resumen-completo-Portal-SGC-Tecnodata.docx"


def xml(text: object) -> str:
    return escape("" if text is None else str(text))


def para(text: str = "", style: str | None = None, bold: bool = False) -> str:
    style_xml = f'<w:pStyle w:val="{style}"/>' if style else ""
    bold_xml = "<w:b/>" if bold else ""
    return (
        "<w:p>"
        f"<w:pPr>{style_xml}</w:pPr>"
        "<w:r>"
        f"<w:rPr>{bold_xml}</w:rPr>"
        f"<w:t xml:space=\"preserve\">{xml(text)}</w:t>"
        "</w:r>"
        "</w:p>"
    )


def bullet(text: str) -> str:
    return (
        '<w:p><w:pPr><w:pStyle w:val="ListParagraph"/>'
        '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{xml(text)}</w:t></w:r></w:p>'
    )


def table(rows: list[list[object]]) -> str:
    out = [
        '<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/>'
        '<w:tblW w:w="0" w:type="auto"/></w:tblPr>'
    ]
    for row_index, row in enumerate(rows):
        out.append("<w:tr>")
        for cell in row:
            bold_xml = "<w:b/>" if row_index == 0 else ""
            out.append(
                "<w:tc><w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>"
                "<w:p><w:r>"
                f"<w:rPr>{bold_xml}</w:rPr>"
                f"<w:t xml:space=\"preserve\">{xml(cell)}</w:t>"
                "</w:r></w:p></w:tc>"
            )
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    return 1200, 700


def image_paragraph(rid: str, path: Path, width_in: float = 6.2) -> str:
    width, height = png_size(path)
    cx = int(width_in * 914400)
    cy = int(cx * height / max(width, 1))
    name = xml(path.name)
    return f"""
    <w:p>
      <w:pPr><w:jc w:val="center"/></w:pPr>
      <w:r>
        <w:drawing>
          <wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
            <wp:extent cx="{cx}" cy="{cy}"/>
            <wp:docPr id="1" name="{name}"/>
            <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
                  <pic:nvPicPr><pic:cNvPr id="0" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>
                  <pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
                  <pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:inline>
        </w:drawing>
      </w:r>
    </w:p>
    """


def flatten_urlpatterns(patterns, prefix=""):
    rows = []
    for pattern in patterns:
        if hasattr(pattern, "url_patterns"):
            rows.extend(flatten_urlpatterns(pattern.url_patterns, prefix + str(pattern.pattern)))
        else:
            rows.append((prefix + str(pattern.pattern), getattr(pattern, "name", "")))
    return rows


def model_rows(model):
    rows = [["Campo", "Tipo", "Obligatorio", "Notas"]]
    for field in model._meta.fields:
        rows.append(
            [
                field.name,
                field.__class__.__name__,
                "No" if getattr(field, "blank", False) or getattr(field, "null", False) else "Si",
                getattr(field, "verbose_name", "") or "",
            ]
        )
    return rows


def metrics_rows():
    User = get_user_model()
    return [
        ["Indicador", "Cantidad actual"],
        ["Hallazgos", Finding.objects.count()],
        ["Documentos SGC", SgcDocument.objects.count()],
        ["Formularios oficiales", SgcOfficialForm.objects.count()],
        ["Procesos publicados", SgcProcess.objects.count()],
        ["Certificados ISO", IsoCertificate.objects.count()],
        ["Comunicados", SgcUpdate.objects.count()],
        ["Capacitaciones / ayuda", SystemHelpContent.objects.count()],
        ["Usuarios", User.objects.count()],
        ["Roles Django", Group.objects.count()],
        ["Permisos configurables", RolePermission.objects.count()],
        ["Registros de auditoria", AuditLog.objects.count()],
    ]


def build_document() -> tuple[str, list[Path]]:
    company = CompanyProfile.current()
    today = datetime.now().strftime("%d-%m-%Y %H:%M")
    images = [
        BASE_DIR / "docs/notebooklm-hallazgos/capturas/01_portada.png",
        BASE_DIR / "docs/notebooklm-hallazgos/capturas/02_login.png",
        BASE_DIR / "docs/notebooklm-hallazgos/capturas/03_inicio_sgc.png",
        BASE_DIR / "docs/notebooklm-hallazgos/capturas/04_registro_hallazgo.png",
        BASE_DIR / "docs/notebooklm-hallazgos/capturas/05_bandeja_hallazgos.png",
        BASE_DIR / "docs/notebooklm-hallazgos/capturas/06_detalle_hallazgo.png",
        BASE_DIR / "docs/notebooklm-hallazgos/capturas/07_carga_evidencia.png",
        BASE_DIR / "static/img/iso-compromiso-calidad.png",
    ]
    images = [path for path in images if path.exists()]

    body: list[str] = []
    body.append(para("Resumen completo del Portal SGC Tecnodata", "Title"))
    body.append(para("Documento de contexto funcional, tecnico y visual para entregar a una inteligencia artificial y obtener nuevas ideas de evolucion del sitio.", bold=True))
    body.append(para(f"Generado: {today}"))
    body.append(para(f"Empresa configurada: {company.company_name}"))
    body.append(para(f"Nombre del sistema: {company.system_name}"))
    body.append(page_break())

    body.append(para("1. Proposito del sistema", "Heading1"))
    body.append(para("El Portal SGC es una aplicacion web para centralizar la administracion del Sistema de Gestion de Calidad de Tecnodata S.A. Su objetivo es reemplazar gradualmente archivos y carpetas dispersas por un sitio trazable, parametrizable y accesible para usuarios internos."))
    body.append(para("El sistema administra hallazgos, control documental, procesos, formularios oficiales, certificado ISO, comunicados, capacitaciones, politica de calidad, mision, vision, auditoria y permisos."))
    body.append(para("Objetivos principales", "Heading2"))
    for item in [
        "Centralizar informacion oficial del Sistema de Gestion de Calidad.",
        "Controlar el ciclo completo de hallazgos, no conformidades y oportunidades de mejora.",
        "Administrar documentos vigentes, obsoletos, versiones y listado maestro documental.",
        "Publicar procesos con control de versiones, imagenes de flujo y archivos descargables.",
        "Disponibilizar formularios oficiales vigentes y destacados.",
        "Permitir personalizacion por empresa para una futura comercializacion del software.",
        "Dar trazabilidad a acciones, responsables, plazos, evidencias, permisos y auditoria.",
    ]:
        body.append(bullet(item))

    body.append(para("2. Stack tecnologico", "Heading1"))
    body.append(table([
        ["Componente", "Tecnologia / decision"],
        ["Lenguaje principal", "Python 3.12"],
        ["Framework backend", "Django 5"],
        ["Base de datos", "PostgreSQL 16 en Docker Compose; SQLite como fallback local por DATABASE_URL"],
        ["Frontend", "Plantillas Django + Tailwind CSS compilado a static/css/output.css"],
        ["Autenticacion", "Django Auth con usuarios, grupos y matriz de permisos propia"],
        ["Archivos", "MEDIA_ROOT local, con subcarpetas para documentos, procesos, evidencias, logos y certificado"],
        ["Servidor desarrollo", "Django runserver en Docker, expuesto en 0.0.0.0:8000"],
        ["Variables de entorno", ".env con DJANGO_ALLOWED_HOSTS, DATABASE_URL, correo SMTP y parametros"],
        ["Estilos", "Inter como fuente principal, paleta corporativa configurable desde mantenedor"],
        ["Auditoria", "Modelo AuditLog interno para registrar acciones relevantes"],
        ["Notificaciones", "Estructura preparada; SMTP real postergado hasta contar con credenciales Office 365"],
    ]))

    body.append(para("3. Arquitectura general", "Heading1"))
    for item in [
        "config: configuracion Django, rutas raiz, settings, WSGI/ASGI.",
        "apps.core: perfil de empresa, identidad visual, politica/mision/vision, auditoria, contenidos de ayuda/capacitacion, permisos configurables.",
        "apps.accounts: usuarios, perfil, gestion de usuarios.",
        "apps.findings: hallazgos, flujo de estados, responsables, evidencias, reportes, plazos, permisos funcionales.",
        "apps.sgc: biblioteca documental, listado maestro, certificados, comunicados, procesos, formularios, fechas importantes y capacitaciones.",
        "apps.maintainers: mantenedores de parametros maestros, identidad SGC, plazos, auditoria y matriz de permisos.",
        "templates: interfaz en plantillas Django.",
        "static: CSS compilado, assets visuales e imagen ISO.",
        "media: archivos cargados por usuarios y datos operativos.",
    ]:
        body.append(bullet(item))

    body.append(para("4. Estado actual de datos", "Heading1"))
    body.append(table(metrics_rows()))

    body.append(para("5. Modulos funcionales", "Heading1"))
    modules = [
        ("Portada publica", "Pantalla previa al login. Presenta el portal, el alcance ISO, opcion de registrar hallazgo e ingreso al sitio."),
        ("Login", "Ingreso seguro de usuarios autorizados. Redirige a Inicio SGC."),
        ("Inicio SGC", "Pagina central autenticada con metricas, alcance, certificado vigente, comunicados, documentos por clausula y fechas importantes."),
        ("Hallazgos", "Registro, validacion, clasificacion, correccion, accion correctiva, oportunidad de mejora, seguimiento, cierre, evidencias, reportes y tablero de tareas."),
        ("Biblioteca documental", "Documentos vigentes por clausula Anexo SL, filtros, descarga, vista, control documental, versiones, obsolescencia y eliminacion controlada."),
        ("Matriz documental - Listado Maestro de Documentos", "Vista maestra para controlar tipo, clausula, version, vigencia, estado, archivo, historial y exportacion CSV."),
        ("Formularios", "Disponibiliza formularios oficiales vigentes. Permite destacar formularios principales y vincularlos opcionalmente a procesos activos."),
        ("Procesos", "Publicacion de procesos operacionales y de apoyo con versiones, prosa, imagen ampliable, archivos de flujo y versiones antiguas conservadas."),
        ("Certificado ISO", "Visualizacion, descarga e historial del certificado ISO vigente. Vencimiento configurado."),
        ("Comunicados", "Publicacion de actualizaciones internas del SGC, con opcion de mostrar en Inicio SGC."),
        ("Capacitaciones", "Contenido de ayuda/capacitacion y registro de avance por usuario."),
        ("Nuestro compromiso", "Popup desde Inicio SGC con politica de calidad, mision, vision e imagen corporativa de compromiso ISO."),
        ("Mantenedores", "Parametros maestros: empresa, logo, identidad SGC, plazos, tipos documentales, usuarios, permisos, auditoria, fechas importantes y elementos de configuracion."),
    ]
    body.append(table([["Modulo", "Descripcion"]] + modules))

    body.append(para("6. Flujo de hallazgos", "Heading1"))
    body.append(para("El flujo de hallazgos fue diseñado para reflejar el procedimiento actual de accion correctiva y oportunidades de mejora. El codigo nace como H### y, si aplica, se transforma en NC### u OM###."))
    for item in [
        "Registro inicial: cualquier colaborador registra descripcion del hallazgo, fecha, datos de informante, area, proceso, fuente, evidencia objetiva y archivo adjunto opcional.",
        "Validacion: el Representante de la Gerencia decide si aplica o no aplica. Si no aplica, cierra con justificacion.",
        "No conformidad: si aplica como NC, se separa en correccion, accion correctiva con causa raiz y seguimiento/verificacion.",
        "Oportunidad de mejora: si aplica como OM, se asigna responsable para proponer plan de accion; RG revisa, aprueba o devuelve; luego se implementa y se hace seguimiento.",
        "Correccion: accion inmediata para controlar el efecto detectado, con responsable, plazo, evidencia y revision por RG.",
        "Accion correctiva: analisis de causa raiz, metodo 5 Por Que o libre, conclusion, accion correctiva determinada, medios de verificacion, recursos y evidencia.",
        "Seguimiento: responsable verifica eficacia, registra tecnica, criterio, resultado, observaciones y evidencia.",
        "Cierre: RG cierra si el tratamiento es conforme y queda trazabilidad completa.",
    ]:
        body.append(bullet(item))

    body.append(para("7. Control documental", "Heading1"))
    for item in [
        "Los documentos se organizan por clausulas del Anexo SL: 1 Alcance, 2 Referencias normativas, 3 Terminos y definiciones, 4 Contexto, 5 Liderazgo, 6 Planificacion, 7 Apoyo, 8 Operacion, 9 Evaluacion del desempeno y 10 Mejora.",
        "Cada documento puede tener codigo, version, tipo documental, fecha de vigencia, estado, archivo, eventos e historial.",
        "Los documentos externos complementarios pueden existir sin codigo o sin version.",
        "La baja documental no elimina automaticamente: el documento pasa a obsoleto y solo administradores/RG pueden eliminar desde mantenedor.",
        "El listado maestro documental permite exportacion CSV.",
        "La clasificacion automatica reconoce patrones: DF como Diagrama de flujo, DI como Documento interno, F+numero como Formulario, PR como Procedimiento, IT como Instructivo.",
        "La duplicidad debe controlarse por nombre completo de archivo, no solo por codigo, porque hay formularios con mismo codigo base y nombres diferentes.",
    ]:
        body.append(bullet(item))

    body.append(para("8. Procesos", "Heading1"))
    for item in [
        "Los procesos se separan en operacionales y de apoyo.",
        "Cada proceso tiene ficha compacta con codigo, nombre, responsable, tipo y estado.",
        "La version vigente incluye prosa del proceso, imagen ampliable con zoom, archivo de flujo descargable y archivos publicados.",
        "Las versiones antiguas se conservan por trazabilidad ISO; no se deben eliminar de forma ordinaria.",
        "Los procesos pueden darse de baja y pasar a procesos obsoletos, visibles en mantenedores para RG/administrador.",
        "Las versiones antiguas tienen opcion de ver prosa y ver imagen en popup.",
    ]:
        body.append(bullet(item))

    body.append(para("9. Personalizacion y comercializacion futura", "Heading1"))
    for item in [
        "El sitio esta pensado para poder venderse a otras empresas con ISO implementada.",
        "La identidad visual se controla desde mantenedores: nombre de empresa, nombre del sistema, colores, logo, labels de menu, modulos visibles y contenido de compromiso.",
        "Los permisos son configurables por rol desde una matriz administrable.",
        "Los modulos pueden activarse/desactivarse para adaptar la solucion a cada cliente.",
        "Recomendacion futura: convertir configuracion actual en modelo multiempresa/tenant si se quiere vender como SaaS.",
    ]:
        body.append(bullet(item))

    body.append(para("10. Roles y permisos", "Heading1"))
    body.append(table([["Permiso", "Nombre", "Seccion"]] + [[code, label, section] for code, label, section in PERMISSION_DEFINITIONS]))
    body.append(para("Roles actuales", "Heading2"))
    for group in Group.objects.order_by("name"):
        body.append(bullet(group.name))

    body.append(para("11. Modelo de datos principal", "Heading1"))
    for title, model in [
        ("Finding - Hallazgo", Finding),
        ("SgcDocument - Documento SGC", SgcDocument),
        ("SgcOfficialForm - Formulario oficial", SgcOfficialForm),
        ("SgcProcess - Proceso", SgcProcess),
        ("IsoCertificate - Certificado ISO", IsoCertificate),
        ("CompanyProfile - Perfil/identidad de empresa", CompanyProfile),
        ("RolePermission - Permisos por rol", RolePermission),
    ]:
        body.append(para(title, "Heading2"))
        body.append(table(model_rows(model)))

    body.append(para("12. Rutas relevantes", "Heading1"))
    routes = flatten_urlpatterns(get_resolver().url_patterns)
    selected_routes = [
        [route, name or "-"]
        for route, name in routes
        if any(key in route for key in ["sistema-gestion", "hallazgos", "mantenedores", "usuarios", "accounts"])
    ][:80]
    body.append(table([["Ruta", "Nombre"]] + selected_routes))

    body.append(para("13. Interfaz visual", "Heading1"))
    body.append(para("El sitio usa un lenguaje visual corporativo: menu lateral azul degradado, tarjetas blancas con bordes suaves, botones azules, estados con colores, fuente Inter y una experiencia ordenada tipo portal interno."))
    body.append(para("Capturas de referencia", "Heading2"))
    rels = []
    for index, path in enumerate(images, start=1):
        rid = f"rIdImg{index}"
        rels.append((rid, path))
        body.append(para(path.stem.replace("_", " ").title(), "Heading3"))
        body.append(image_paragraph(rid, path, width_in=6.3))

    body.append(page_break())
    body.append(para("14. Ideas sugeridas para pedir a otra IA", "Heading1"))
    for item in [
        "Proponer mejoras de experiencia de usuario para cada modulo sin perder sobriedad corporativa.",
        "Proponer un roadmap para transformar el portal en producto vendible a multiples empresas.",
        "Detectar brechas contra ISO 9001:2015 en control documental, hallazgos, acciones correctivas y evidencias.",
        "Diseñar un modulo de auditorias internas conectado con hallazgos y planes de accion.",
        "Diseñar un modulo de riesgos y oportunidades enlazado con procesos y matriz de riesgos.",
        "Proponer dashboard ejecutivo real que aporte informacion accionable y no duplique Inicio SGC.",
        "Proponer mejoras al modelo de permisos para una version SaaS multiempresa.",
        "Proponer estructura de capacitaciones con evaluaciones, asistencia, evidencia y vigencia.",
        "Proponer integracion con Microsoft 365, SharePoint, Power Automate y Entra ID.",
    ]:
        body.append(bullet(item))

    body.append(para("15. Prompt recomendado para entregar junto a este documento", "Heading1"))
    body.append(para("Actua como consultor senior en sistemas de gestion ISO 9001, arquitectura de software Django y diseno UX de portales corporativos. Analiza el documento adjunto sobre el Portal SGC Tecnodata. Propone mejoras funcionales, tecnicas, visuales y comerciales, priorizadas por impacto y esfuerzo. Considera que el sistema busca centralizar el SGC, administrar hallazgos, documentos, procesos, formularios, certificados, comunicados, capacitaciones y permisos, con posibilidad de venderse a otras empresas en el futuro."))

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <w:body>
        {''.join(body)}
        <w:sectPr>
          <w:pgSz w:w="12240" w:h="15840"/>
          <w:pgMar w:top="1008" w:right="1008" w:bottom="1008" w:left="1008" w:header="720" w:footer="720" w:gutter="0"/>
        </w:sectPr>
      </w:body>
    </w:document>"""
    return document_xml, [path for _rid, path in rels]


def styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
        <w:name w:val="Normal"/><w:qFormat/>
        <w:rPr><w:rFonts w:ascii="Inter" w:hAnsi="Inter"/><w:sz w:val="22"/></w:rPr>
        <w:pPr><w:spacing w:after="160" w:line="276" w:lineRule="auto"/></w:pPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Title">
        <w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/>
        <w:rPr><w:b/><w:sz w:val="44"/><w:color w:val="173A69"/></w:rPr>
        <w:pPr><w:spacing w:after="280"/></w:pPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Heading1">
        <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
        <w:rPr><w:b/><w:sz w:val="32"/><w:color w:val="1F4F91"/></w:rPr>
        <w:pPr><w:spacing w:before="280" w:after="160"/></w:pPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Heading2">
        <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
        <w:rPr><w:b/><w:sz w:val="26"/><w:color w:val="173A69"/></w:rPr>
        <w:pPr><w:spacing w:before="220" w:after="120"/></w:pPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="Heading3">
        <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
        <w:rPr><w:b/><w:sz w:val="22"/><w:color w:val="315FAE"/></w:rPr>
      </w:style>
      <w:style w:type="paragraph" w:styleId="ListParagraph">
        <w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:qFormat/>
        <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
      </w:style>
      <w:style w:type="table" w:styleId="TableGrid">
        <w:name w:val="Table Grid"/><w:uiPriority w:val="59"/><w:qFormat/>
        <w:tblPr><w:tblBorders>
          <w:top w:val="single" w:sz="4" w:space="0" w:color="D7E0EF"/>
          <w:left w:val="single" w:sz="4" w:space="0" w:color="D7E0EF"/>
          <w:bottom w:val="single" w:sz="4" w:space="0" w:color="D7E0EF"/>
          <w:right w:val="single" w:sz="4" w:space="0" w:color="D7E0EF"/>
          <w:insideH w:val="single" w:sz="4" w:space="0" w:color="D7E0EF"/>
          <w:insideV w:val="single" w:sz="4" w:space="0" w:color="D7E0EF"/>
        </w:tblBorders></w:tblPr>
      </w:style>
    </w:styles>"""


def numbering_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:abstractNum w:abstractNumId="0">
        <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>
        <w:pPr><w:tabs><w:tab w:val="num" w:pos="720"/></w:tabs><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl>
      </w:abstractNum>
      <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
    </w:numbering>"""


def write_docx():
    document_xml, images = build_document()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image_rels = []
    image_content_types = []
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
              <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
              <Default Extension="xml" ContentType="application/xml"/>
              <Default Extension="png" ContentType="image/png"/>
              <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
              <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
              <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
            </Types>""",
        )
        docx.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
            </Relationships>""",
        )
        for index, image in enumerate(images, start=1):
            rid = f"rIdImg{index}"
            target = f"media/image{index}.png"
            image_rels.append(
                f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{target}"/>'
            )
            image_content_types.append(target)
            docx.write(image, f"word/{target}")
        docx.writestr(
            "word/_rels/document.xml.rels",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
              <Relationship Id="rIdNumbering" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
              {''.join(image_rels)}
            </Relationships>""",
        )
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/styles.xml", styles_xml())
        docx.writestr("word/numbering.xml", numbering_xml())
    print(OUTPUT)


if __name__ == "__main__":
    write_docx()
