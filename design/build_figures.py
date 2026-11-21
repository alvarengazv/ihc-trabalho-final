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
        label(p, 6, top, value.replace("≫", ">>"), 8.2)
        top -= 10
    for (role, data), amount in zip(layout,lengths):
        if role == "group":
            box(p,3,top-16,W-6,15,LIGHT)
            label(p,8,top-12,"A  "+data,8.6,True)
        elif role == "plan":
            for j,v in enumerate(lines(data,W-25,7.7)): label(p,14,top-6-9*j,v.replace("≫", ">>"),7.7)
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
    # An edge-labelled MoLIC graph: repeated scene symbols refer to the same
    # vertex; each directed arc carries the user's utterance and deputy's reply.
    arcs = [
        ("S0", "S1", "u: consultar cardápio", "d: apresentar categorias e alimentos"),
        ("S0/S1", "S3", "u: consultar pedido", "d: apresentar linhas e total; guardar origem"),
        ("S0", "S3", "u: repetir pedido [há histórico]", "P: somar linhas à comanda; d: apresentar revisão"),
        ("S1/S3", "S0", "u: consultar início", "d: apresentar início e histórico, se disponível"),
        ("S1", "S1", "u: escolher categoria [versão B]", "d: apresentar alimentos da categoria solicitada"),
        ("S1", "S1", "u: paginar resumo [B, >4 linhas e página disponível]", "d: apresentar até quatro linhas e posição da página"),
        ("S1", "S2", "u: abrir item", "d: apresentar composição, quantidade e preço"),
        ("S2", "S2", "u: ajustar quantidade ou escolher opção", "d: apresentar valor da escolha"),
        ("S2", "S1", "u: adicionar item [composição válida]", "P: somar linha; d: apresentar comanda atualizada"),
        ("S2", "S3", "u: salvar alteração [editando e composição válida]", "P: atualizar linha; d: apresentar revisão atualizada"),
        ("S2", "S1/S3", "u: voltar dos detalhes", "d: retomar catálogo (inclusão) ou revisão (edição)"),
        ("S3", "S2", "u: alterar item", "d: apresentar composição atual da linha escolhida"),
        ("S3", "S3", "u: ajustar unidades, remover ou desfazer remoção", "P: atualizar linhas; d: apresentar quantidade e total"),
        ("S3", "S0/S1", "u: voltar da revisão", "d: restaurar origem de abertura; após repetir, S0"),
        ("S3", "S4", "u: confirmar pedido [há ao menos uma linha]", "P: registrar pedido; d: apresentar composição confirmada"),
        ("S0–S4", "S5", "u: consultar ajuda [ubíqua]", "d: apresentar dica da origem; suspender cena"),
        ("S5", "S5", "u: escolher camada", "d: apresentar explicação solicitada"),
        ("S5", "origem", "u: fechar ajuda", "d: restaurar cena suspensa e conservar comanda"),
        ("S2", "AL/S2", "d: solicitar opção [obrigatória e ausente]", "u: escolher opção; d: habilitar inclusão ou alteração"),
        ("cena", "CE/cena", "u: propor ação fora da guarda", "P: rejeitar proposta; d: manter signos e ações válidas"),
    ]
    groups = {0:"Origem e exploração", 6:"Escolha e composição", 11:"Revisão e confirmação",
              16:"Subdiálogo de ajuda", 19:"Prevenção e recuperação"}
    widths = [lines(a[2], W-55, 7.5) + lines(a[3], W-55, 7.5) for a in arcs]
    height = 17 + 14*len(groups) + sum(5 + 9*len(row) for row in widths)
    p = canvas("MoLIC", height)
    label(p, 3, height-10, "Papel: pessoa que prepara a comanda", 9.5, True)
    top = height-15
    for i, ((origin, target, request, response), row) in enumerate(zip(arcs, widths)):
        if i in groups:
            box(p, 2, top-13, W-4, 13, DARK)
            label(p, 7, top-9, groups[i], 8, True, "#ffffff")
            top -= 14
        h = 5 + 9*len(row)
        box(p, 2, top-h+1, 45, h-2, LIGHT)
        label(p, 5, top-8, origin, 7, True)
        p.setLineWidth(.6)
        p.line(7, top-10, 7, top-h+6)
        p.line(7, top-h+6, 11, top-h+6)
        p.line(9, top-h+8, 11, top-h+6)
        p.line(9, top-h+4, 11, top-h+6)
        label(p, 14, top-h+8, target, 7, True)
        for j, line in enumerate(row):
            label(p, 52, top-8-9*j, line, 7.5)
        top -= h
    p.save()

def draw_wireframes():
    screens = [
        ("S0 • Início", ["Mesa de Minas   |   Ajuda","Ver cardápio", "Ver pedido","Último pedido¹","Repetir pedido¹"]),
        ("S1 A • Cardápio",["Cardápio   |   Ajuda","Início   •   Ver pedido","Entradas","Salada verde (V, SL)","Nome, detalhes e preço","Lista contínua ↓"]),
        ("S1 B • Cardápio",["Cardápio   |   Ajuda","Categorias","Entradas   •   Massas","Nome, detalhes e preço","Resumo • até 4 linhas por página","Total   •   Ver pedido"]),
        ("S2 • Item",["Detalhes   |   Ajuda","Voltar","Nome e preço","Opção, se exigida","Quantidade   −   +","Adicionar / Salvar"]),
        ("S3 • Revisão",["Revisão   |   Ajuda","Voltar   •   Início","Item, opção e unidades","−   +   Alterar   Remover","Total","Confirmar pedido"]),
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
