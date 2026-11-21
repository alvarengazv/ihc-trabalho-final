import json
import os
import re
import time
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.catalog import TASKS
from agent.config import calibration_only
from agent.mechanisms.channel import FREE_PAN, free_pan_offset

FORBIDDEN = re.compile(
    r"\b(?:HTA|CTT|GOMS|KLM|MoLIC|DOM|disabled|ground[ _-]?truth|"
    r"id_configuracao|item_id|id_evento|id_tarefa|hash_configuracao|"
    r"pedido_confirmado|S[0-5]|V[12])\b|<(?:html|div|button)\b|"
    r"\b(?:open|line|category|price|option):\d+|critério de sucesso", re.I)
FUNCTION = ("Escolha uma única ação disponível para realizar a tarefa. Leia os trechos "
            "visíveis e as lembranças fornecidas. Os números em TOCAR indicam a posição "
            "do elemento na lista visível atual. Responda com um objeto JSON com a chave acao.")
SCHEMA = {"type": "object", "properties": {"acao": {"type": "string"}},
          "required": ["acao"], "additionalProperties": False}


@lru_cache(maxsize=1)
def training_example():
    from agent.config import sample
    from agent.mechanisms import Channel
    from app.geometry import projected_layout
    from app.model import MenuApp
    snack = MenuApp("Treino", "A")
    reader = Channel(sample("C", 0))
    elements, height, scroll = projected_layout(snack)
    frame = reader.observe(elements, snack.scene, height=height, scroll=scroll)
    sign = next(sign for sign in frame["vista"] if sign.get("texto") == "Pão de queijo")
    return {"tarefa": TASKS["Treino"], "trecho": sign, "resposta": {"acao": sign["gesto"]}}


def make_prompt(task, projection, channel):
    calibration_only(task)
    channel.check_projection(projection)
    data = {"orientacao": FUNCTION, "exemplo_de_treino": training_example(), "tarefa": TASKS[task],
            "observacao": projection}
    if FREE_PAN in projection["acoes"]:
        data["orientacao"] += (" No gesto livre, substitua dx e dy por percentuais inteiros "
                              "da largura e da altura da vista, de −100 a 100, "
                              "com pelo menos um deslocamento diferente de zero.")
    prompt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if FORBIDDEN.search(prompt):
        raise ValueError("Forbidden structure or analyst-only token in outgoing context")
    return prompt


def strict_action(raw, offered):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate action key")
            result[key] = value
        return result
    body = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(body, dict) or set(body) != {"acao"} or type(body["acao"]) is not str:
        raise ValueError("Expected exactly one string-valued action")
    action = body["acao"]
    if action == FREE_PAN or (action not in offered and not (
            FREE_PAN in offered and free_pan_offset(action) is not None)):
        raise ValueError("Action absent from current channel")
    return body["acao"]


class ProviderError(RuntimeError):
    pass


def guard_request(body, provider, model, prompt, temperature, seed):
    """Verify the final wire envelope, including non-text provider fields."""
    if provider == "gemini":
        parameters = {"responseMimeType": "application/json", "responseJsonSchema": SCHEMA, "seed": seed}
        if temperature is not None:
            parameters["temperature"] = temperature
        valid = (set(body) == {"contents", "generationConfig"} and
                 body["contents"] == [{"role": "user", "parts": [{"text": prompt}]}] and
                 body["generationConfig"] == parameters)
    else:
        valid = (body.get("model") == model and body.get("max_tokens") == 256 and
                 body.get("output_config") == {"format": {"type": "json_schema", "schema": SCHEMA}} and
                 body.get("messages") == [{"role": "user", "content": prompt}] and
                 set(body) == {"model", "max_tokens", "output_config", "messages"} |
                 ({"temperature"} if temperature is not None else set()) and
                 body.get("temperature") == temperature)
    if not valid:
        raise ValueError("Unexpected field or unverified context in provider request")


class RemotePolicy:
    def __init__(self, provider, model, seed, temperature=None):
        if provider not in ("gemini", "claude"):
            raise ValueError("Unknown provider")
        self.provider, self.model, self.seed = provider, model, seed
        self.temperature = temperature
        env_name = "GEMINI_API_KEY" if provider == "gemini" else "ANTHROPIC_API_KEY"
        self.key = os.getenv(env_name)
        if not self.key:
            raise ProviderError(f"Missing {env_name}")

    def request(self, prompt):
        if self.provider == "gemini":
            url = "https://generativelanguage.googleapis.com/v1beta/models/" + quote(self.model, safe="") + ":generateContent"
            config = {"responseMimeType": "application/json", "responseJsonSchema": SCHEMA, "seed": self.seed}
            if self.temperature is not None:
                config["temperature"] = self.temperature
            body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": config}
            headers = {"x-goog-api-key": self.key}
        else:
            url = "https://api.anthropic.com/v1/messages"
            body = {"model": self.model, "max_tokens": 256, "messages": [{"role": "user", "content": prompt}],
                    "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}}}
            if self.temperature is not None:
                body["temperature"] = self.temperature
            headers = {"x-api-key": self.key, "anthropic-version": "2023-06-01"}
        return url, headers, body

    def choose(self, task, projection, channel, audit, rejected):
        for attempt in range(1, 4):
            # Construct the sole outbound text at the transmission boundary,
            # anew for each request (no previous turns or provider session).
            prompt = make_prompt(task, projection, channel)
            url, headers, body = self.request(prompt)
            guard_request(body, self.provider, self.model, prompt, self.temperature, self.seed)
            record = {"tentativa": attempt, "provedor": self.provider, "modelo_solicitado": self.model,
                      "temperatura": self.temperature, "semente_api": self.seed if self.provider == "gemini" else None,
                      "url": url, "requisicao": body, "observacao": projection}
            audit(record)
            started = time.monotonic()
            request = Request(url, json.dumps(body, ensure_ascii=False).encode("utf8"),
                              {**headers, "Content-Type": "application/json"}, method="POST")
            try:
                with urlopen(request, timeout=80) as response:
                    data = json.load(response)
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                record.update(latencia_ms=round(1000 * (time.monotonic() - started)),
                              falha=type(exc).__name__, status_http=getattr(exc, "code", None))
                audit(record)
                raise ProviderError(f"API failure ({record['falha']}, HTTP {record['status_http']})") from exc
            record.update(latencia_ms=round(1000 * (time.monotonic() - started)), resposta=data)
            try:
                if self.provider == "gemini":
                    candidate = data["candidates"][0]
                    raw = "".join(part["text"] for part in candidate["content"]["parts"]
                                  if "text" in part and not part.get("thought"))
                    version = data["modelVersion"]
                else:
                    raw = "".join(block["text"] for block in data["content"] if block["type"] == "text")
                    version = data["model"]
                action = strict_action(raw, channel.actions)
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                record["rejeicao"] = type(exc).__name__
                audit(record)
                rejected(attempt, str(exc))
                continue
            record["modelo_retornado"] = version
            audit(record)
            return action, version, record["latencia_ms"]
        raise ProviderError("Invalid response after two retries")

