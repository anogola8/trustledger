"""PDF helpers built on ReportLab (free, open source)."""
import io

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor('#1F3A5F')


def qr_png_bytes(url, box_size=8):
    img = qrcode.make(url, box_size=box_size, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _styles():
    ss = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('t', parent=ss['Title'], textColor=NAVY, fontSize=20, alignment=0),
        'h2': ParagraphStyle('h2', parent=ss['Heading2'], textColor=NAVY, fontSize=13, spaceBefore=10),
        'body': ParagraphStyle('b', parent=ss['BodyText'], fontSize=10, leading=14),
        'small': ParagraphStyle('s', parent=ss['BodyText'], fontSize=8, textColor=colors.grey),
    }


def build_pdf(story_builder):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    st = _styles()
    story = story_builder(st)
    doc.build(story)
    return buf.getvalue()


def table(rows, widths=None, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [('GRID', (0, 0), (-1, -1), 0.4, colors.lightgrey), ('FONTSIZE', (0, 0), (-1, -1), 9),
             ('VALIGN', (0, 0), (-1, -1), 'TOP')]
    if header:
        style += [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DDE6F0')), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]
    t.setStyle(TableStyle(style))
    return t


def qr_flowable(url, size=32 * mm):
    return Image(io.BytesIO(qr_png_bytes(url)), width=size, height=size)


__all__ = ['build_pdf', 'table', 'qr_flowable', 'qr_png_bytes', 'Paragraph', 'Spacer', 'ImageReader']
