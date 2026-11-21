"""MoLIC-derived interaction machine. Browser and proxy consume the same layout."""
import json
from copy import deepcopy
from pathlib import Path
from .catalog import CATEGORIES, LAST_ORDER, MENU, SISTER_ORDER, TASKS, TRAINING, money

HELP_PATH = Path(__file__).resolve().parents[1] / "design" / "help.json"
LAYERS = {"dica": "Dica local", "contexto": "Sobre esta tela", "guia": "Guia de uso"}
SCENES = {"S0": "Início", "S1": "Cardápio", "S2": "Detalhes do item",
          "S3": "Revisão do pedido", "S4": "Pedido confirmado", "S5": "Ajuda"}


class MenuApp:
    def __init__(self, task="C1", version="A"):
        task = "Treino" if task.lower() == "treino" else task
        if task not in TASKS or version not in ("A", "B"):
            raise ValueError("Tarefa ou versão desconhecida.")
        self.task, self.version = task, version
        self.menu = TRAINING if task == "Treino" else MENU
        self.scene = "S0" if task in ("V1", "V2") else "S1"
        self.category = 0
        self.footer_page = 0
        self.review_origin = "S1"
        self.item = None
        self.option = None
        self.quantity = 1
        self.edit = None
        self.confirmed = False
        self.help_origin = None
        self.layer = "dica"
        self.removed = None
        self.order = []
        initial = SISTER_ORDER if task == "C2" else ((26, None, 1),) if task == "V2" else ()
        for item, option, count in initial:
            self.order.append(self._row(item, option, count))

    def _row(self, item, option, count):
        dish = self.menu[item]
        return {"item_id": item, "nome": dish.name, "opcao": option,
                "quantidade": count, "preco_centavos": dish.price(option)}

    def state(self):
        return {"tela": self.scene, "pedido": deepcopy(self.order),
                "confirmado": self.confirmed, "categoria": self.category,
                "item_ativo": self.item, "opcao": self.option, "quantidade": self.quantity,
                "total_centavos": sum(r["preco_centavos"] * r["quantidade"] for r in self.order),
                "origem_ajuda": self.help_origin, "camada": self.layer}

    def _store(self, row):
        """Coalesce two genuinely equivalent choices without combining different sizes."""
        for i, existing in enumerate(self.order):
            if (existing["item_id"], existing["opcao"]) == (row["item_id"], row["opcao"]):
                existing["quantidade"] += row["quantidade"]
                return i
        self.order.append(row)
        return len(self.order) - 1

    def apply(self, action):
        allowed = {e.get("action") for e in self.elements() if e.get("action")}
        if action not in allowed:
            return [{"tipo": "acao_rejeitada", "motivo": "inexistente"}]
        old = self.scene
        events = []

        def emit(kind, **fields):
            events.append(dict(tipo=kind, **deepcopy(fields)))

        def order_event(kind, idx, previous=None):
            row = previous if kind == "item_removido" else self.order[idx]
            emit(kind, linha=idx, item=row["item_id"], opcao=row["opcao"],
                 quantidade=row["quantidade"], anterior=previous, novo=None if kind == "item_removido" else row,
                 pedido=self.order, estado_posterior=self.order)

        verb, _, arg = action.partition(":")
        if verb in ("add", "save", "inc", "dec", "repeat"):
            self.removed = None
        if verb == "help":
            self.help_origin, self.scene, self.layer = old, "S5", "dica"
            emit("ajuda_aberta", tela_origem=old, camada="dica", topico=SCENES[old])
        elif verb == "layer":
            if self.layer != arg:
                self.layer = arg
                emit("ajuda_aberta", tela_origem=self.help_origin, camada=arg, topico=SCENES[self.help_origin])
        elif verb == "back":
            if old == "S5":
                self.scene = self.help_origin
                emit("ajuda_fechada", tela_origem=self.scene, retorno=self.scene, camada=self.layer, topico=SCENES[self.scene])
                self.help_origin = None
            elif old == "S3":
                self.scene = self.review_origin
            else:
                self.scene = "S3" if old == "S2" and self.edit is not None else "S1"
        elif verb in ("home", "menu", "review"):
            if verb == "review":
                self.review_origin = old
            self.scene = {"home": "S0", "menu": "S1", "review": "S3"}[verb]
        elif verb == "category":
            if self.category != int(arg):
                self.category = int(arg)
                emit("tela_alterada", anterior=old, nova=old, categoria=CATEGORIES[self.category])
        elif verb == "footer":
            self.footer_page += 1 if arg == "next" else -1
        elif verb == "repeat":
            self.review_origin = "S0"
            for item, option, count in LAST_ORDER:
                idx = self._store(self._row(item, option, count))
                order_event("item_adicionado", idx)
            self.scene = "S3"
        elif verb in ("open", "edit"):
            if verb == "open":
                self.item, self.option, self.quantity, self.edit = int(arg), None, 1, None
            else:
                self.edit = int(arg)
                row = self.order[self.edit]
                self.item, self.option, self.quantity = row["item_id"], row["opcao"], row["quantidade"]
            self.scene = "S2"
        elif verb == "option":
            self.option = arg
            emit("opcao_selecionada", item=self.item, opcao=arg)
        elif verb in ("more", "less"):
            self.quantity += 1 if verb == "more" else -1
        elif verb in ("add", "save"):
            row = self._row(self.item, self.option, self.quantity)
            if verb == "save":
                idx = self.edit
                previous = self.order[idx]
                self.order[idx] = row
                order_event("item_alterado", idx, previous)
                self.scene = "S3"
            else:
                idx = self._store(row)
                order_event("item_adicionado", idx)
                self.scene = "S1"
        elif verb in ("inc", "dec"):
            idx = int(arg)
            previous = self.order[idx].copy()
            self.order[idx]["quantidade"] += 1 if verb == "inc" else -1
            order_event("item_alterado", idx, previous)
        elif verb == "remove":
            idx = int(arg)
            self.removed = (idx, self.order.pop(idx))
            order_event("item_removido", idx, self.removed[1])
        elif verb == "undo":
            idx, row = self.removed
            self.order.insert(idx, row)
            self.removed = None
            order_event("item_adicionado", idx)
        elif verb == "confirm":
            self.scene, self.confirmed, self.removed = "S4", True, None
            emit("pedido_confirmado", pedido=self.order, estado_final=self.order)
        if old != self.scene:
            emit("tela_alterada", anterior=old, nova=self.scene)
        return events

    def elements(self, scroll_y=0):
        """Visual signs only. Rectangle coordinates are CSS pixels on a 360-wide page.

        Fixed elements use the document scroll offset, distinct from magnifier panning.
        Analyst metadata (id, part, item_id, action) never forms a policy label.
        """
        elements = []

        def add(key, text, role, x, y, w, h, action=None, style=None, **meta):
            e = dict(id=key, text=text, role=role, box=[x, y, w, h], style=style or role, **meta)
            if action:
                e["action"] = action
            elements.append(e)

        def button(action, label, y, x=16, w=328, style="button", **meta):
            add(action, ("✓ " if meta.get("selected") else "") + label, "button", x, y, w, 44, action, style, **meta)

        def title(text, y):
            add("heading", text, "heading", 16, y, 328, 44)

        def review_button(y, fixed=False):
            count = sum(r["quantidade"] for r in self.order)
            button("review", f"Ver pedido ({count})", y, 208, 136, "primary", fixed=fixed)

        add("brand", "Mesa de Minas" if self.task != "Treino" else "Lanchonete", "label",
            16, 12, 224, 44, style="brand")
        if self.scene != "S5":
            button("help", "Ajuda", 12, 256, 88, "quiet")

        if self.scene == "S0":
            title("Início", 76)
            button("menu", "Ver cardápio", 140, style="primary")
            button("review", "Ver pedido", 196)
            if self.task == "V2":
                add("last-heading", "Último pedido", "heading", 16, 270, 328, 36)
                for i, (item, option, count) in enumerate(LAST_ORDER):
                    label = f"{count} × {self.menu[item].name}" + (f" · {option}" if option else "")
                    add(f"last:{i}", label, "label", 16, 310 + 48 * i, 328, 46)
                button("repeat", "Repetir pedido", 516, style="primary")

        elif self.scene == "S1":
            title("Cardápio", 76)
            button("home", "Início", 132, 16, 108, "quiet")
            review_button(132)
            y = 192
            if self.version == "B" and self.task != "Treino":
                for i, name in enumerate(CATEGORIES):
                    button(f"category:{i}", name, y + (i // 2) * 50, 16 + (i % 2) * 168, 160,
                           "selected" if i == self.category else "tab", selected=i == self.category)
                y += 164
            current = None
            for dish in self.menu.values():
                if self.version == "B" and self.task != "Treino" and dish.category != CATEGORIES[self.category]:
                    continue
                if dish.category != current:
                    current = dish.category
                    add(f"section:{dish.category}", dish.category, "heading", 16, y, 328, 42, style="section")
                    y += 48
                action = f"open:{dish.id}"
                data = dict(item_id=dish.id, card=dish.id)
                add(f"name:{dish.id}", dish.name, "name", 16, y, 328, 40, action, **data, part="name")
                add(f"desc:{dish.id}", dish.description, "description", 16, y + 40, 328, 44, action, **data, part="description")
                dy = 84
                if dish.tags:
                    add(f"tags:{dish.id}", "(" + ", ".join(dish.tags) + ")", "tag", 16, y+dy, 328, 27, action, **data, part="tags")
                    dy += 27
                add(f"price:{dish.id}", " / ".join(map(money, dish.prices)), "price", 16, y+dy, 328, 34, action, **data, part="price")
                y += dy + 48
            if self.version == "A":
                button("review", "Ver pedido", y+8, style="primary")
                elements[-1]["id"] = "review:end"
            else:
                summary = f'{sum(r["quantidade"] for r in self.order)} un. · {money(self.state()["total_centavos"])}'
                page = min(self.footer_page, max(0,(len(self.order)-1)//4))
                rows = self.order[page*4:(page+1)*4]
                paged = len(self.order) > 4
                top = scroll_y + 800 - 64 - len(rows)*30 - (50 if paged else 0)
                add("summary", summary, "status", 0, top, 360, 64, style="footer", fixed=True)
                review_button(top+10, fixed=True)
                elements[-1]["id"] = "review:footer"
                for offset, row in enumerate(rows):
                    label = f'{row["quantidade"]} × {row["nome"]}'
                    add(f"summary-line:{page*4+offset}", label, "label", 0, top+64+offset*30, 360, 30,
                        style="footerline", fixed=True, item_id=row["item_id"], part="summary-line")
                if paged:
                    footer_y = top+64+len(rows)*30
                    add("summary-pages", f"Resumo {page+1}/{(len(self.order)+3)//4}", "label", 0, footer_y, 360, 50,
                        style="footerline", fixed=True)
                    if page:
                        button("footer:previous", "Anterior", footer_y+3, 132, 94, fixed=True)
                    if page < (len(self.order)-1)//4:
                        button("footer:next", "Próxima", footer_y+3, 236, 108, fixed=True)

        elif self.scene == "S2":
            dish = self.menu[self.item]
            button("back", "Voltar", 76, 16, 110, "quiet")
            add(f"name:{dish.id}", dish.name, "heading", 16, 140, 328, 66, item_id=dish.id, part="name")
            add(f"desc:{dish.id}", dish.description, "description", 16, 208, 328, 50, item_id=dish.id, part="description", style="plain")
            y = 262
            if dish.tags:
                add(f"tags:{dish.id}", "(" + ", ".join(dish.tags) + ")", "tag", 16, y, 328, 34, item_id=dish.id, part="tags", style="plain")
                y += 38
            price_text = " / ".join(map(money, dish.prices)) if not self.option else money(dish.price(self.option))
            add(f"price:{dish.id}", price_text, "price", 16, y, 328, 38, item_id=dish.id, part="price", style="detailprice")
            y += 50
            if dish.options:
                prompt = "Escolha o tamanho" if dish.category == "Massas" else "Escolha o acompanhamento"
                add("choose", prompt, "label", 16, y, 328, 32)
                y += 36
                for option in dish.options:
                    selected = self.option == option
                    button(f"option:{option}", option, y, style="selected" if selected else "button", selected=selected)
                    y += 50
            add("quantity", f"Quantidade: {self.quantity}", "label", 16, y, 177, 44)
            for verb, label, x, active in (("less", "−", 224, self.quantity > 1), ("more", "+", 292, True)):
                add(verb, label, "button", x, y, 52, 44, verb if active else None, "button" if active else "inactive")
            y += 56
            active = not dish.options or self.option is not None
            action = "save" if self.edit is not None else "add"
            add(action, "Salvar alteração" if self.edit is not None else "Adicionar", "button", 16, y, 328, 46,
                action if active else None, "primary" if active else "inactive")
            if not active:
                add("option-hint", "Selecione uma opção para continuar.", "label", 16, y + 52, 328, 44)

        elif self.scene in ("S3", "S4"):
            title(SCENES[self.scene], 76)
            if self.scene == "S3":
                button("back", "Voltar", 128, 16, 154, "quiet")
                button("home", "Início", 128, 184, 160, "quiet")
            y = 188 if self.scene == "S3" else 138
            if not self.order:
                add("empty", "Seu pedido está vazio.", "status", 16, y, 328, 48)
                y += 60
            for i, row in enumerate(self.order):
                data = dict(item_id=row["item_id"], line=i)
                add(f"line:{i}", row["nome"], "name", 16, y, 328, 38, part="name", **data)
                detail = f'{row["quantidade"]} un. · {money(row["preco_centavos"] * row["quantidade"])}'
                if row["opcao"]:
                    detail = f'{row["opcao"]} · {detail}'
                add(f"line-qty:{i}", detail, "label", 16, y+38, 328, 32, part="quantity", **data)
                y += 74
                if self.scene == "S3":
                    for verb, label, x, w in (("dec", "−", 16, 44), ("inc", "+", 66, 44),
                                               ("edit", "Alterar", 116, 100), ("remove", "Remover", 222, 122)):
                        active = verb != "dec" or row["quantidade"] > 1
                        action = f"{verb}:{i}"
                        add(action, label, "button", x, y, w, 44, action if active else None, "button" if active else "inactive", **data)
                    y += 53
            if self.scene == "S3" and self.removed:
                button("undo", "Desfazer remoção", y, style="quiet")
                y += 52
            total = money(self.state()["total_centavos"])
            add("total", f"Total: {total}", "status", 16, y, 328, 42, style="total")
            if self.scene == "S3":
                add("confirm", "Confirmar pedido", "button", 16, y+48, 328, 44,
                    "confirm" if self.order else None, "primary" if self.order else "inactive")

        elif self.scene == "S5":
            title("Ajuda", 76)
            button("back", "Fechar ajuda", 132, style="quiet")
            add("topic", SCENES[self.help_origin], "heading", 16, 196, 328, 44, style="section")
            y = 248
            for key, label in LAYERS.items():
                button(f"layer:{key}", label, y, style="selected" if key == self.layer else "button", selected=key == self.layer)
                y += 50
            content = json.loads(HELP_PATH.read_text(encoding="utf-8-sig"))[self.help_origin][self.layer]
            add("help-text", content, "description", 16, y+12, 328, 36+24*(len(content)//29+2), style="helptext")
        return elements





