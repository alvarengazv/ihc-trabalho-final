"""Compute per-run instrumentation metrics from the external record."""
from collections import Counter, defaultdict

from .criteria import DESSERTS, EXPECTED, REQUIRED, UNSWEETENED, VEGETARIAN
from .criteria import SIDES, dinner_rules, order_matches, quantities


def fraction(numerator, denominator):
    return numerator / denominator if denominator else None


def data(event):
    return event.get("dados", event)


def layer_number(event):
    key = str(data(event).get("camada"))
    return {"dica": "1", "contexto": "2", "guia": "3"}.get(key, key)


def action_name(event):
    action = data(event).get("acao")
    return action.get("acao", action.get("tipo")) if isinstance(action, dict) else action


def human_return_signatures(events):
    """Touch opening a scene followed by return, with no intervening scene action."""
    pending = None
    matches = set()
    for event in events:
        d = data(event)
        step = event["passo"]
        if event["tipo"] == "acao_executada":
            if pending is not None and (action_name(event) == "VOLTAR" or d.get("alvo") == "back"):
                matches.add(step)
            pending = None
        if event["tipo"] == "tela_alterada" and d.get("nova") == "S2" and d.get("anterior") != "S2":
            pending = step
    return matches


def mac_signatures(events, correct, threshold):
    counts = dict.fromkeys(("Socorro!", "Desisto", "Pra mim está bom", "Epa!",
                            "Cadê?", "O que é isso?"), 0)
    known = set()
    grouped = defaultdict(list)
    for event in events:
        grouped[event["passo"]].append(event)
    stagnant = 0
    slip_age = None
    for group in grouped.values():
        progress = False
        acted = False
        for event in group:
            kind = event["tipo"]
            d = data(event)
            if kind == "ajuda_aberta":
                counts["Socorro!"] += 1
                if layer_number(event) == "1" and d.get("topico"):
                    counts["O que é isso?"] += 1
            elif kind == "desistencia":
                counts["Desisto"] += 1
            elif kind == "pedido_confirmado" and not correct:
                counts["Pra mim está bom"] += 1
            elif kind == "deslize_injetado":
                slip_age = -1
            elif kind == "acao_executada":
                acted = True
                if slip_age is not None:
                    slip_age += 1
                    if 0 < slip_age <= 2 and (action_name(event) == "VOLTAR" or
                            str(d.get("alvo", "")).casefold() in {"voltar", "desfazer", "back", "undo"}):
                        counts["Epa!"] += 1
                        slip_age = None
                    elif slip_age >= 2:
                        slip_age = None
            if kind == "elemento_visto":
                key = (event.get("tela"), d.get("elemento"))
                if key not in known:
                    progress = True
                    known.add(key)
            if kind in {"tela_alterada", "item_adicionado", "item_removido", "item_alterado"}:
                progress = True
        stagnant = 0 if progress else stagnant + int(acted)
        if acted and stagnant == threshold:
            counts["Cadê?"] += 1
    return counts


def exposure(events, required, field, task):
    # A sign entering twice is a revisit only after leaving the view. The logger
    # emits entry events, not periodic snapshots of still-visible elements.
    entries = Counter()
    revisits = 0
    seen_before = set()
    decision_seen = set()
    quantity_seen = set()
    requires_quantities = task in {"C2", "V2"} and any(
        "criterio_visivel" in data(e) for e in events if e["tipo"] == "elemento_visto")
    chosen = set()
    stopped = False
    for event in events:
        if event["tipo"] == "pedido_confirmado":
            break
        if event["tipo"] == "item_adicionado":
            item = data(event).get("item")
            if task == "V1" and item in required and item not in chosen:
                chosen.add(item)
                if item in seen_before:
                    decision_seen.add(item)
            if task in {"C1", "Treino"}:
                stopped = True
        if event["tipo"] != "elemento_visto":
            continue
        d = data(event)
        item = d.get("item_id")
        if item is None or not d.get("legivel"):
            continue
        item = int(item)
        if item not in required:
            continue
        if requires_quantities and d.get("campo") == "quantidade" and d.get("criterio_visivel"):
            quantity_seen.add(item)
        if d.get("campo") == field:
            if field in {"preco", "linha"} and not d.get("criterio_visivel", True):
                continue
            if d.get("reentrada", entries[item] > 0 and d.get("entrada", True)):
                revisits += 1
            entries[item] += 1
            if not stopped:
                seen_before.add(item)
    if requires_quantities:
        seen_before &= quantity_seen
    return entries, decision_seen if task == "V1" else seen_before, revisits


def selected_errors(events, task, rows):
    """Reconstruct committed choices; post-selection signs cannot explain a choice."""
    expected = EXPECTED.get(task, {})
    allowed = {i for i, _ in expected} if expected else VEGETARIAN | UNSWEETENED | DESSERTS
    wrong_kept = set()
    wrong_removed = set()
    associations = set()
    isolated = {}
    at_open = {}
    e3 = item_choices = composition_choices = 0
    automatic_copy = None
    for event in events:
        kind = event["tipo"]
        d = data(event)
        if kind == "elemento_visto" and d.get("legivel"):
            if d.get("campo") in {"preco", "etiqueta", "quantidade"}:
                isolated[d.get("item_id"), d["campo"]] = d.get("fragmentado", False)
            continue
        if kind == "acao_executada":
            target = str(d.get("alvo"))
            if target == "repeat":
                automatic_copy = event["passo"]
            if target.startswith("open:"):
                item = int(target.split(":")[1])
                field = "etiqueta" if task == "V1" else "preco"
                at_open[item] = isolated.get((item, field), False)
            continue
        if kind not in {"item_adicionado", "item_removido", "item_alterado"}:
            continue
        if event["passo"] == automatic_copy:
            continue
        item = d.get("item", d.get("item_id"))
        if kind == "item_removido":
            item_choices += 1
            if task in {"C2", "V2"} and item in allowed:
                wrong_removed.add(item)
            wrong_kept.discard(item)
            associations.discard(item)
            continue
        if kind == "item_adicionado":
            item_choices += 1
            wrong_removed.discard(item)
            if item not in allowed:
                wrong_kept.add(item)
                field = "etiqueta" if task == "V1" else "preco"
                fragmented = at_open.get(item, isolated.get((item, field), False))
                if fragmented and any(abs(item - i) == 1 and item // 6 == i // 6 for i in allowed):
                    associations.add(item)
        if item not in allowed or "quantidade" not in d:
            continue
        composition_choices += 1
        qty, option = d["quantidade"], d.get("opcao") or ""
        if task == "V1":
            max_qty = 1 if item in DESSERTS else 2
            e3 += int(qty > max_qty or qty < 1 or (item in VEGETARIAN and option not in SIDES))
        else:
            mistaken = expected.get((item, option)) != qty
            e3 += int(mistaken)
            if task == "C2" and mistaken and isolated.get((item, "quantidade")):
                order = [r["item_id"] for r in d.get("pedido", [])]
                if item in order and 24 in order and abs(order.index(item) - order.index(24)) == 1:
                    associations.add(item)
    final_items = {row["item_id"] for row in rows}
    n_wrong = len(wrong_kept & final_items) + len(wrong_removed - final_items)
    return n_wrong, len(associations), e3, item_choices, composition_choices


def oversized_targets(events, task, required, profile):
    if profile in {"C", "G"}:
        return 0
    # App S1 card components and S3 review row are 328 CSS px wide.
    # Heights of their semantic groups are <= 160 CSS px. At this portrait
    # aspect ratio horizontal clipping always occurs before vertical clipping.
    scene = "S3" if task in {"C2", "V2"} else "S1"
    relevant = [e for e in events if e.get("tela") == scene]
    regions = [e["regiao_visivel"] for e in relevant if e.get("regiao_visivel")]
    if not regions:
        return None
    return len(required) if any(360 / r["z"] < 328 for r in regions) else 0


def evaluate(log, reference_actions=None):
    events = log["events"]
    task = events[0]["id_tarefa"]
    state = log["final_state"]
    rows = state["pedido"]
    by_kind = defaultdict(list)
    for event in events:
        by_kind[event["tipo"]].append(event)
    cfg = events[0]["id_configuracao"]
    meta = log.get("meta", {})
    if reference_actions is None:
        reference_actions = meta.get("reference_actions")
    actions = by_kind["acao_executada"]
    a = len(actions)
    confirmed = bool(state.get("confirmado") and by_kind["pedido_confirmado"])
    correct = order_matches(task, rows)
    terminal = next((e["tipo"] for e in reversed(events)
                     if e["tipo"] in {"falha_tecnica", "desistencia", "limite_atingido"}), None)
    s = None if terminal == "falha_tecnica" else int(confirmed and correct and not terminal)
    incomplete = not confirmed and terminal is None
    if incomplete:
        s = None
    counts = dict.fromkeys(("E1", "E2", "E3", "E4", "E5", "E6"), 0)
    ordered_food_drink = {row["item_id"] for row in rows if 6 <= row["item_id"] < 12
                         or 18 <= row["item_id"] < 24}
    required, field = REQUIRED.get(task, (ordered_food_drink, "etiqueta"))
    entries, seen_before, revisits = exposure(events, required, field, task)
    actual = quantities(rows)
    counts["E1"], counts["E2"], counts["E3"], item_choices, composition_choices = selected_errors(events, task, rows)
    counts["E4"] = len(by_kind["deslize_injetado"])
    human = events[0].get("synthetic") is False
    human_returns = human_return_signatures(events) if human else set()
    if human:
        counts["E4"] = len(human_returns)
    if confirmed and task in {"C2", "V2"}:
        counts["E5"] = int(actual[(24, "")] != 2 if task == "C2" else actual[(26, "")] > 0)
    if confirmed and task == "V1":
        counts["E6"] = dinner_rules(rows).count(False)
    n_pan = len(by_kind["vista_deslocada"])
    n_zoom = len(by_kind["zoom_alterado"])
    opportunities = {
        "E1": item_choices,
        "E2": oversized_targets(events, task, required, cfg),
        "E3": composition_choices,
        "E4": n_pan if human else n_pan + counts["E4"],
        "E5": int(task in {"C2", "V2"}),
        "E6": 5 if task == "V1" else 0,
    }
    opens = by_kind["ajuda_aberta"]
    per_layer = {str(i): sum(layer_number(e) == str(i) for e in opens)
                 for i in (1, 2, 3)}
    first = (sum(e["passo"] <= opens[0]["passo"] for e in actions) if opens else None)
    observed = any(e.get("regiao_visivel") for e in events)
    mac = mac_signatures(events, correct, int(meta.get("n", 5)))
    if human:
        mac["Epa!"] = len(human_returns)
        if not observed:
            mac["Cadê?"] = None
    return {
        "resultado": ("desconhecido" if incomplete else "falha_tecnica" if s is None else "interrupcao" if terminal
                      else "sucesso" if s else "erro"),
        "S": s, "A": a, "N_ref": reference_actions, "R_A": fraction(a, reference_actions),
        "erros": counts, "oportunidades": opportunities,
        "Re": {key: fraction(value, opportunities[key]) for key, value in counts.items()},
        "D": fraction(n_pan + n_zoom, len(entries)),
        "V": fraction(revisits, len(required)) if observed else None,
        "O": fraction(len(required - seen_before), len(required)) if observed else None,
        "U": len(opens), "U_por_camada": per_layer, "U_primeira_posicao":
            fraction(first, a) if opens else None,
        "MAC": mac,
        "interrupcao": terminal, "propostas_rejeitadas": len(by_kind["acao_rejeitada"]),
    }
