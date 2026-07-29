import base64
import html
import mimetypes
import os
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "notebooklm-hallazgos"
HTML_DIR = OUT_DIR / "html"
IMG_DIR = OUT_DIR / "capturas"
DOCX_PATH = OUT_DIR / "Guia-video-tratamiento-hallazgos-NotebookLM.docx"
MD_PATH = OUT_DIR / "instrucciones-video-tratamiento-hallazgos.md"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def setup_django():
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ["DATABASE_URL"] = "postgres://sistema_gestion:sistema_gestion@localhost:5432/sistema_gestion"
    import django

    django.setup()


def data_uri(path):
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def inline_assets(raw_html):
    css_path = ROOT / "static" / "css" / "output.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    raw_html = re.sub(
        r'<link[^>]+href="[^"]*static/css/output\.css[^"]*"[^>]*>',
        lambda _match: f"<style>{css}</style>",
        raw_html,
    )

    def replace_static(match):
        attr = match.group(1)
        url = unquote(match.group(2).split("?", 1)[0])
        asset = ROOT / url.lstrip("/")
        if asset.exists() and asset.is_file():
            return f'{attr}="{data_uri(asset)}"'
        return match.group(0)

    raw_html = re.sub(r'(src|href)="(/static/[^"]+)"', replace_static, raw_html)
    raw_html = raw_html.replace("min-h-screen", "min-h-[900px]")
    return raw_html


def save_snapshots():
    from django.contrib.auth import get_user_model
    from django.test import Client
    from apps.findings.models import Finding

    User = get_user_model()
    admin = User.objects.filter(is_superuser=True, is_active=True).first() or User.objects.filter(is_active=True).first()
    if not admin:
        raise RuntimeError("No active Django user found.")

    finding = Finding.objects.order_by("-created_at").first()
    pages = [
        ("01_portada", "Portada publica", "/", False),
        ("02_login", "Pantalla de inicio de sesion", "/cuentas/login/", False),
        ("03_inicio_sgc", "Inicio SGC", "/sistema-gestion/", True),
        ("04_registro_hallazgo", "Registro de hallazgo", "/hallazgos/nuevo/", False),
        ("05_bandeja_hallazgos", "Bandeja de hallazgos", "/hallazgos/?status=abiertos", True),
    ]
    if finding:
        pages.extend(
            [
                ("06_detalle_hallazgo", "Detalle del hallazgo y etapas", f"/hallazgos/{finding.pk}/", True),
                ("07_carga_evidencia", "Carga de evidencia por etapa", f"/hallazgos/{finding.pk}/evidencias/nueva/", True),
            ]
        )

    HTML_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for slug, title, path, auth in pages:
        client = Client(HTTP_HOST="localhost")
        if auth:
            client.force_login(admin)
        response = client.get(path, follow=True)
        if response.status_code != 200:
            continue
        content = inline_assets(response.content.decode("utf-8", errors="replace"))
        content = content.replace("</head>", f"<style>body{{zoom:.9}}</style><title>{html.escape(title)}</title></head>")
        html_path = HTML_DIR / f"{slug}.html"
        html_path.write_text(content, encoding="utf-8")
        snapshots.append((slug, title, html_path))
    return snapshots


def capture_with_edge(snapshots):
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    captures = []
    browser = CHROME if CHROME.exists() else EDGE
    if not browser.exists():
        return captures
    for slug, title, html_path in snapshots:
        image_path = IMG_DIR / f"{slug}.png"
        user_data_dir = OUT_DIR / f"edge-profile-{slug}"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        args = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-software-rasterizer",
            "--no-first-run",
            "--disable-extensions",
            "--hide-scrollbars",
            "--window-size=1440,1100",
            f"--user-data-dir={user_data_dir}",
            f"--screenshot={image_path}",
            html_path.as_uri(),
        ]
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if image_path.exists():
            captures.append((title, image_path))
    return captures


def png_size(path):
    with path.open("rb") as f:
        data = f.read(24)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return 1200, 800
    return struct.unpack(">II", data[16:24])


def esc(text):
    return html.escape(str(text), quote=False)


def p(text="", style=None):
    style_xml = f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""
    return f"<w:p>{style_xml}<w:r><w:t>{esc(text)}</w:t></w:r></w:p>"


def bullets(items):
    return "".join(p(f"- {item}") for item in items)


def image_xml(rel_id, path):
    width_px, height_px = png_size(path)
    max_width_emu = int(6.5 * 914400)
    width_emu = int(width_px / 96 * 914400)
    height_emu = int(height_px / 96 * 914400)
    if width_emu > max_width_emu:
        scale = max_width_emu / width_emu
        width_emu = max_width_emu
        height_emu = int(height_emu * scale)
    doc_pr_id = rel_id.replace("rId", "")
    return f"""
<w:p>
  <w:r>
    <w:drawing>
      <wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" distT="0" distB="0" distL="0" distR="0">
        <wp:extent cx="{width_emu}" cy="{height_emu}"/>
        <wp:docPr id="{doc_pr_id}" name="{esc(path.name)}"/>
        <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
          <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <pic:nvPicPr><pic:cNvPr id="0" name="{esc(path.name)}"/><pic:cNvPicPr/></pic:nvPicPr>
              <pic:blipFill><a:blip r:embed="{rel_id}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
              <pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{width_emu}" cy="{height_emu}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
            </pic:pic>
          </a:graphicData>
        </a:graphic>
      </wp:inline>
    </w:drawing>
  </w:r>
</w:p>
"""


def guide_text():
    return """# Instrucciones para NotebookLM: video tratamiento de hallazgos

Objetivo del video:
Crear un video explicativo para capacitar a los colaboradores de Tecnodata S.A. en el uso del portal SGC para registrar, tratar, verificar y cerrar hallazgos del Sistema de Gestion de Calidad.

Audiencia:
Colaboradores que reportan hallazgos, Representante de la Gerencia, responsables de correccion, responsables de accion correctiva y responsables de verificacion de eficacia.

Duracion sugerida:
6 a 8 minutos.

Tono:
Profesional, claro, cercano y orientado a capacitacion interna. Usar lenguaje simple, sin tecnicismos innecesarios. Explicar cada rol y cada etapa como parte de un flujo controlado del SGC.

Mensaje central:
El hallazgo no es solo un registro. Es un flujo controlado que permite validar una situacion, corregirla, analizar su causa raiz, definir acciones para evitar recurrencia, verificar eficacia y cerrar con evidencia.

Estructura sugerida del video:

1. Bienvenida e introduccion al portal SGC
- Presentar el portal como la plataforma central del Sistema de Gestion.
- Explicar que permite registrar hallazgos, administrar documentos, revisar informacion ISO y mantener trazabilidad.
- Indicar que cualquier colaborador puede registrar un hallazgo.

2. Registro inicial del hallazgo
- Explicar que el colaborador debe ingresar una descripcion clara del hallazgo.
- Incluir fecha de deteccion, datos del informante, area, proceso, fuente y evidencia objetiva cuando exista.
- Aclarar que el sistema asigna un codigo inicial H001, H002, etc.
- Al registrar, el sistema debe informar al colaborador y al Representante de la Gerencia.

3. Validacion por el Representante de la Gerencia
- El Representante de la Gerencia revisa si el hallazgo aplica o no aplica para tratamiento.
- Si no aplica, debe cerrar el hallazgo indicando la respuesta o justificacion.
- Si aplica, debe clasificarlo como No Conformidad u Oportunidad de Mejora.
- Al aprobarlo, el codigo cambia a NC001 para No Conformidades u OM001 para Oportunidades de Mejora.
- Luego asigna responsable y plazo para la correccion.

4. Tratamiento de la correccion
- La correccion es la accion inmediata para controlar o resolver el efecto detectado.
- Puede ser realizada por una persona distinta al responsable de la accion correctiva.
- El responsable de correccion registra la accion realizada y carga evidencia.
- El Representante de la Gerencia revisa y aprueba o devuelve la correccion.

5. Accion correctiva y analisis de causa raiz
- Esta etapa busca eliminar la causa para evitar que el problema vuelva a ocurrir.
- El responsable de accion correctiva realiza analisis de causa raiz.
- Metodos disponibles: 5 Por Que o texto libre para otro metodo, como Ishikawa.
- Debe cargar evidencia, documentar la causa raiz y definir la accion correctiva.
- El Representante de la Gerencia revisa y aprueba la accion correctiva.

6. Verificacion de eficacia
- El Representante de la Gerencia asigna un responsable de seguimiento y verificacion.
- Se define un plazo para medir la eficacia.
- El responsable verifica si la accion realmente evito la recurrencia o si fue efectiva.
- Debe registrar resultado, observaciones y evidencia.

7. Cierre del hallazgo
- Si la verificacion es eficaz, el hallazgo se cierra.
- Si no es eficaz, se deben definir nuevas acciones o seguimiento adicional.
- El sistema mantiene trazabilidad completa: estado, responsables, fechas, evidencia y comentarios.

8. Consulta y seguimiento
- Mostrar la bandeja de hallazgos abiertos, cerrados, vencidos o por vencer.
- Explicar que las tarjetas del Inicio SGC permiten acceder rapidamente a documentos, hallazgos abiertos, plazos y registros cerrados.

Indicaciones visuales para NotebookLM:
- Usar las capturas incluidas en este documento como referencia visual.
- Mostrar primero la portada y el login.
- Luego mostrar Inicio SGC, destacando las tarjetas y el acceso a hallazgos.
- Usar la pantalla Nuevo Hallazgo para explicar como reporta un colaborador.
- Usar la bandeja y el detalle del hallazgo para explicar estados, responsables y seguimiento.
- Usar la pantalla de evidencia para reforzar que cada etapa debe quedar respaldada.

Frase de cierre sugerida:
El tratamiento de hallazgos fortalece el Sistema de Gestion de Calidad porque convierte cada situacion detectada en una oportunidad controlada de correccion, aprendizaje, mejora y prevencion.
"""


def create_markdown():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text(guide_text(), encoding="utf-8")


def create_docx(captures):
    media_names = []
    rels = []
    body = []
    body.append(p("Guia para video NotebookLM", "Title"))
    body.append(p("Tratamiento de hallazgos en el Sistema de Gestion de Calidad", "Subtitle"))
    body.append(p("Este documento contiene instrucciones para solicitar a NotebookLM un video explicativo y capturas del sitio como apoyo visual."))
    body.append(p("Objetivo del video", "Heading1"))
    body.append(p("Capacitar a los usuarios en el registro, validacion, tratamiento, accion correctiva, verificacion de eficacia y cierre de hallazgos."))
    body.append(p("Indicaciones principales para NotebookLM", "Heading1"))
    body.append(bullets([
        "Duracion sugerida: 6 a 8 minutos.",
        "Tono: profesional, claro y cercano.",
        "Publico objetivo: colaboradores, Representante de la Gerencia y responsables asignados.",
        "Usar las capturas como referencia visual del sistema.",
        "Explicar responsabilidades, plazos, evidencias y cierre del flujo.",
    ]))
    body.append(p("Guion sugerido", "Heading1"))
    sections = [
        ("1. Bienvenida e introduccion", "Presentar el Portal SGC como plataforma central para documentos, hallazgos y trazabilidad ISO."),
        ("2. Registro del hallazgo", "Un colaborador describe el hallazgo, informa fecha, proceso, fuente y evidencia objetiva. El sistema asigna codigo H001, H002, etc."),
        ("3. Validacion del Representante de la Gerencia", "El Representante valida si aplica. Si no aplica, cierra con respuesta. Si aplica, clasifica como NC u OM y asigna responsables y plazos."),
        ("4. Correccion", "El responsable de correccion ejecuta la accion inmediata, registra lo realizado y carga evidencia."),
        ("5. Accion correctiva", "El responsable analiza causa raiz con 5 Por Que o metodo libre, carga evidencia y define la accion para evitar recurrencia."),
        ("6. Verificacion de eficacia", "El responsable asignado verifica si la accion fue efectiva dentro del plazo definido y registra resultado con evidencia."),
        ("7. Cierre y consulta", "Si la verificacion es eficaz, el hallazgo se cierra. Luego puede consultarse en la bandeja e historial."),
    ]
    for title, text in sections:
        body.append(p(title, "Heading2"))
        body.append(p(text))

    body.append(p("Roles que debe explicar el video", "Heading1"))
    body.append(bullets([
        "Colaborador: registra el hallazgo con datos claros y evidencia disponible.",
        "Representante de la Gerencia: valida, clasifica, asigna responsables, revisa etapas y cierra.",
        "Responsable de correccion: ejecuta la correccion inmediata y sube evidencia.",
        "Responsable de accion correctiva: analiza causa raiz y define acciones para evitar recurrencia.",
        "Responsable de verificacion: mide la eficacia y documenta el resultado.",
    ]))
    body.append(p("Capturas de referencia", "Heading1"))
    for index, (caption, path) in enumerate(captures, start=1):
        rel_id = f"rId{index}"
        media_name = f"image{index}.png"
        media_names.append((media_name, path))
        rels.append((rel_id, media_name))
        body.append(p(caption, "Heading2"))
        body.append(image_xml(rel_id, path))

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {''.join(body)}
    <w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720"/></w:sectPr>
  </w:body>
</w:document>
"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId0" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
""" + "".join(
        f'  <Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{media_name}"/>\n'
        for rel_id, media_name in rels
    ) + "</Relationships>"
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="40"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:rPr><w:color w:val="5B6F9D"/><w:sz w:val="24"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="Heading 1"/><w:pPr><w:spacing w:before="280" w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="Heading 2"/><w:pPr><w:spacing w:before="220" w:after="100"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
</w:styles>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    with zipfile.ZipFile(DOCX_PATH, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", root_rels)
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/styles.xml", styles_xml)
        docx.writestr("word/_rels/document.xml.rels", rels_xml)
        for media_name, path in media_names:
            docx.write(path, f"word/media/{media_name}")


def main():
    setup_django()
    create_markdown()
    snapshots = save_snapshots()
    captures = capture_with_edge(snapshots)
    create_docx(captures)
    print(f"Markdown: {MD_PATH}")
    print(f"Word: {DOCX_PATH}")
    print(f"Capturas: {len(captures)}")


if __name__ == "__main__":
    main()
