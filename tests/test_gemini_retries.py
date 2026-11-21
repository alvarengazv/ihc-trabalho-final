"""Offline transport fixtures for the Gemini batch runner."""
from collections import deque
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from agent.config import sample
from agent.mechanisms import Channel
from agent.policies.remote import ProviderError
from agent.run import Trial
from tools.run_gemini_pilot import PacedGemini


def error(status, delay=None, quota=None):
    details = [{"violations": [{"quotaId": quota}]}] if quota else []
    body = {"error": {"status": "UNAVAILABLE", "details": details}}
    headers = {"Retry-After": str(delay)} if delay is not None else {}
    return HTTPError("https://example.invalid", status, "test", headers,
                     io.BytesIO(json.dumps(body).encode()))


def model_response(action):
    body = {"modelVersion": "test-only", "candidates": [{"content": {
        "parts": [{"text": json.dumps({"acao": action})}]}}]}
    return io.BytesIO(json.dumps(body).encode())


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-only"})
@patch("tools.run_gemini_pilot.time.sleep")
@patch("tools.run_gemini_pilot.random.uniform", return_value=0)
class GeminiRetryTests(unittest.TestCase):
    def test_503_retries_in_same_trial_step(self, _jitter, sleep):
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            policy = PacedGemini("test-only", 42, None, 10)
            trial = Trial("C2", "A", sample("C", 42), folder, policy)
            targets = deque(("review", error(503, delay=12), "inc:3", "confirm"))

            def send(*args, **kwargs):
                target = targets.popleft()
                if isinstance(target, HTTPError):
                    raise target
                action = next(label for label, move in trial.channel.actions.items()
                              if move == ("touch", target))
                return model_response(action)

            with patch("agent.policies.remote.urlopen", side_effect=send) as remote:
                log_path, metrics = trial.run()
            self.assertEqual(remote.call_count, 4)
            self.assertTrue(any(call.args[0] >= 11.9 for call in sleep.call_args_list))
            self.assertEqual((1, 3, 0), (metrics["S"], metrics["A"], metrics["propostas_rejeitadas"]))
            audit = Path(folder) / "auditoria_prompts_contextos" / log_path.stem
            failed = json.loads((audit / "002-1.json").read_text(encoding="utf8"))
            recovered = json.loads((audit / "002-2.json").read_text(encoding="utf8"))
            self.assertEqual(failed["status_http"], 503)
            self.assertGreaterEqual(failed["nova_tentativa_em_s"], 11.9)
            self.assertEqual(failed["requisicao"], recovered["requisicao"])
            self.assertEqual(recovered["modelo_retornado"], "test-only")

    def test_transport_and_format_budgets(self, _jitter, _sleep):
        policy = PacedGemini("test-only", 42, None, 10, retries=2)
        channel = Channel(sample("C", 42))
        projection = channel.observe([], "S1")
        failures = [error(503), model_response("bad"), URLError(TimeoutError()),
                    model_response("bad"), model_response("bad")]
        audited = {}
        rejected = []
        with patch("agent.policies.remote.urlopen", side_effect=failures) as remote, redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ProviderError, "Invalid response after two retries"):
                policy.choose("C1", projection, channel,
                              lambda item: audited.update({item["tentativa"]: item}),
                              lambda attempt, reason: rejected.append(attempt))
        self.assertEqual(remote.call_count, 5)
        self.assertEqual(sorted(audited), [1, 2, 3, 4, 5])
        self.assertEqual(rejected, [2, 4, 5])

    def test_auth_daily_quota_and_exhaustion(self, _jitter, _sleep):
        channel = Channel(sample("C", 42))
        projection = channel.observe([], "S1")
        for failures in (
                [error(401)], [error(429, quota="GenerateRequestsPerDayPerProject")],
                [error(503, delay=500)], [error(503), error(503)]):
            policy = PacedGemini("test-only", 42, None, 10, retries=1)
            audited = {}
            with self.subTest(failures=failures), redirect_stdout(io.StringIO()):
                with patch("agent.policies.remote.urlopen", side_effect=failures) as remote:
                    with self.assertRaises(ProviderError):
                        policy.choose("C1", projection, channel,
                                      lambda item: audited.update({item["tentativa"]: item}),
                                      lambda *_: self.fail("Transport error is not an invalid action"))
                self.assertEqual(remote.call_count, len(failures))
                self.assertNotIn("nova_tentativa_em_s", audited[max(audited)])
