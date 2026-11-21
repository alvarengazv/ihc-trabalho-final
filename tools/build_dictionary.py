"""Render the pilot dictionary from its maintained Markdown tables (ReportLab)."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

folder = Path(__file__).resolve().parents[1] / "deliverables" / "E3_Pacote_Piloto"
styles = getSampleStyleSheet()
styles.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=9, leading=12,
                          alignment=TA_LEFT, textColor=colors.HexColor("#182e30")))
elements = []
table = []


def finish_table():
    if not table:
        return
    widths = [38, 25, 109] if len(table[0]) == 3 else [40, 132]
    view = LongTable(table[:], colWidths=[w * mm for w in widths], repeatRows=1)
    view.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#cde6df")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f7f6")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.extend([view, Spacer(1, 8)])
    table.clear()


for line in (folder / "dicionario_eventos.md").read_text(encoding="utf8").splitlines():
    line = line.replace(chr(96), "")
    if line.startswith("|"):
        if line.startswith("|---"):
            continue
        table.append([Paragraph(escape(cell.strip()), styles["Cell"])
                      for cell in line.strip("|").split("|")])
        continue
    finish_table()
    if line.startswith("## "):
        elements.append(Paragraph(line[3:], styles["Heading2"]))
    elif line.startswith("# "):
        elements.append(Paragraph(line[2:], styles["Title"]))
    elif line:
        elements.extend([Paragraph(escape(line), styles["BodyText"]), Spacer(1, 7)])
finish_table()


def footer(canvas, doc):
    canvas.setFont("Helvetica", 8)
    canvas.drawString(19 * mm, 12 * mm, "UX-Agent   /   Instrumentação do cardápio")
    canvas.drawRightString(191 * mm, 12 * mm, f"{doc.page}")


SimpleDocTemplate(str(folder / "dicionario_eventos.pdf"), pagesize=A4,
                  title="Dicionário de eventos do cardápio", leftMargin=19*mm,
                  rightMargin=19*mm, topMargin=16*mm, bottomMargin=19*mm).build(
                      elements, onFirstPage=footer, onLaterPages=footer)
