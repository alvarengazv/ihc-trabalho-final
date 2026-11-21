"""Regenerate the vector design plates from the analyst's specifications."""
import json
from pathlib import Path
from textwrap import wrap
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)
for normal, bold in [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]:
    if Path(normal).exists():
        pdfmetrics.registerFont(TTFont("Body", normal))
        pdfmetrics.registerFont(TTFont("Bold", bold))
        break

DARK, MID, LIGHT = "#173830", "#476655", "#e9f2ed"
W = 278

def canvas(name, height):
    paper = Canvas(str(OUT / (name + ".pdf")), pagesize=(W, height), invariant=1)
    paper.setTitle(name.replace("-", " "))
    paper.setStrokeColor(HexColor(MID))
    return paper

def box(paper, x, y, width, height, fill):
    paper.setFillColor(HexColor(fill))
    paper.roundRect(x, y, width, height, 3, fill=1, stroke=0)

def label(paper, x, y, value, size=8.2, bold=False, color=DARK):
    paper.setFillColor(HexColor(color))
    paper.setFont("Bold" if bold else "Body", size)
    paper.drawString(x, y, value)

def lines(value, width, size=8.2, font="Body"):
    row = ""
    output = []
    for word in value.split():
        combined = (row + " " + word).strip()
        if pdfmetrics.stringWidth(combined, font, size) > width and row:
            output.append(row)
            row = word
        else:
            row = combined
    return output + [row]

def draw_tree(key, model):
    layout = []
    for title, temporal, children in model["groups"]:
        layout.append(("group", title))
        layout.append(("plan", temporal))
        for kind, op, value in children:
            layout.append(("leaf", (kind, op, value)))
    header = lines(model["goal"], W-18, 10, "Bold")
    top_plan = lines(model["plan"], W-18)
    lengths = []
    for role, data in layout:
        if role == "group": lengths.append(20)
        elif role == "plan": lengths.append(5 + 9*len(lines(data, W-25, 7.7)))
        else: lengths.append(4 + 10*len(lines(data[2], W-62)))
    height = 18+13*len(header)+10*len(top_plan)+sum(lengths)+6
    p = canvas("CTT-"+key, height)
    top = height-6
    box(p, 1, top-9-13*len(header), W-2, 13*len(header)+10, DARK)
    for i, value in enumerate(header): label(p,7,top-12-13*i,value,10,True,"#ffffff")
    top -= 16+13*len(header)
    for value in top_plan:
        label(p, 6, top, value, 8.2)
        top -= 10
    for (role, data), amount in zip(layout,lengths):
        if role == "group":
            box(p,3,top-16,W-6,15,LIGHT)
            label(p,8,top-12,"A  "+data,8.6,True)
        elif role == "plan":
            for j,v in enumerate(lines(data,W-25,7.7)): label(p,14,top-6-9*j,v,7.7)
        else:
            kind,op,value = data
            p.setLineWidth(.5)
            p.line(10,top+2,10,top-amount+2)
            p.line(10,top-5,14,top-5)
            label(p,16,top-8,kind,8.2,True)
            label(p,29,top-8,op,7.6)
            for j,v in enumerate(lines(value,W-62)): label(p,58,top-8-10*j,v)
        top -= amount
    p.save()

def draw_dialogue():
    nodes = [
        ("S0 • Início", "u: consultar cardápio → S1; consultar pedido → S3. Com histórico, u: repetir pedido → somar as linhas → S3."),
        ("S1 • Escolher refeição", "u: explorar categoria (B) → S1; abrir item → S2; consultar pedido → S3; consultar início → S0. d: apresentar alimentos e preços."),
        ("S2 • Compor item", "u: escolher opção, ajustar quantidade → S2. d: apresentar opção e preço. Se faltar opção: d: solicitar escolha (alerta); u: escolher opção (recuperação)."),
        ("P • Atualizar comanda", "u: adicionar item → P → S1; salvar alteração → P → S3. d: apresentar composição atualizada. u: voltar → origem de inclusão ou edição."),
        ("S3 • Conferir pedido", "u: ajustar quantidade, remover linha, desfazer remoção → S3; alterar item → S2; retomar cardápio → S1; consultar início → S0. d: apresentar linhas e total."),
        ("P • Registrar pedido", "u: confirmar pedido [há linha] → P → S4. d: apresentar registro. Tentativa sem guarda → captura de erro; conservar a cena e oferecer operações válidas."),
        ("S4 • Consultar confirmação", "d: apresentar pedido registrado. O resultado da tarefa é apurado externamente. A leitura humana pode consultar a ajuda da confirmação."),
        ("S5 • Consultar ajuda", "Qualquer origem S0–S4: u: abrir ajuda → S5. u: escolher camada → S5; fechar ajuda → origem. d: apresentar explicação ou retomar diálogo."),
    ]
    height = 8+sum(22+11*len(lines(body,W-22)) for _,body in nodes)
    p = canvas("MoLIC",height)
    top = height-3
    for title,body in nodes:
        rows=lines(body,W-22)
        h = 19+11*len(rows)
        box(p,2,top-h,W-4,h,LIGHT if not title.startswith("P •") else "#e8eaf0")
        label(p,9,top-11,title,8.7,True)
        for i,line in enumerate(rows): label(p,10,top-23-11*i,line)
        top -= h+3
    p.save()

def draw_wireframes():
    screens = [
        ("S0 • Início", ["Mesa de Minas   |   Ajuda","Ver cardápio", "Ver pedido","Último pedido¹","Repetir pedido¹"]),
        ("S1 A • Cardápio",["Cardápio   |   Ajuda","Início   •   Ver pedido","Entradas","Salada verde (V, SL)","Nome, detalhes e preço","Lista contínua ↓"]),
        ("S1 B • Cardápio",["Cardápio   |   Ajuda","Categorias","Entradas   •   Massas","Nome, detalhes e preço","Resumo no rodapé","Total   •   Ver pedido"]),
        ("S2 • Item",["Detalhes   |   Ajuda","Voltar","Nome e preço","Opção, se exigida","Quantidade   −   +","Adicionar / Salvar"]),
        ("S3 • Revisão",["Revisão   |   Ajuda","Cardápio   •   Início","Item, opção e unidades","−   +   Alterar   Remover","Total","Confirmar pedido"]),
        ("S4 • Confirmação",["Pedido confirmado","Ajuda","Composição registrada","Total"]),
        ("S5 • Ajuda",["Ajuda   |   Fechar ajuda","Assunto da origem","Dica local","Sobre esta tela","Guia de uso","Texto da camada"]),
    ]
    p=canvas("Wireframes",406)
    for i,(name,items) in enumerate(screens):
        x=(i%2)*139+2
        y=406-((i//2)+1)*99
        box(p,x,y,135,94,LIGHT)
        box(p,x+3,y+73,129,18,DARK)
        label(p,x+8,y+79,name,8.4,True,"#ffffff")
        for j,row in enumerate(items): label(p,x+7,y+62-10*j,row,7.7)
    label(p,144,62,"¹ Apenas com histórico",8)
    label(p,144,50,"previsto no protocolo.",8)
    p.save()

if __name__ == "__main__":
    for key, model in json.loads((HERE/"ctt.json").read_text(encoding="utf8")).items():
        draw_tree(key,model)
    draw_dialogue()
    draw_wireframes()
