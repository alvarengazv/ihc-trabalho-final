"""Separa o PDF compilado do E4 em artigo (E4) e apêndice (E1).

O arquivo UXAgent_P3_Artigo_E4.tex compila o artigo seguido do Apêndice E1,
que usa a mesma lista de referências. Este script grava:
  deliverables/P3_E4_com_Apendice_E1.pdf  (documento completo)
  deliverables/UXAgent_P3_Artigo_E4.pdf   (páginas do artigo)
  deliverables/UXAgent_P3_Anexo_E1.pdf    (páginas do apêndice)
Requer: python -m pip install pypdf
"""
import shutil
from pathlib import Path

from pypdf import PdfReader, PdfWriter

D = Path(__file__).resolve().parent.parent / "deliverables"
src = D / "UXAgent_P3_Artigo_E4.pdf"
full = D / "P3_E4_com_Apendice_E1.pdf"
shutil.copyfile(src, full)
reader = PdfReader(str(full))
start = next(i for i, p in enumerate(reader.pages) if "Apêndice E1" in (p.extract_text() or "")[:200])
for name, pages in (("UXAgent_P3_Artigo_E4.pdf", range(start)), ("UXAgent_P3_Anexo_E1.pdf", range(start, len(reader.pages)))):
    w = PdfWriter()
    for i in pages:
        w.add_page(reader.pages[i])
    with open(D / name, "wb") as f:
        w.write(f)
print(f"E4: {start} páginas; E1: {len(reader.pages) - start} páginas")
