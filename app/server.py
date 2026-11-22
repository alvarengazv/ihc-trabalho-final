"""Local teaching console. Run python -m app.server --port 8765."""
import argparse
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse
from uuid import uuid4

from agent.config import digest, sample
from agent.mechanisms import Channel
from agent.run import Trial, observation, reference_count
from verifier import evaluate
from .receipt import ReceiptHelp
from .catalog import TASKS
from .geometry import projected_layout
from .model import MenuApp

ASSETS = Path(__file__).with_name("static")
SESSIONS = OrderedDict()
LOCK = Lock()


class Console:
    def __init__(self, task, version, mode, seed, zoom):
        if mode not in ("manual", "R", "lens"):
            raise ValueError("Modo desconhecido.")
        if task in ("V1", "V2"):
            raise ValueError("A validação está reservada para o protocolo futuro.")
        if mode != "manual" and task not in ("C1", "C2"):
            raise ValueError("O ensaio instrumentado utiliza C1 ou C2.")
        if not 1 <= zoom <= 7:
            raise ValueError("Ampliação fora do intervalo.")
        self.mode, self.task, self.metrics, self.done = mode, task, None, False
        self.session = uuid4().hex
        self.step = 0
        self.expert = None
        self.receipt_help = None
        self.progress = False
        if mode == "R":
            self.params = sample("R", seed, reference_zoom=zoom)
            self.expert = Trial(task, version, self.params, Path("."))
            self.app, self.channel, self.events = self.expert.app, self.expert.channel, self.expert.events
            self.expert.emit("sessao_iniciada", parametros=self.params)
            self.expert.emit("tarefa_iniciada", estado_inicial=self.app.state(), pedido=self.app.state()["pedido"])
            self.baseline = reference_count(task, version, zoom)
        else:
            self.params = sample("P" if mode == "lens" else "C", seed)
            if mode == "manual":
                self.params["z"] = 1
            self.app = MenuApp(task, version)
            self.channel = Channel(self.params)
            self.events = []
            self.emit("sessao_iniciada", parametros=self.params)
            self.emit("tarefa_iniciada", estado_inicial=self.app.state(), pedido=self.app.state()["pedido"])
        self.refresh()

    def emit(self, kind, **data):
        if self.expert:
            self.expert.emit(kind, **data)
            return
        reg = self.region() if self.mode == "lens" else None
        self.events.append(dict(tipo=kind, dados=data, id_evento=f"{self.session}/{len(self.events)+1}",
            id_sessao=self.session, id_configuracao="P-manual" if self.mode=="lens" else "operador",
            id_tarefa=self.task, versao_interface=self.app.version, versao_mecanismos=self.params["version"],
            hash_configuracao=digest(self.params), modelo_llm=None, versao_llm=None,
            semente=self.params["seed"], passo=self.step, tela=self.app.scene,
            carimbo_tempo=datetime.now(timezone.utc).isoformat(), regiao_visivel=reg, synthetic=self.mode=="lens"))

    def region(self):
        x,y,w,h = self.channel.region
        return dict(x=x, y=y, z=self.channel.z, largura=w, altura=h)

    def refresh(self):
        if self.mode == "manual":
            self.public = None
            return
        if self.expert:
            # The live monitor must not advance FIFO or novelty before the real executor.
            self.public = observation(self.app, deepcopy(self.channel))
            return
        self.public = observation(self.app, self.channel)
        self.emit("observacao", observacao=self.public, elementos=list(self.channel.visible),
                  memoria=self.public["memoria"])
        for item in self.channel.seen_events:
            self.emit("elemento_visto", **item)

    def finish(self, reason):
        self.done = True
        log = {"events": self.events, "final_state": self.app.state(), "meta": {}}
        self.metrics = evaluate(log, reference_actions=self.baseline if self.expert else None)
        self.emit("tarefa_encerrada", resultado=self.metrics["resultado"],
                  categorias=[k for k, n in self.metrics["erros"].items() if n],
                  metricas=self.metrics)
        self.emit("sessao_encerrada")

    def act(self, choice):
        if self.done:
            raise ValueError("Esta execução foi encerrada.")
        if self.mode == "R":
            self.step += 1
            self.expert.step = self.step
            reason = self.expert.cycle()
            if reason:
                self.finish(reason)
            elif self.step >= self.params["L"]:
                self.emit("limite_atingido", numero_acoes=self.step)
                self.finish("limite_atingido")
            self.refresh()
            return
        if self.mode == "manual":
            if choice == "DESISTIR":
                self.step += 1
                self.emit("acao_executada", acao="DESISTIR", alvo=None, origem="pessoa")
                self.emit("desistencia")
                self.finish("desistencia")
                return
            changes = self.app.apply(choice)
            if changes and changes[0]["tipo"] == "acao_rejeitada":
                raise ValueError("Ação indisponível nesta tela.")
            self.step += 1
            self.emit("acao_executada", acao="TOCAR", alvo=choice, origem="pessoa")
            for change in changes:
                self.emit_change(change, "pessoa")
        else:
            if choice not in self.channel.actions:
                raise ValueError("O gesto precisa estar na observação corrente.")
            self.step += 1
            move = self.channel.actions[choice]
            origin = "pessoa"
            new = any(e["novo"] for e in self.channel.seen_events)
            if self.channel.impasse(self.progress or new):
                choice, origin = "TOCAR(Ajuda)", "acionador"
                move = self.channel.actions[choice]
            slip = self.channel.slip(move)
            if slip:
                move, point = slip
                origin = "deslize"
                self.emit("deslize_injetado", proposta=choice, executada="TOCAR", alvo=move[1], ponto_inicial=point)
            kind, arg = move
            before = self.region()
            action = {"pan":"DESLOCAR","touch":"TOCAR","quit":"DESISTIR","zoom":"AMPLIAR" if kind=="zoom" and arg>self.channel.z else "REDUZIR"}[kind]
            self.emit("acao_executada", acao=action, alvo=arg, origem=origin, gesto=choice)
            self.progress = False
            if kind == "quit":
                self.emit("desistencia")
                self.finish("desistencia")
                return
            if kind in ("pan","zoom"):
                self.channel.move(move)
                if kind=="pan":
                    self.emit("vista_deslocada", anterior=before, nova=self.region())
                else:
                    self.emit("zoom_alterado", anterior=before["z"], novo=self.channel.z)
            elif arg:
                for change in self.app.apply(arg):
                    self.emit_change(change, origin)
        if self.app.confirmed:
            self.finish("confirmado")
        elif self.mode == "lens" and self.step >= self.params["L"]:
            self.emit("limite_atingido", numero_acoes=self.step)
            self.finish("limite_atingido")
        if not self.done:
            self.refresh()

    def emit_change(self, change, origin):
        data = dict(change)
        kind = data.pop("tipo")
        if kind.startswith("ajuda_"):
            data["origem"] = origin
        self.emit(kind, **data)
        if kind == "tela_alterada":
            self.channel.scene_changed(self.app.scene == "S5")
        if kind.startswith("item_") or kind == "tela_alterada":
            self.progress = True

    def payload(self, cursor=0):
        elems, height, scroll = projected_layout(self.app, self.channel.y, self.channel.z)
        return dict(session=self.session, mode=self.mode, task=self.task, version=self.app.version,
                    instruction=TASKS[self.task], scene=self.app.scene, elements=elems, height=height,
                    scroll=scroll, region=self.region(), public=self.public, events=self.events[cursor:],
                    cursor=len(self.events), step=self.step, done=self.done, metrics=self.metrics)


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body, mime="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        files = {"/":("index.html","text/html"), "/console.js":("console.js","text/javascript"),
                 "/style.css":("style.css","text/css")}
        asset = files.get(urlparse(self.path).path)
        if not asset:
            return self.reply(404, {"error":"Recurso inexistente."})
        self.reply(200, (ASSETS/asset[0]).read_bytes(), asset[1]+"; charset=utf-8")

    def do_POST(self):
        if self.headers.get("Origin") not in (None, "http://"+self.headers.get("Host","")):
            return self.reply(403, {"error":"Origem inválida."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                raise ValueError("Solicitação inválida.")
            args = json.loads(self.rfile.read(length))
            with LOCK:
                if self.path == "/api/start":
                    c = Console(args["task"], args["version"], args["mode"], int(args["seed"]),
                                float(args.get("zoom", 1)))
                    SESSIONS[c.session] = c
                    if len(SESSIONS) > 40:
                        SESSIONS.popitem(last=False)
                    return self.reply(200, c.payload())
                if self.path == "/api/action":
                    c = SESSIONS[args["session"]]
                    if args["cursor"] != len(c.events):
                        raise ValueError("Esta ação já foi processada. Reinicie a sessão se necessário.")
                    c.act(args.get("action", ""))
                    return self.reply(200, c.payload(args["cursor"]))
                if self.path == "/api/receipt-help":
                    c = SESSIONS[args["session"]]
                    if not c.done or not c.app.confirmed:
                        raise ValueError("O comprovante está disponível após a confirmação.")
                    if c.receipt_help is None:
                        c.receipt_help = ReceiptHelp(c.app, c.events[0])
                    return self.reply(200, c.receipt_help.act(args["action"]))
            self.reply(404, {"error":"Recurso inexistente."})
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            self.reply(400, {"error":str(exc)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()

