"""Channel, API adapter boundary and reproducibility checks. No live API in tests."""
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.config import calibration_only, digest, sample
from agent.mechanisms import Channel
from agent.mechanisms.channel import FREE_PAN
from agent.policies.remote import ProviderError, RemotePolicy, guard_request, make_prompt, strict_action
from agent.run import EVENTS, Trial, observation, reference_count
from app.model import MenuApp


def sign(key, text, x, y, w=80, h=20, **fields):
    return dict(id=key, text=text, role="label", box=[x, y, w, h], **fields)


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.params = dict(sample("P", 7), z=4, k=2)
        self.chan = Channel(self.params)

    def test_projected_text_and_no_hidden_names(self):
        signs = [sign("name:9", "Identidade oculta", 0, 220, part="name", item_id=9),
                 sign("price:9", "0123456789", 50, 30, 100, part="price", item_id=9, action="open:9")]
        view = self.chan.observe(signs, "S1")
        self.assertEqual(self.chan.region, [0, 0, 90, 200])
        self.assertEqual(view["vista"][0]["texto"], "0123")
        self.assertTrue(self.chan.seen_events[0]["fragmentado"])
        prompt = make_prompt("C1", view, self.chan)
        for token in ("Identidade oculta", "456789", "open:9", "price:9", "item_id", "Lasanha de carne"):
            self.assertNotIn(token, prompt)
        self.assertIn("Pão de queijo", prompt)
        self.assertIn("TOCAR(1)", prompt)
        self.chan.z = 2
        low = self.chan.observe(signs, "S1")
        self.assertFalse(any("texto" in e for e in low["vista"]))

    def test_memory_fifo_and_nonactionable(self):
        signs = [sign(f"id-{i}", f"Palavra{i}", 0, i*220) for i in range(5)]
        for i in range(4):
            self.chan.y = i * 220
            view = self.chan.observe(signs, "S1", height=1200)
        self.assertEqual([e["texto"] for e in view["memoria"]], ["Palavra1", "Palavra2"])
        self.assertNotIn("Palavra0", make_prompt("C1", view, self.chan))
        self.assertTrue(all("gesto" not in e for e in view["memoria"]))
        self.chan.y = 440
        self.chan.observe(signs, "S1", height=1200)
        self.assertTrue(self.chan.seen_events[0]["reentrada"])

    def test_guard_checks_every_surface(self):
        base = self.chan.observe([sign("legal", "Escolha", 0, 10)], "S1")
        for key in ("vista", "memoria", "acoes"):
            contaminated = copy.deepcopy(base)
            contaminated[key].append("unbuffered visible-looking content")
            with self.assertRaises(ValueError):
                make_prompt("C1", contaminated, self.chan)
        forged = self.chan.observe([sign("legal", "HTA", 0, 20)], "S1")
        with self.assertRaises(ValueError):
            make_prompt("C1", forged, self.chan)

    def test_error_origin_hit_and_background(self):
        self.chan.params["p"] = 1
        self.chan.observe([sign("pick", "Exemplo", 40, 90, 20, 20, action="open:21")], "S1")
        move, point = self.chan.slip(("pan", (90, 0)))
        self.assertEqual((move, point), (("touch", "open:21"), [45, 100]))
        self.chan.observe([], "S1")
        self.assertEqual(self.chan.slip(("pan", (90, 0)))[0], ("touch", None))
        self.assertIsNone(self.chan.slip(("touch", "help")))

    def test_impasse_is_progress_relative(self):
        self.chan.params.update(n=2, q=1)
        self.chan.observe([sign("help", "Ajuda", 255, 12, action="help")], "S1")
        self.assertFalse(self.chan.impasse(False))
        self.assertFalse(self.chan.impasse(True))
        self.assertFalse(self.chan.impasse(False))
        self.assertTrue(self.chan.impasse(False))
        self.chan.scene_changed(True)
        self.assertFalse(self.chan.impasse(False))

    def test_help_only_after_open_and_cleared_on_exit(self):
        public_sign = [sign("help-text", "Instrução", 0, 30)]
        with self.assertRaises(ValueError):
            self.chan.observe(public_sign, "S5")
        self.chan.observe([sign("identity", "Prato já visto", 0, 20)], "S1")
        self.chan.scene_changed(help_open=True)
        self.chan.observe(public_sign, "S5")
        self.chan.scene_changed(False)
        outside = self.chan.observe([], "S1")
        self.assertNotIn("Instrução", make_prompt("C1", outside, self.chan))
        self.assertIn("Prato já visto", make_prompt("C1", outside, self.chan))

    def test_scan_and_zoom_gate(self):
        self.chan.observe([], "S1", height=2000)
        self.assertIn("DESLOCAR(próximo)", self.chan.actions)
        self.assertNotIn("DESLOCAR(baixo)", self.chan.actions)
        self.assertIn("AMPLIAR", self.chan.actions)
        self.chan.params["s"] = "salteada"
        self.chan.observe([], "S1", height=2000)
        self.assertFalse(any(key.startswith("DESLOCAR") for key in self.chan.actions))
        self.chan.move(self.chan.actions["REDUZIR"])
        self.chan.observe([], "S1", height=2000)
        self.assertIn("DESLOCAR(ponto inferior)", self.chan.actions)

    def test_free_pan_supports_arbitrary_bounded_gestures(self):
        reader = Channel(dict(sample("C", 4), z=2))
        reader.observe([], "S1", height=1600)
        token = strict_action('{"acao":"DESLOCAR(37%,41%)"}', reader.actions)
        reader.move(reader.resolve(token))
        self.assertAlmostEqual(reader.x, 66.6)
        self.assertAlmostEqual(reader.y, 164)
        self.chan.observe([], "S1", height=1600)
        for choice, allowed in ((token, self.chan.actions), (FREE_PAN, reader.actions),
                                ("DESLOCAR(101%,1%)", reader.actions)):
            with self.assertRaises(ValueError):
                strict_action(json.dumps({"acao": choice}), allowed)

    def test_review_discrepancy_is_outside_initial_magnified_view(self):
        app = MenuApp("C2", "A")
        app.apply("review")
        public = observation(app, self.chan)
        self.assertNotIn("line:3", self.chan.visible)
        self.assertNotIn("Pudim", json.dumps(public, ensure_ascii=False))
        generic = Channel(sample("G", 7))
        page = observation(app, generic)
        self.assertIn("Pudim de leite", json.dumps(page, ensure_ascii=False))

    def test_occlusion_at_footer(self):
        row = sign("secret", "Oculto", 10, 735, 100, 20)
        row["visible_box"] = [10, 735, 100, 0]
        neutral = Channel(sample("C", 1))
        self.assertEqual(neutral.observe([row], "S1")["vista"], [])

    def test_paired_sampling_and_hash(self):
        for seed in range(32):
            p = sample("P", seed)
            c = sample("C", seed)
            self.assertEqual([p[k] for k in ("k", "n", "q")], [c[k] for k in ("k", "n", "q")])
            self.assertEqual(p, sample("P", seed))
            self.assertEqual(len(digest(p)), 64)
            for profile, low, high in (("P", 3, 5), ("P2", 1.5, 2.5), ("P6", 5.5, 7)):
                self.assertTrue(low <= sample(profile, seed)["z"] <= high)
            self.assertNotEqual(digest(p), digest(sample("P", seed, ("M7",))))


class RunTests(unittest.TestCase):
    def test_magnified_reference_sees_numeric_quantity_before_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            path, score = Trial("C2", "B", sample("R", 42, reference_zoom=7), folder).run()
            events = json.loads(path.read_text(encoding="utf8"))["events"]
            edit = next(e["passo"] for e in events if e["tipo"] == "item_alterado")
            quantities_seen = {e["dados"]["item_id"] for e in events if e["passo"] <= edit
                               and e["tipo"] == "elemento_visto"
                               and e["dados"]["campo"] == "quantidade"
                               and e["dados"]["criterio_visivel"]}
            self.assertEqual({6, 18, 20, 24}, quantities_seen)
            self.assertEqual((1, 1, 0), (score["S"], score["R_A"], score["O"]))

    def test_reference_results_in_both_interfaces(self):
        with tempfile.TemporaryDirectory() as folder:
            for task, counts in (("C1", (8, 7)), ("C2", (3, 3))):
                for version, expected in zip(("A", "B"), counts):
                    with self.subTest(task=task, version=version):
                        path, score = Trial(task, version, sample("R", 42), folder).run()
                        log = json.loads(Path(path).read_text(encoding="utf8"))
                        self.assertEqual((score["S"], score["R_A"], score["A"], score["O"]), (1, 1, expected, 0))
                        self.assertFalse(any(score["erros"].values()))
                        self.assertTrue(all(e["tipo"] in EVENTS and e["synthetic"] for e in log["events"]))
                        self.assertTrue(all(e["modelo_llm"] is None for e in log["events"]))
                        self.assertTrue(reference_count(task, version, 5) >= expected)
            self.assertFalse((Path(folder) / "auditoria_prompts_contextos").exists())

    def test_validation_guard_is_before_state_construction(self):
        for task in ("V1", "V2", "Treino", ""):
            with self.assertRaises(ValueError):
                calibration_only(task)
            with patch("agent.run.MenuApp", side_effect=AssertionError("state instantiated")):
                with self.assertRaises(ValueError):
                    Trial(task, "A", sample("R", 1), ".")
                with self.assertRaises(ValueError):
                    reference_count(task, "A", 1)


class AdapterTests(unittest.TestCase):
    def test_three_invalid_synthetic_responses_are_a_technical_failure(self):
        channel = Channel(sample("C", 1))
        projection = channel.observe([sign("entry", "Escolha", 0, 10, action="open:0")], "S1")
        fixture = {"modelVersion": "test-only", "candidates": [{"content": {
            "parts": [{"text": '{"acao":"TOCAR(999)"}'}]}}]}
        records, rejections = [], []
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fixture-key"}):
            policy = RemotePolicy("gemini", "test-only", 1)
        with patch("agent.policies.remote.urlopen", side_effect=lambda *a, **kw:
                   io.BytesIO(json.dumps(fixture).encode())) as mocked:
            with self.assertRaises(ProviderError):
                policy.choose("C1", projection, channel, lambda r: records.append(copy.deepcopy(r)),
                              lambda i, reason: rejections.append((i, reason)))
        self.assertEqual(mocked.call_count, 3)
        self.assertEqual([i for i, _ in rejections], [1, 2, 3])
        self.assertEqual(len(records), 6)
        self.assertTrue(all("fixture-key" not in str(r) for r in records))

    def test_response_grammar(self):
        offered = ["TOCAR(1)"]
        self.assertEqual(strict_action('{"acao":"TOCAR(1)"}', offered), offered[0])
        for bad in ('{"acao":"TOCAR(2)"}', '{"acao":"TOCAR(1)","acao":"TOCAR(1)"}',
                    '{"acao":5}', '{"acao":"TOCAR(1)","razão":"x"}', '[]', 'TOCAR(1)'):
            with self.assertRaises(ValueError):
                strict_action(bad, offered)

    def test_stateless_provider_envelopes_without_network(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fixture-key", "ANTHROPIC_API_KEY": "fixture-key"}):
            for name in ("gemini", "claude"):
                remote = RemotePolicy(name, "test-only", 42, 0.3)
                url, _, body = remote.request("conteúdo permitido")
                self.assertTrue(url.startswith("https://"))
                self.assertEqual(json.dumps(body, ensure_ascii=False).count("conteúdo permitido"), 1)
                self.assertNotIn("fixture-key", str(body))
                guard_request(body, name, "test-only", "conteúdo permitido", 0.3, 42)
                forged = dict(body, system="segmento que não passou pela janela")
                with self.assertRaises(ValueError):
                    guard_request(forged, name, "test-only", "conteúdo permitido", 0.3, 42)
                if name == "gemini":
                    self.assertEqual(body["generationConfig"]["seed"], 42)
                else:
                    self.assertNotIn("seed", body)

