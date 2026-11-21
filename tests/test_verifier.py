"""Hand-authored analytic records, never interactive trials or provider outputs."""
import unittest
import json
from pathlib import Path

from verifier import evaluate


def row(item, option="", qty=1, price=0):
    return dict(item_id=item, opcao=option, quantidade=qty, preco_centavos=price)


def record(task, rows, sequence, *, confirmed=True, profile="P"):
    events = []
    for step, kind, payload in [(0, "sessao_iniciada", {}), *sequence]:
        events.append(dict(tipo=kind, dados=payload, passo=step, id_tarefa=task,
                           id_configuracao=profile, tela="S3", regiao_visivel={"z": 3}))
    return dict(events=events, final_state=dict(pedido=rows, confirmado=confirmed))


def sight(item, field, clipped=False):
    return dict(item_id=item, elemento=f"{field}/{item}", campo=field,
                legivel=True, fragmentado=clipped)


class MetricsTests(unittest.TestCase):
    def test_archived_handwritten_fixture(self):
        fixture = Path(__file__).with_name("fixtures") / "help_then_quit.json"
        log = json.loads(fixture.read_text(encoding="utf8"))
        result = evaluate(log)
        self.assertEqual(log["expected"], {key: result[key] for key in log["expected"]})

    def test_wrong_neighbour_fragment_slip_and_recovery(self):
        events = [
            (1, "elemento_visto", sight(12, "preco")),
            (1, "elemento_visto", sight(13, "preco", True)),
            (1, "deslize_injetado", {}), (1, "acao_executada", {"acao": "TOCAR"}),
            (2, "acao_executada", {"acao": "VOLTAR"}),
            (3, "acao_executada", {"acao": "DESLOCAR"}), (3, "vista_deslocada", {}),
            (3, "elemento_visto", sight(12, "preco")),
            (4, "acao_executada", {"acao": "TOCAR"}),
            (4, "item_adicionado", dict(item=13, quantidade=1, opcao="Individual")),
            (5, "pedido_confirmado", {}),
        ]
        m = evaluate(record("C1", [row(13, "Individual")], events), 4)
        self.assertEqual((0, 4, 1), (m["S"], m["A"], m["R_A"]))
        self.assertEqual([1, 1, 0, 1, 0, 0], list(m["erros"].values()))
        self.assertEqual((1, 1/3, 2/3), (m["D"], m["V"], m["O"]))
        self.assertEqual(.5, m["Re"]["E4"])
        self.assertEqual((1, 1), (m["MAC"]["Epa!"], m["MAC"]["Pra mim está bom"]))

    def test_quantity_repaired_before_confirmation(self):
        events = [
            (1, "item_adicionado", dict(item=14, opcao="Para dois", quantidade=1)),
            (2, "item_alterado", dict(item=14, opcao="Individual", quantidade=1)),
            (3, "pedido_confirmado", {}),
        ]
        m = evaluate(record("C1", [row(14, "Individual")], events))
        self.assertEqual(1, m["S"])
        self.assertEqual(1, m["erros"]["E3"])
        self.assertIsNone(m["R_A"])

    def test_preloaded_discrepancy_and_comparator(self):
        rows = [row(6, "Arroz branco"), row(18, qty=2), row(20), row(24)]
        m = evaluate(record("C2", rows, [(1, "pedido_confirmado", {})], profile="C"))
        self.assertEqual((0, 1, None), (m["S"], m["Re"]["E5"], m["Re"]["E2"]))

    def test_rule_violation_from_static_event_fixture(self):
        # Evaluating a fixed log exercises E6 without running or tuning on V1.
        rows = [row(8, "Legumes", 2, 3990), row(18, qty=2, price=990), row(26, price=1690)]
        m = evaluate(record("V1", rows, [(1, "pedido_confirmado", {})]))
        self.assertEqual(1, m["erros"]["E6"])
        self.assertEqual(0, m["S"])

    def test_impasse_layers_and_interruption(self):
        events = [(i, "acao_executada", {"acao": "TOCAR"}) for i in range(1, 7)]
        events += [(6, "ajuda_aberta", dict(camada="dica", topico="Tamanho")),
                   (7, "acao_executada", {"acao": "TOCAR"}),
                   (7, "ajuda_aberta", dict(camada="contexto", topico="Opções")),
                   (8, "desistencia", {})]
        m = evaluate(record("C1", [], events, confirmed=False))
        self.assertEqual((0, 2, 6/7), (m["S"], m["U"], m["U_primeira_posicao"]))
        self.assertEqual({"1": 1, "2": 1, "3": 0}, m["U_por_camada"])
        self.assertEqual([2, 1, 0, 0, 1, 1], list(m["MAC"].values()))
        self.assertIsNone(m["D"])

    def test_failure_excludes_success_denominator_and_limit_counts(self):
        for terminal, expected in (("falha_tecnica", None), ("limite_atingido", 0)):
            m = evaluate(record("C1", [], [(1, terminal, {})], confirmed=False))
            self.assertEqual(expected, m["S"])
            self.assertEqual(terminal, m["interrupcao"])
        m = evaluate(record("C1", [row(14, "Individual")], []))
        self.assertIsNone(m["S"])
        self.assertEqual("desconhecido", m["resultado"])

    def test_fragment_after_committed_selection_is_not_association(self):
        sequence = [
            (1, "acao_executada", {"acao": "TOCAR", "alvo": "open:13"}),
            (2, "elemento_visto", sight(13, "preco", True)),
            (3, "item_adicionado", dict(item=13, opcao="Individual", quantidade=1)),
            (4, "pedido_confirmado", {}),
        ]
        result = evaluate(record("C1", [row(13, "Individual")], sequence))
        self.assertEqual((1, 0), (result["erros"]["E1"], result["erros"]["E2"]))

    def test_corrected_wrong_selection_has_no_retained_error(self):
        sequence = [
            (1, "elemento_visto", sight(13, "preco", True)),
            (2, "item_adicionado", dict(item=13, opcao="Individual", quantidade=1)),
            (3, "item_removido", dict(item=13)),
            (4, "item_adicionado", dict(item=14, opcao="Individual", quantidade=1)),
            (5, "pedido_confirmado", {}),
        ]
        result = evaluate(record("C1", [row(14, "Individual")], sequence))
        self.assertEqual((0, 0), (result["erros"]["E1"], result["erros"]["E2"]))
        self.assertEqual((3, 1), (result["oportunidades"]["E1"], result["oportunidades"]["E3"]))

    def test_oversize_uses_geometry_and_unknown_view_is_not_omission(self):
        log = record("C1", [], [(1, "desistencia", {})], confirmed=False)
        for e in log["events"]:
            e.update(tela="S1", regiao_visivel={"z": 1.05})
        self.assertEqual(0, evaluate(log)["oportunidades"]["E2"])
        log["events"][0]["regiao_visivel"] = {"z": 1.2}
        self.assertEqual(3, evaluate(log)["oportunidades"]["E2"])
        for e in log["events"]:
            e.update(regiao_visivel=None, synthetic=False)
        result = evaluate(log)
        self.assertIsNone(result["O"])
        self.assertIsNone(result["V"])
        self.assertIsNone(result["oportunidades"]["E2"])

    def test_no_false_slip_after_intervening_human_action(self):
        sequence = [
            (1, "acao_executada", dict(acao="TOCAR", alvo="open:13")),
            (1, "tela_alterada", dict(anterior="S1", nova="S2")),
            (2, "acao_executada", dict(acao="TOCAR", alvo="option:Individual")),
            (3, "acao_executada", dict(acao="TOCAR", alvo="back")),
            (4, "desistencia", {}),
        ]
        for skip, inferred in ((False, 0), (True, 1)):
            log = record("C1", [], [e for e in sequence if not skip or e[0] != 2], confirmed=False)
            for e in log["events"]:
                e["synthetic"] = False
            result = evaluate(log)
            self.assertEqual((inferred, inferred), (result["MAC"]["Epa!"], result["erros"]["E4"]))
            self.assertIsNone(result["Re"]["E4"])

