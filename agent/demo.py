"""A scripted mechanism fixture for the recording. No API, trial or pilot log."""
import json

from app.model import MenuApp
from .config import sample
from .mechanisms import Channel
from .run import observation


def show(label, value):
    print(label)
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main():
    print("Demonstração técnica com ações roteirizadas. Amostra fora do piloto, sem LLM.")
    app = MenuApp("C2", "B")
    app.apply("review")
    reader = Channel(sample("P", 42))
    frame = observation(app, reader)
    show("M1 e M5 • Vista inicial da revisão (x, y, largura, altura)", reader.region)
    show("Trechos que entram na observação", [e.get("texto") for e in frame["vista"] if e.get("texto")])
    show("M6 • Gestos de varredura disponíveis", [a for a in frame["acoes"] if a.startswith("DESLOCAR")])
    for _ in range(20):
        reader.move(reader.actions["DESLOCAR(próximo)"])
        second = observation(app, reader)
        if any(e.get("texto") for e in second["memoria"]):
            break
    show("M2 • Lembranças dos signos que saíram da janela", second["memoria"])

    app = MenuApp("C1", "B")
    app.apply("category:2")
    elements = app.elements()
    price = next(e for e in elements if e["id"] == "price:12")
    # This deliberate camera position makes the two sign fragments reproducible.
    reader.y = price["box"][1]
    reader.x = 18
    observation(app, reader)
    show("M3 • Fragmento de preço apresentado sem o nome acima da janela",
         reader.visible[price["id"]][1])

    # Seed selection is explicit, for a filmable mechanism demonstration only.
    # No random outcome from this fixture is aggregated as a pilot observation.
    for seed in range(1000):
        fixture = Channel(sample("P", seed))
        fixture.x, fixture.y = 18, price["box"][1] - fixture.region[3] / 2 + 12
        observation(app, fixture)
        slip = fixture.slip(("pan", (0, 0)))
        if slip and slip[0][1]:
            break
    else:
        raise RuntimeError("No illustrative card hit")
    move, point = slip
    show("M4 • Evento de teste reproduzível", {"tipo": "deslize_injetado", "semente": seed,
         "p": fixture.params["p"], "proposta": "DESLOCAR", "executada": "TOCAR",
         "ponto_inicial": point, "transicao_observada": app.apply(move[1])})

    fixture.scene_changed()
    observation(app, fixture)
    for count in range(1, 100):
        if fixture.impasse(False):
            break
    else:
        raise RuntimeError("No illustrative help trigger")
    opening = app.apply("help")
    show("M7 • Abertura da ajuda após ações roteirizadas sem progresso",
         {"acoes_estagnadas": count, "n": fixture.params["n"], "q": fixture.params["q"],
          "eventos": opening})
    assert any(e["tipo"] == "ajuda_aberta" for e in opening)
    fixture.scene_changed(help_open=True)
    help_frame = observation(app, fixture)
    show("Primeira observação do subdiálogo de ajuda", help_frame["vista"][:3])


if __name__ == "__main__":
    main()

