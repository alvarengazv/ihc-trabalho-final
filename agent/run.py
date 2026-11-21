"""Run a single isolated calibration trial using the shared menu state machine."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4

from app.model import MenuApp
from app.geometry import projected_layout
from .config import CALIBRATION, calibration_only, digest, sample
from .mechanisms import Channel
from .policies.reference import Reference
from .policies.remote import ProviderError, RemotePolicy

EVENTS = frozenset("""
sessao_iniciada tarefa_iniciada observacao acao_proposta acao_rejeitada deslize_injetado
acao_executada vista_deslocada zoom_alterado tela_alterada elemento_visto opcao_selecionada
item_adicionado item_alterado item_removido ajuda_aberta ajuda_fechada pedido_confirmado
desistencia limite_atingido falha_tecnica tarefa_encerrada sessao_encerrada""".split())


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    temp.replace(path)


def observation(app, chan):
    elements, height, scroll = projected_layout(app, chan.y, chan.z)
    return chan.observe(elements, app.scene, height=height, scroll=scroll)


def reference_count(task, version, zoom):
    """Independent shadow traversal; never derive the denominator from the measured log."""
    calibration_only(task)
    app = MenuApp(task, version)
    chan = Channel(sample("R", 0, reference_zoom=zoom))
    rule = Reference(task, version)
    for count in range(1, 1001):
        observation(app, chan)
        _, move = rule.choose(chan)
        if move[0] == "touch":
            changes = app.apply(move[1])
            if any(e["tipo"] == "acao_rejeitada" for e in changes):
                raise ValueError("Invalid expert transition")
            if any(e["tipo"] == "tela_alterada" for e in changes):
                chan.scene_changed()
        else:
            chan.move(move)
        if app.confirmed:
            return count
    raise ValueError("Expert reference did not terminate")


class Trial:
    def __init__(self, task, version, params, out, policy=None):
        calibration_only(task)
        self.app = MenuApp(task, version)
        self.task, self.params, self.out, self.policy = task, params, Path(out), policy
        self.channel = Channel(params)
        self.session = f"{task}-{version}-{params['profile']}-{params['seed']}-{uuid4().hex[:12]}"
        self.events = []
        self.step = 0
        self.hash = digest(params)
        self.model_version = None
        self.rule = Reference(task, version) if params["profile"] == "R" else None
        self.progress = False

    def region(self):
        x, y, w, h = self.channel.region
        return {"x": x, "y": y, "z": self.channel.z, "largura": w, "altura": h}

    def emit(self, kind, **data):
        if kind not in EVENTS:
            raise ValueError(f"Unknown event: {kind}")
        self.events.append({
            "id_evento": f"{self.session}/{len(self.events) + 1}", "id_sessao": self.session,
            "id_configuracao": self.params["profile"], "id_tarefa": self.task,
            "versao_interface": self.app.version, "versao_mecanismos": self.params["version"],
            "hash_configuracao": self.hash, "modelo_llm": self.policy.model if self.policy else None,
            "versao_llm": self.model_version, "semente": self.params["seed"], "passo": self.step,
            "carimbo_tempo": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "tela": self.app.scene, "regiao_visivel": self.region(), "synthetic": True,
            "temperatura": self.policy.temperature if self.policy else None,
            "tipo": kind, "dados": data,
        })

    def audit(self, record):
        path = self.out / "auditoria_prompts_contextos" / self.session
        save(path / f"{self.step:03d}-{record['tentativa']}.json", record)

    def rejected(self, attempt, reason):
        self.emit("acao_rejeitada", tentativa=attempt, motivo=reason)

    def cycle(self):
        chan = self.channel
        public = observation(self.app, chan)
        self.emit("observacao", observacao=public, elementos=list(chan.visible),
                  memoria=public["memoria"], estado_interface=self.app.state(), rolagem=chan.scroll)
        new = any(e["novo"] for e in chan.seen_events)
        for item in chan.seen_events:
            self.emit("elemento_visto", **item)
        forced = self.step > 1 and chan.impasse(self.progress or new)
        latency = None
        if forced:
            label, origin = "TOCAR(Ajuda)", "acionador"
            move = chan.actions[label]
        elif self.rule:
            label, move = self.rule.choose(chan)
            origin = "R"
        else:
            label, self.model_version, latency = self.policy.choose(
                self.task, public, chan, self.audit, self.rejected)
            move = chan.resolve(label)
            origin = "LLM"
            self.emit("acao_proposta", acao=label, alvo=move[1], latencia_ms=latency)
        slip = chan.slip(move)
        if slip:
            move, point = slip
            self.emit("deslize_injetado", proposta=label, executada="TOCAR", alvo=move[1], ponto_inicial=point)
            origin = "deslize"
        kind, value = move
        self.progress = False
        name = {"touch": "TOCAR", "pan": "DESLOCAR", "quit": "DESISTIR",
                "zoom": "AMPLIAR" if kind == "zoom" and value > chan.z else "REDUZIR"}[kind]
        if label == "VOLTAR" and origin != "deslize":
            name = "VOLTAR"
        before = self.region()
        changes = []
        if kind == "touch" and value:
            changes = self.app.apply(value)
            if any(e["tipo"] == "acao_rejeitada" for e in changes):
                raise ValueError("Channel and interaction gate disagree")
        elif kind in ("pan", "zoom"):
            chan.move(move)
        self.emit("acao_executada", acao=name, alvo=value, origem=origin, gesto=label)
        if kind == "pan":
            self.emit("vista_deslocada", anterior=before, nova=self.region())
        elif kind == "zoom":
            self.emit("zoom_alterado", anterior=before["z"], novo=chan.z)
        elif kind == "quit":
            self.emit("desistencia")
            return "desistencia"
        for event in changes:
            event = dict(event)
            typ = event.pop("tipo")
            if typ.startswith("ajuda_"):
                event["origem"] = origin
            self.emit(typ, **event)
            if typ == "tela_alterada":
                chan.scene_changed(self.app.scene == "S5")
            if typ in ("item_adicionado", "item_alterado", "item_removido", "tela_alterada"):
                self.progress = True
        return "confirmado" if self.app.confirmed else None

    def run(self):
        from verifier import evaluate
        baseline = reference_count(self.task, self.app.version, self.params["z"])
        self.emit("sessao_iniciada", parametros=self.params)
        self.emit("tarefa_iniciada", estado_inicial=self.app.state(), pedido=self.app.state()["pedido"])
        reason = None
        for self.step in range(1, self.params["L"] + 1):
            try:
                reason = self.cycle()
            except (ProviderError, ValueError) as exc:
                self.emit("falha_tecnica", classe=type(exc).__name__, mensagem=str(exc))
                reason = "falha_tecnica"
            if reason:
                break
        if reason is None:
            self.emit("limite_atingido", numero_acoes=self.params["L"])
        log = {"meta": {"reference_actions": baseline, "parametros": self.params, "n": self.params["n"],
                         "executor": "R" if self.rule else self.policy.provider},
               "events": self.events, "final_state": self.app.state()}
        metrics = evaluate(log, reference_actions=baseline)
        outcome = ("falha_tecnica" if metrics["S"] is None else
                   "interrupcao" if metrics["interrupcao"] else
                   "sucesso" if metrics["S"] else "erro")
        self.emit("tarefa_encerrada", resultado=outcome,
                  categorias=[key for key, value in metrics["erros"].items() if value], metricas=metrics)
        self.emit("sessao_encerrada")
        path = self.out / "logs" / (self.session + ".json")
        save(path, log)
        return path, metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=CALIBRATION, required=True)
    parser.add_argument("--version", choices=("A", "B"), required=True)
    parser.add_argument("--config", choices=("P", "P2", "P6", "C", "G", "R"), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--provider", choices=("gemini", "claude"), default="gemini")
    parser.add_argument("--model", help="Exact provider model ID, or GEMINI_MODEL / ANTHROPIC_MODEL")
    parser.add_argument("--temperature", type=float, help="Omit to use the provider default")
    parser.add_argument("--disable", action="append", choices=[f"M{i}" for i in range(1, 8)], default=[])
    parser.add_argument("--reference-zoom", type=float, help="Initial aperture for an expert R run")
    parser.add_argument("--out", type=Path, default=Path("deliverables/E3_Pacote_Piloto"))
    args = parser.parse_args()
    params = sample(args.config, args.seed, args.disable, args.reference_zoom)
    policy = None
    if args.config != "R":
        key = "GEMINI_MODEL" if args.provider == "gemini" else "ANTHROPIC_MODEL"
        model = args.model or os.getenv(key)
        if not model:
            parser.error(f"Set --model or {key} to the exact available model identifier.")
        try:
            policy = RemotePolicy(args.provider, model, args.seed, args.temperature)
        except ProviderError as exc:
            parser.error(str(exc))
    path, metrics = Trial(args.task, args.version, params, args.out, policy).run()
    print(path)
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    main()

