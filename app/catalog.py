"""Canonical menu and participant instructions. All monetary values are in cents."""
from dataclasses import dataclass

CATEGORIES = ("Entradas", "Pratos principais", "Massas", "Bebidas", "Sobremesas")
SIDES = ("Arroz branco", "Purê de batata", "Legumes")
SIZES = ("Individual", "Para dois")
TASKS = {
    "Treino": "Você está numa lanchonete e quer um pão de queijo. Adicione um pão de queijo ao pedido e confirme.",
    "C1": "Você vai almoçar no escritório e quer uma lasanha, tamanho individual. Entre as lasanhas do cardápio, escolha a de menor preço, coloque uma no pedido e confirme o pedido.",
    "C2": "Sua irmã começou um pedido de almoço para vocês duas e pediu que você terminasse. O pedido deve ficar assim: um frango grelhado com arroz, dois sucos de laranja, uma água sem gás e dois pudins de leite. Confira o pedido, corrija o que estiver diferente e confirme.",
    "V1": "Você vai jantar em casa com seu companheiro. Peça um prato vegetariano da seção de pratos principais para cada um (podem ser iguais ou diferentes), uma bebida sem açúcar para cada um e uma sobremesa para dividir. O pedido inteiro não pode passar de R$ 110,00. Confirme o pedido.",
    "V2": "Você quer repetir o seu último pedido, com uma mudança: o macarrão à bolonhesa deve ser no tamanho para dois. O restante deve ficar igual ao último pedido. Confirme o pedido.",
}


@dataclass(frozen=True)
class Item:
    id: int
    category: str
    name: str
    description: str
    tags: tuple
    prices: tuple

    @property
    def options(self):
        return {"Pratos principais": SIDES, "Massas": SIZES}.get(self.category, ())

    def price(self, option=None):
        return self.prices[-1] if option == "Para dois" else self.prices[0]


# Modelagem, Appendix C, pp. 14–15. Order controls both interface alternatives.
_ROWS = [
    ("Bruschetta de tomate", "Pão, tomate, manjericão", "V", 1890),
    ("Pastéis de carne (6 un.)", "Carne moída temperada", "", 2290),
    ("Salada verde", "Alface, rúcula, tomate", "V SL", 1690),
    ("Caldo de feijão", "Feijão, bacon, cheiro-verde", "SL", 1490),
    ("Bolinho de queijo (8 un.)", "Queijo minas", "V", 2190),
    ("Torresmo", "Barriga de porco frita", "SL", 2490),
    ("Frango grelhado", "Peito de frango grelhado", "", 3290),
    ("Filé de tilápia", "Tilápia grelhada com limão", "SL", 3690),
    ("Risoto de cogumelos", "Arroz arbóreo, cogumelos, parmesão", "V", 3990),
    ("Moqueca de legumes", "Palmito, banana-da-terra, leite de coco", "V SL", 3490),
    ("Bife acebolado", "Contrafilé com cebola", "", 3590),
    ("Omelete de espinafre", "Ovos, espinafre, queijo", "V", 2790),
    ("Lasanha de frango", "Frango, molho branco", "", 3690, 6490),
    ("Macarrão à bolonhesa", "Espaguete, molho de carne", "", 3190, 5590),
    ("Lasanha de carne", "Carne moída, molho de tomate", "", 3490, 6190),
    ("Nhoque ao sugo", "Batata, molho de tomate", "V", 2990, 5290),
    ("Lasanha de berinjela", "Berinjela, queijo, molho de tomate", "V", 3890, 6790),
    ("Talharim ao alho e óleo", "Alho, azeite", "V SL", 2790, 4890),
    ("Suco de laranja", "Natural, 400 ml", "SA", 990),
    ("Refrigerante lata", "350 ml", "", 690),
    ("Água sem gás", "500 ml", "SA", 490),
    ("Suco de maracujá", "Adoçado, 400 ml", "", 990),
    ("Chá gelado de limão", "400 ml", "SA", 790),
    ("Limonada suíça", "Adoçada, 400 ml", "", 1190),
    ("Pudim de leite", "Fatia", "", 1290),
    ("Mousse de maracujá", "Taça", "", 1190),
    ("Brownie com sorvete", "Brownie e uma bola de creme", "", 1690),
    ("Salada de frutas", "Frutas da estação", "SL SA", 1090),
    ("Torta de limão", "Fatia", "", 1390),
    ("Sorvete", "Duas bolas", "", 990),
]
MENU = {i: Item(i, CATEGORIES[i // 6], name, desc, tuple(tags.split()), tuple(prices))
        for i, (name, desc, tags, *prices) in enumerate(_ROWS)}

# The sources prescribe five snack items and only name the pão de queijo.
# The other four entries and all training prices are design choices.
TRAINING = {i: Item(i, "Lanchonete", name, desc, (), (price,))
            for i, (name, desc, price) in enumerate((
                ("Pão de queijo", "Uma unidade", 500),
                ("Café coado", "Uma xícara", 400),
                ("Bolo de fubá", "Uma fatia", 600),
                ("Suco de uva", "Um copo", 700),
                ("Sanduíche de queijo", "Uma unidade", 850),
            ), start=30)}

LAST_ORDER = ((13, "Individual", 1), (2, None, 1), (20, None, 2), (25, None, 1))
SISTER_ORDER = ((6, "Arroz branco", 1), (18, None, 2), (20, None, 1), (24, None, 1))


def money(cents):
    return f"R$ {cents // 100},{cents % 100:02d}"
