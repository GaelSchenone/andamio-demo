"""Genera el PDF de un presupuesto, con el mismo espíritu que la plantilla original."""

import importlib.resources
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from presupuestos_backend.formato import fecha_larga, moneda
from presupuestos_backend.models import Presupuesto
from presupuestos_backend.negocio import cargar_negocio

INK = colors.HexColor("#000000")
INK_SOFT = colors.HexColor("#5C5C5C")
LINE = colors.HexColor("#D8D8D8")
ACCENT = colors.HexColor("#000000")
ACCENT_SOFT = colors.HexColor("#F2F2F2")

ANCHO_UTIL = A4[0] - 4 * cm

label_style = ParagraphStyle(
    "label",
    fontName="Helvetica-Bold",
    fontSize=7.5,
    textColor=INK_SOFT,
    leading=10,
)
valor_style = ParagraphStyle(
    "valor",
    fontName="Helvetica",
    fontSize=10.5,
    textColor=INK,
    leading=14,
)
titulo_style = ParagraphStyle(
    "titulo",
    fontName="Helvetica-Bold",
    fontSize=22,
    textColor=INK,
    leading=26,
)
negocio_nombre_style = ParagraphStyle(
    "negocio_nombre",
    fontName="Helvetica-Bold",
    fontSize=13,
    textColor=INK,
    leading=16,
)
negocio_info_style = ParagraphStyle(
    "negocio_info",
    fontName="Helvetica",
    fontSize=9,
    textColor=INK_SOFT,
    leading=13,
    alignment=TA_RIGHT,
)
tabla_header_style = ParagraphStyle(
    "tabla_header",
    fontName="Helvetica-Bold",
    fontSize=8.5,
    textColor=colors.white,
)
tabla_celda_style = ParagraphStyle(
    "tabla_celda",
    fontName="Helvetica",
    fontSize=9.5,
    textColor=INK,
    leading=13,
)
tabla_num_style = ParagraphStyle(
    "tabla_num",
    fontName="Helvetica",
    fontSize=9.5,
    textColor=INK,
    alignment=TA_RIGHT,
)
total_label_style = ParagraphStyle(
    "total_label",
    fontName="Helvetica-Bold",
    fontSize=13,
    textColor=INK,
    alignment=TA_RIGHT,
)
total_valor_style = ParagraphStyle(
    "total_valor",
    fontName="Helvetica-Bold",
    fontSize=15,
    textColor=ACCENT,
    alignment=TA_RIGHT,
)
observaciones_style = ParagraphStyle(
    "observaciones",
    fontName="Helvetica",
    fontSize=9,
    textColor=INK,
    leading=13,
)
firma_label_style = ParagraphStyle(
    "firma_label",
    fontName="Helvetica-Bold",
    fontSize=8,
    textColor=INK_SOFT,
    alignment=TA_CENTER,
)
footer_style = ParagraphStyle(
    "footer",
    fontName="Helvetica",
    fontSize=7.5,
    textColor=INK_SOFT,
)
footer_right_style = ParagraphStyle(
    "footer_right",
    fontName="Helvetica",
    fontSize=7.5,
    textColor=INK_SOFT,
    alignment=TA_RIGHT,
)


def _campo(label: str, valor: str, ancho: float) -> Table:
    t = Table(
        [[Paragraph(label.upper(), label_style)], [Paragraph(valor or "-", valor_style)]],
        colWidths=[ancho],
    )
    t.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
                ("TOPPADDING", (0, 1), (-1, 1), 2),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                ("LINEBELOW", (0, 1), (-1, 1), 0.6, LINE),
            ]
        )
    )
    return t


def _fila_campos(campos: list[tuple[str, str]]) -> Table:
    ancho = ANCHO_UTIL / len(campos)
    celdas = [_campo(label, valor, ancho - 0.3 * cm) for label, valor in campos]
    t = Table([celdas], colWidths=[ancho] * len(campos))
    t.setStyle(
        TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")])
    )
    return t


def _logo_path() -> str:
    ref = importlib.resources.files("presupuestos_backend") / "static" / "logo.png"
    return str(ref)


def generar_pdf(presupuesto: Presupuesto) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.6 * cm,
        bottomMargin=1.4 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=f"Presupuesto {presupuesto.numero} - {presupuesto.cliente_obra}",
    )
    story = []

    negocio = cargar_negocio()
    logo = Image(_logo_path(), width=1.5 * cm, height=1.615 * cm)
    negocio_texto = Paragraph(
        f"{escape(negocio.nombre)}<br/>"
        f"<font size=8.5 color='#5C5C5C'>{escape(negocio.rubro)}</font>",
        negocio_nombre_style,
    )
    contacto_texto = Paragraph(
        "<br/>".join(escape(linea) for linea in negocio.lineas_encabezado()),
        negocio_info_style,
    )
    header = Table(
        [[logo, negocio_texto, contacto_texto]],
        colWidths=[2.2 * cm, ANCHO_UTIL / 2, ANCHO_UTIL / 2 - 2.2 * cm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 8),
            ]
        )
    )
    story.append(header)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.8, color=INK))
    story.append(Spacer(1, 14))

    story.append(Paragraph(" ".join("PRESUPUESTO"), titulo_style))
    story.append(Spacer(1, 14))

    story.append(
        _fila_campos(
            [
                ("Cliente / Obra", presupuesto.cliente_obra),
                ("N° de presupuesto", presupuesto.numero),
                ("Fecha de emisión", fecha_larga(presupuesto.fecha_emision)),
            ]
        )
    )
    story.append(
        _fila_campos(
            [
                ("Dirección", presupuesto.direccion),
                ("Vigencia (días)", f"{presupuesto.vigencia_dias} días"),
                ("Plazo de obra", presupuesto.plazo_obra),
            ]
        )
    )
    story.append(Spacer(1, 16))

    story.append(Paragraph("DETALLE DE LOS TRABAJOS", label_style))
    story.append(Spacer(1, 6))

    encabezado = [
        Paragraph("DESCRIPCIÓN DEL TRABAJO", tabla_header_style),
        Paragraph("UNIDAD", tabla_header_style),
        Paragraph("CANT.", tabla_header_style),
        Paragraph("IMPORTE", tabla_header_style),
    ]
    filas = [encabezado]
    for item in presupuesto.items:
        filas.append(
            [
                Paragraph(item.descripcion, tabla_celda_style),
                Paragraph(item.unidad or "-", tabla_celda_style),
                Paragraph(f"{item.cantidad:g}", tabla_num_style),
                Paragraph(f"$ {moneda(item.importe)}", tabla_num_style),
            ]
        )
    anchos = [ANCHO_UTIL * p for p in (0.48, 0.16, 0.14, 0.22)]
    tabla_items = Table(filas, colWidths=anchos, repeatRows=1)
    tabla_items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(tabla_items)

    total_tabla = Table(
        [
            [
                Paragraph("TOTAL", total_label_style),
                Paragraph(f"$ {moneda(presupuesto.total)}", total_valor_style),
            ]
        ],
        colWidths=[ANCHO_UTIL - 4.5 * cm, 4.5 * cm],
    )
    total_tabla.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (1, 0), (1, 0), ACCENT_SOFT),
                ("BOX", (1, 0), (1, 0), 0.6, ACCENT),
                ("RIGHTPADDING", (1, 0), (1, 0), 10),
                ("LEFTPADDING", (1, 0), (1, 0), 10),
                ("TOPPADDING", (1, 0), (1, 0), 6),
                ("BOTTOMPADDING", (1, 0), (1, 0), 6),
            ]
        )
    )
    story.append(total_tabla)
    story.append(Spacer(1, 18))

    story.append(
        _fila_campos(
            [
                ("Forma de pago", presupuesto.forma_pago),
                ("Materiales a cargo de", presupuesto.materiales_a_cargo),
            ]
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("OBSERVACIONES", label_style))
    story.append(Spacer(1, 4))
    obs_html = (presupuesto.observaciones or "").replace("\n", "<br/>")
    obs_tabla = Table([[Paragraph(obs_html, observaciones_style)]], colWidths=[ANCHO_UTIL])
    obs_tabla.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("BACKGROUND", (0, 0), (-1, -1), ACCENT_SOFT),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(obs_tabla)
    story.append(Spacer(1, 34))

    firmas = Table(
        [
            [
                HRFlowable(width="90%", thickness=0.6, color=INK_SOFT),
                HRFlowable(width="90%", thickness=0.6, color=INK_SOFT),
            ],
            [
                Paragraph(f"FIRMA {escape(negocio.nombre.upper())}", firma_label_style),
                Paragraph("FIRMA CONFORMIDAD CLIENTE", firma_label_style),
            ],
        ],
        colWidths=[ANCHO_UTIL / 2, ANCHO_UTIL / 2],
    )
    firmas.setStyle(TableStyle([("TOPPADDING", (0, 1), (-1, 1), 6)]))
    story.append(firmas)
    story.append(Spacer(1, 20))

    pie = Table(
        [
            [
                Paragraph(escape(negocio.linea_pie()), footer_style),
                Paragraph("Presupuesto sujeto a la vigencia indicada", footer_right_style),
            ]
        ],
        colWidths=[ANCHO_UTIL / 2, ANCHO_UTIL / 2],
    )
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE))
    story.append(Spacer(1, 6))
    story.append(pie)

    doc.build(story)
    buffer.seek(0)
    return buffer
