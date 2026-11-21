import json
import math
import random
import re
from collections import OrderedDict

ROLES = {
    "heading": "título", "button": "botão", "price": "texto", "label": "texto",
    "description": "texto", "name": "texto", "tag": "marcador", "status": "mensagem",
}
FREE_PAN = "DESLOCAR(dx%,dy%)"


def criterion_span(element, line):
    """Return a decisive glyph span for externally audited task signs."""
    text = line["text"]
    if element.get("part") == "price":
        match = re.search(r"\d+,\d{2}", text)
    elif element["id"].startswith("line-qty:"):
        match = re.search(r"(?<!\d)\d+(?= un\.)", text)
    elif element["id"].startswith("line:"):
        # Readable lead fragment of the item name, short enough at 7×.
        match = re.match(r"\S{1,4}", text)
    else:
        match = None
    if match is None:
        return None
    x, y, width, height = line["box"]
    advance = width / len(text)
    return [x + match.start() * advance, y, (match.end() - match.start()) * advance, height]


def criterion_visible(element, clip):
    for line in element.get("text_lines", []):
        span = criterion_span(element, line)
        visible = intersection(span, clip) if span and clip else None
        if visible and visible[2] >= span[2] - 1e-7 and visible[3] >= span[3] / 2:
            return True
    return False


def free_pan_offset(token):
    """Local gesture displacement, expressed as percentages of the aperture."""
    match = re.fullmatch(r"DESLOCAR\((-?\d{1,3})%,(-?\d{1,3})%\)", token, re.ASCII)
    if match:
        dx, dy = map(int, match.groups())
        if (dx or dy) and max(abs(dx), abs(dy)) <= 100:
            return dx / 100, dy / 100
    return None


def intersection(box, view):
    x, y, w, h = box
    vx, vy, vw, vh = view
    left, top = max(x, vx), max(y, vy)
    width, height = min(x + w, vx + vw) - left, min(y + h, vy + vh) - top
    return (left, top, width, height) if width > 0 and height > 0 else None


def fragment(text, box, clip):
    """Character-proportional approximation in the glyph box supplied by the UI."""
    if not text or not clip:
        return ""
    x, y, w, h = box
    left, top, width, height = clip
    # Horizontal clipping exposes only complete character cells. A sliver of a
    # line is insufficient for reading, independently of the zoom threshold.
    if height < h * 0.5:
        return ""
    first = math.ceil((left - x) / w * len(text) - 1e-8)
    last = math.floor((left + width - x) / w * len(text) + 1e-8)
    return text[first:last]


class Channel:
    def __init__(self, params):
        self.params = params
        self.active = set(params["mechanisms"])
        self.rng = random.Random(f'{params["seed"]}/gestures')
        self.z = params["z"]
        self.x = self.y = 0.0
        self.previous = OrderedDict()
        self.memory = OrderedDict()
        self.known = set()
        self.stagnation = 0
        self.help_open = False
        self.skip_stage = 0
        self._sealed = None

    @property
    def region(self):
        return [self.x, self.y, 360 / self.z, 800 / self.z]

    def scene_changed(self, help_open=False):
        self.x = self.y = 0.0
        self.skip_stage = 0
        if self.help_open and not help_open:
            self.previous.clear()
            for key in list(self.memory):
                if key[0] == "S5":
                    del self.memory[key]
        self.help_open = help_open

    def constrain(self, height):
        w, h = self.region[2:]
        self.x = max(0, min(360 - w, self.x))
        self.y = max(0, min(max(800, height) - h, self.y))

    def observe(self, elements, scene, height=None, scroll=0):
        if scene == "S5" and not self.help_open:
            raise ValueError("Help observation requires logged help opening")
        self.elements = elements
        self.scene = scene
        self.height = height or max([800] + [e["box"][1] + e["box"][3] for e in elements if not e.get("fixed")])
        self.scroll = scroll
        self.constrain(self.height)
        # Ablations: M1 restricts regular scenes; M5 independently enforces S3.
        cropped = "M1" in self.active or (scene == "S3" and "M5" in self.active)
        full_page = self.params["profile"] == "G"
        view = self.region if cropped else [0, scroll, 360, 800]
        if full_page:
            view = [0, 0, 360, self.height]
        readable = self.z >= self.params["z_leg"] or not cropped
        self.actions = {}
        self.visible = {}
        self.seen_events = []
        current = OrderedDict()
        screen = []
        crops = {e["id"]: intersection(e["box"] if full_page else e.get("visible_box", e["box"]), view)
                 for e in elements}
        def visible_text(e):
            crop = crops[e["id"]]
            if not readable or crop is None:
                return ""
            lines = e.get("text_lines", [{"text": e["text"], "box": e.get("text_box", e["box"])}])
            return " ".join(s for line in lines
                            if (s := fragment(line["text"], line["box"], intersection(line["box"], crop))))
        names = {e.get("item_id"): visible_text(e) for e in elements
                 if e.get("part") == "name" and visible_text(e).strip()}
        for e in elements:
            clip = crops[e["id"]]
            if not clip:
                continue
            key = (scene, e["id"])
            box = e["box"]
            text = visible_text(e)
            is_attribute = e.get("part") in ("tags", "tag", "price", "description") or (
                scene == "S3" and e.get("part") == "quantity")
            isolated = (self.z > 1 and is_attribute and
                        e.get("item_id") is not None and e["item_id"] not in names)
            pos = [round(clip[0] - view[0], 2), round(clip[1] - view[1], 2),
                   round(clip[2], 2), round(clip[3], 2)]
            public = {"tipo": ROLES.get(e["role"], "texto"), "caixa": pos}
            if readable and e.get("selected"):
                public["aparencia"] = "realçado"
            if text:
                public["texto"] = text
                if (is_attribute and ("M3" not in self.active or not self.params["f"])
                        and e.get("item_id") in names):
                    public["nome_visivel"] = names[e["item_id"]]
            if e.get("action"):
                action = f"TOCAR({len(screen) + 1})"
                public["gesto"] = action
                self.actions[action] = ("touch", e["action"])
            screen.append(public)
            self.visible[e["id"]] = (e, public)
            current[key] = {"tipo": public["tipo"], **({"texto": text} if text else {})}
            if key not in self.previous or self.previous[key].get("texto", "") != text:
                self.seen_events.append({
                    "elemento": e["id"], "item_id": e.get("item_id"),
                    "campo": "linha" if e["id"].startswith("line:") else {
                        "name": "nome", "price": "preco", "tag": "etiqueta", "tags": "etiqueta",
                        "quantity": "quantidade"}.get(e.get("part"), "outro"),
                    "legivel": bool(text.strip()), "fragmentado": isolated,
                    "criterio_visivel": bool(text.strip()) and criterion_visible(e, clip),
                    "fracao_visivel": round(clip[2] * clip[3] / (box[2] * box[3]), 6),
                    "novo": key not in self.known, "entrada": key not in self.previous,
                    "reentrada": key in self.known and key not in self.previous, "texto": text,
                })
                self.known.add(key)
        for key, value in self.previous.items():
            if key not in current:
                self.memory[key] = value
                self.memory.move_to_end(key)
        for key in current:
            self.memory.pop(key, None)
        capacity = self.params["k"] if "M2" in self.active or full_page else 0
        while capacity is not None and len(self.memory) > capacity:
            self.memory.popitem(last=False)
        self.previous = current
        self._navigation(elements, scene)
        result = {"vista": screen, "memoria": list(self.memory.values()), "acoes": list(self.actions)}
        self._sealed = json.dumps(result, ensure_ascii=False, sort_keys=True)
        return result

    def check_projection(self, projection):
        if json.dumps(projection, ensure_ascii=False, sort_keys=True) != self._sealed:
            raise ValueError("Outgoing context differs from the projected visual channel")

    def _navigation(self, elements, scene):
        actions = self.actions
        available = {e.get("action") for e in elements}
        if "help" in available:
            actions["TOCAR(Ajuda)"] = ("touch", "help")
        if "back" in available:
            actions["VOLTAR"] = ("touch", "back")
        actions["DESISTIR"] = ("quit", None)
        if self.params["profile"] == "G":
            return
        if self.z < 7:
            actions["AMPLIAR"] = ("zoom", min(7, self.z + 1))
        if self.z > 1:
            actions["REDUZIR"] = ("zoom", max(1, self.z - 1))
        policy = self.params["s"] if "M6" in self.active else "livre"
        w, h = self.region[2:]
        max_x, max_y = 360 - w, max(self.height - h, 0)
        last_col = max(0, math.ceil(360 / w) - 1)
        col = min(last_col, math.ceil(self.x / w - 1e-8))
        def pan(label, x, y):
            target = (max(0, min(max_x, x)), max(0, min(max_y, y)))
            if target != (self.x, self.y):
                actions[f"DESLOCAR({label})"] = ("pan", target)
        if policy in ("linear", "livre"):
            if col < last_col:
                pan("próximo", (col + 1) * w, self.y)
            elif self.y < max_y:
                pan("próximo", 0, self.y + h)
            if col:
                pan("anterior", (col - 1) * w, self.y)
            elif self.y:
                pan("anterior", max_x, self.y - h)
            pan("início da linha", 0, self.y)
        if policy == "livre":
            if max_x or max_y:
                actions[FREE_PAN] = ("pan", None)
            for name, dx, dy in (("direita", w, 0), ("esquerda", -w, 0),
                                 ("baixo", 0, h), ("cima", 0, -h)):
                pan(name, self.x + dx, self.y + dy)
        if policy == "salteada" and self.z <= self.params["z_leg"] and (self.skip_stage == 1 or self.z == 1):
            # Point selection repositions the aperture in an adjacent band or
            # within the current overview. Zoom-in is a separate gesture.
            for name, fx, fy in (("ponto superior", 0, -1), ("ponto inferior", 0, 1),
                                 ("ponto à direita", 1, 0), ("ponto à esquerda", -1, 0)):
                pan(name, self.x + fx * w, self.y + fy * h)

    def resolve(self, token):
        offset = free_pan_offset(token)
        if FREE_PAN in self.actions and offset is not None:
            w, h = self.region[2:]
            return "pan", (self.x + offset[0] * w, self.y + offset[1] * h)
        if token == FREE_PAN or token not in self.actions:
            raise ValueError("Action absent from current channel")
        return self.actions[token]

    def move(self, move):
        kind, value = move
        if kind == "zoom":
            self.skip_stage = int(value < self.z)
            self.z = value
        elif kind == "pan":
            self.x, self.y = value
            self.skip_stage = 2
        self.constrain(self.height)

    def slip(self, move):
        if move[0] != "pan" or "M4" not in self.active or self.rng.random() >= self.params["p"]:
            return None
        x, y, w, h = self.region
        point = [x + w / 2, y + h / 2]
        hit = next((e for e, _ in reversed(list(self.visible.values()))
                    if intersection(e.get("visible_box", e["box"]), [*point, 1e-7, 1e-7])), None)
        return (("touch", hit.get("action") if hit else None), point)

    def impasse(self, progressed):
        self.stagnation = 0 if progressed else self.stagnation + 1
        if ("M7" in self.active and self.stagnation >= self.params["n"] and
                not self.help_open and "TOCAR(Ajuda)" in self.actions and
                self.rng.random() < self.params["q"]):
            self.stagnation = 0
            return True
        return False

