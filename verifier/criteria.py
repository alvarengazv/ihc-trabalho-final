"""Analyst-only predicates. Menu identifiers follow Appendix C, starting at zero."""
from collections import Counter

EXPECTED = {
    "Treino": {(30, ""): 1},
    "C1": {(14, "Individual"): 1},
    "C2": {(6, "Arroz branco"): 1, (18, ""): 2, (20, ""): 1, (24, ""): 2},
    "V2": {(13, "Para dois"): 1, (2, ""): 1, (20, ""): 2, (25, ""): 1},
}
REQUIRED = {
    "C1": ({12, 14, 16}, "preco"),
    "C2": ({6, 18, 20, 24}, "linha"),
    "V2": ({13, 2, 20, 25, 26}, "linha"),
    "Treino": ({30}, "nome"),
}
VEGETARIAN = {8, 9, 11}
UNSWEETENED = {18, 20, 22}
DESSERTS = set(range(24, 30))
SIDES = {"Arroz branco", "Purê de batata", "Legumes"}


def quantities(rows):
    result = Counter()
    for row in rows:
        result[(int(row["item_id"]), row.get("opcao") or "")] += row["quantidade"]
    return result


def dinner_rules(rows):
    main = drink = dessert = extras = cost = 0
    suitable_main = suitable_drink = True
    for row in rows:
        item = int(row["item_id"])
        qty = row["quantidade"]
        if 6 <= item < 12:
            main += qty
            suitable_main &= item in VEGETARIAN and row.get("opcao") in SIDES
        elif 18 <= item < 24:
            drink += qty
            suitable_drink &= item in UNSWEETENED
        elif item in DESSERTS:
            dessert += qty
        else:
            extras += qty
        cost += row["preco_centavos"] * qty
    return (main == 2 and suitable_main, drink == 2 and suitable_drink,
            dessert == 1, extras == 0, cost <= 11000)


def order_matches(task, rows):
    if any(type(r["quantidade"]) is not int or r["quantidade"] <= 0 for r in rows):
        return False
    return all(dinner_rules(rows)) if task == "V1" else quantities(rows) == EXPECTED[task]
