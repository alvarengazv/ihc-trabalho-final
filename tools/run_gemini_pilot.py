"""Run the paired Gemini calibration matrix with one seed and model."""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
import os
from pathlib import Path
import random
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.config import CALIBRATION, sample
from agent.policies.remote import ProviderError, RemotePolicy
from agent.run import Trial, save
from tools.freeze import freeze_manifest

DEFAULT_MODEL = "gemini-3.5-flash-lite"
PROFILES = ("C", "P", "P2", "P6")
KEY_FILE = ROOT / ".env.gemini-key"
TRANSIENT_HTTP = {408, 429, 500, 502, 503, 504}
MAX_RETRY_WAIT = 120


def error_codes(error):
    try:
        payload = json.loads(error.read(8192))
    except (ValueError, OSError):
        payload = {}
    finally:
        error.close()
    body = payload.get("error", {}) if isinstance(payload, dict) else {}
    if not isinstance(body, dict):
        body = {}
    details = [d for d in body.get("details", []) if isinstance(d, dict)]
    codes = [body.get("status", ""), *(d.get("reason", "") for d in details)]
    diagnostic = {"codes": list(dict.fromkeys(s for s in codes
                                              if isinstance(s, str) and re.fullmatch(r"[A-Z_]{2,80}", s)))}
    for detail in details:
        metrics = [item.get("quotaId", "") for item in detail.get("violations", [])
                   if isinstance(item, dict)]
        if metrics:
            diagnostic["quota_ids"] = [s for s in metrics if isinstance(s, str)
                                       and re.fullmatch(r"[A-Za-z0-9_]{2,120}", s)]
        delay = detail.get("retryDelay", "")
        if isinstance(delay, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?s", delay):
            diagnostic["retry_delay"] = delay
    return diagnostic


def retry_after(headers):
    value = headers.get("Retry-After", "").strip() if headers else ""
    if value.isascii() and value.isdecimal():
        return int(value)
    if value:
        try:
            timestamp = parsedate_to_datetime(value)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return max(0, (timestamp - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            pass
    return 0


def retry_wait(error, details, retries, minimum):
    """Return a bounded delay or None for errors that should end the step."""
    if isinstance(error, HTTPError):
        if error.code not in TRANSIENT_HTTP:
            return None
        if error.code == 429 and any("perday" in metric.lower() or "daily" in metric.lower()
                                     for metric in details.get("quota_ids", [])):
            return None
        if error.code == 429:
            minimum = max(30, minimum)
        advised = max(retry_after(error.headers), float(details.get("retry_delay", "0s")[:-1]))
    else:
        reason = error.reason if isinstance(error, URLError) else error
        if not isinstance(reason, (TimeoutError, ConnectionError)):
            return None
        advised = 0
    if advised > MAX_RETRY_WAIT:
        return None
    backoff = minimum * 2 ** retries
    return min(MAX_RETRY_WAIT, max(advised, backoff) + random.uniform(0, 1))


class PacedGemini(RemotePolicy):
    """Pace the transport outside the policy inputs and action stream."""

    def __init__(self, model, seed, temperature, rpm, retries=4, retry_base=2):
        super().__init__("gemini", model, seed, temperature)
        self.interval = 60 / rpm
        self.next_request = 0
        self.retries = retries
        self.retry_base = retry_base

    def request(self, prompt):
        wait = self.next_request - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.next_request = time.monotonic() + self.interval
        return super().request(prompt)

    def choose(self, task, projection, channel, audit, rejected):
        # Each invocation is one trial step. Keep the provider's format-rejection
        # budget across HTTP retries and number all wire attempts in one sequence.
        offset = invalid = 0
        last = None

        def record_attempt(record):
            nonlocal last
            last = {**record, "tentativa": offset + record["tentativa"]}
            audit(last)

        def reject_attempt(attempt, reason):
            nonlocal invalid
            rejected(offset + attempt, reason)
            invalid += 1
            if invalid >= 3:
                raise ProviderError("Invalid response after two retries")

        for retries in range(self.retries + 1):
            try:
                return super().choose(task, projection, channel, record_attempt, reject_attempt)
            except ProviderError as exc:
                error = exc.__cause__
                if error is None or last is None:
                    raise
                details = error_codes(error) if isinstance(error, HTTPError) else {}
                last["diagnostico"] = details
                delay = retry_wait(error, details, retries, self.retry_base) if retries < self.retries else None
                if delay is None:
                    audit(last)
                    raise ProviderError(f"{exc} · {json.dumps(details)}") from exc
                offset = last["tentativa"]
                self.next_request = max(self.next_request, time.monotonic() + delay)
                wait = max(0, self.next_request - time.monotonic())
                last["nova_tentativa_em_s"] = round(wait, 2)
                audit(last)
                code = f"HTTP {error.code}" if isinstance(error, HTTPError) else type(error).__name__
                print(f"{code} · nova tentativa em {wait:.1f}s ({retries + 1}/{self.retries}).",
                      flush=True)


def load_key():
    if os.getenv("GEMINI_API_KEY"):
        return
    if KEY_FILE.is_file():
        key = KEY_FILE.read_text(encoding="utf-8-sig").strip()
        if key and not key.startswith("GEMINI_API_KEY=") and not any(c.isspace() for c in key):
            os.environ["GEMINI_API_KEY"] = key
            return
        raise ProviderError("Salve apenas o valor da chave em .env.gemini-key.")
    raise ProviderError("Configure GEMINI_API_KEY ou o arquivo local .env.gemini-key.")


def check_key(model):
    """Check the selected model's metadata without a generation request."""
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + quote(model, safe="")
    request = Request(url, headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    try:
        with urlopen(request, timeout=20) as response:
            metadata = json.load(response)
    except HTTPError as exc:
        print(f"Gemini HTTP {exc.code} {json.dumps(error_codes(exc))}", file=sys.stderr)
        return 1
    except (URLError, OSError, ValueError) as exc:
        print(f"Falha no diagnóstico Gemini ({type(exc).__name__}).", file=sys.stderr)
        return 1
    if "generateContent" not in metadata.get("supportedGenerationMethods", []):
        print("O modelo não lista suporte a generateContent.", file=sys.stderr)
        return 1
    print(f"Gemini aceitou a chave para consultar {model}, com suporte a generateContent.")
    return 0


def completed_conditions(folder, manifest):
    completed = {}
    for path in sorted((folder / "logs").glob("*.json")):
        log = json.loads(path.read_text(encoding="utf8"))
        if log["meta"]["executor"] != "gemini":
            continue
        start = log["events"][0]
        if (start["modelo_llm"], start["semente"], start["temperatura"]) != (
                manifest["modelo"], manifest["semente"], manifest["temperatura"]):
            raise ValueError(f"A execução {path.name} usa outra configuração.")
        result = next(e for e in log["events"] if e["tipo"] == "tarefa_encerrada")
        if result["dados"]["resultado"] == "falha_tecnica":
            continue
        condition = (start["id_configuracao"], start["id_tarefa"], start["versao_interface"])
        completed[condition] = path
    return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.getenv("GEMINI_MODEL") or DEFAULT_MODEL)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--rpm", type=int, default=10, help="Max requests per minute for this runner")
    parser.add_argument("--retries", type=int, choices=range(7), default=4,
                        help="Transport retries per step (default: 4)")
    parser.add_argument("--retry-base", type=float, default=2,
                        help="Initial exponential backoff in seconds (default: 2)")
    parser.add_argument("--out", type=Path, default=ROOT / "runs" / "E3_Gemini")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--plan", action="store_true", help="Print the planned matrix without calling the API")
    modes.add_argument("--check-key", action="store_true", help="Check Gemini model metadata without generation")
    args = parser.parse_args()
    if args.temperature is not None and (not math.isfinite(args.temperature)
                                         or not 0 <= args.temperature <= 2):
        parser.error("Use uma temperatura finita entre 0 e 2.")
    if args.rpm < 1:
        parser.error("Use --rpm maior ou igual a 1.")
    if not 1 <= args.retry_base <= MAX_RETRY_WAIT:
        parser.error(f"Use --retry-base entre 1 e {MAX_RETRY_WAIT} segundos.")

    conditions = [(profile, task, version) for profile in PROFILES
                  for task in CALIBRATION for version in ("A", "B")]
    manifest = {
        "provedor": "gemini", "modelo": args.model, "semente": args.seed,
        "temperatura": args.temperature,
        "hash_instrumento": freeze_manifest()["hash_instrumento"],
        "condicoes": [list(c) for c in conditions],
    }
    if args.plan:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    try:
        load_key()
        policy = PacedGemini(args.model, args.seed, args.temperature, args.rpm, args.retries, args.retry_base)
    except ProviderError as exc:
        parser.error(str(exc))
    if args.check_key:
        return check_key(args.model)

    protocol = args.out / "protocolo_gemini.json"
    if protocol.exists():
        if json.loads(protocol.read_text(encoding="utf8")) != manifest:
            parser.error("O diretório contém outro protocolo. Use --out para separar os resultados.")
    else:
        if next((args.out / "logs").glob("*.json"), None):
            parser.error("O diretório contém registros sem protocolo correspondente.")
        save(protocol, manifest)

    try:
        completed = completed_conditions(args.out, manifest)
    except ValueError as exc:
        parser.error(str(exc))
    for index, (profile, task, version) in enumerate(conditions, 1):
        label = f"[{index}/{len(conditions)}] {profile} {task}/{version}"
        if (profile, task, version) in completed:
            print(f"{label} já registrada.", flush=True)
            continue
        print(f"{label} em execução.", flush=True)
        log, metrics = Trial(task, version, sample(profile, args.seed), args.out, policy).run()
        print(f"{label} {metrics['resultado']}, S={metrics['S']}, A={metrics['A']} · {log.name}",
              flush=True)
        if metrics["resultado"] == "falha_tecnica":
            content = json.loads(log.read_text(encoding="utf8"))
            failure = next(e["dados"]["mensagem"] for e in content["events"]
                           if e["tipo"] == "falha_tecnica")
            print(f"{failure}. A execução e a auditoria foram preservadas.", file=sys.stderr)
            return 1
    print(f"Piloto Gemini completo. Registros em {args.out.resolve()}.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
