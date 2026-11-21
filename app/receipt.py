"""Post-task, human-only receipt help. The experiment's final log stays closed."""
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from .model import LAYERS


class ReceiptHelp:
    def __init__(self, app, session_event):
        self.app = deepcopy(app)
        self.session = uuid4().hex
        self.common = {key: session_event[key] for key in (
            "id_tarefa", "versao_interface", "versao_mecanismos", "hash_configuracao")}
        self.history = []

    def act(self, action):
        if self.app.scene == "S4":
            allowed = {"help"}
        else:
            allowed = {"back", *("layer:" + layer for layer in LAYERS)}
        if action not in allowed:
            raise ValueError("Ação indisponível na consulta ao comprovante.")
        for event in self.app.apply(action):
            if event["tipo"].startswith("ajuda_"):
                event = dict(event)
                kind = event.pop("tipo")
                self.history.append({
                    **self.common, "id_evento": f"{self.session}/{len(self.history)+1}",
                    "id_sessao": self.session, "id_configuracao": "operador",
                    "modelo_llm": None, "versao_llm": None, "semente": None,
                    "passo": len(self.history)+1, "tela": self.app.scene,
                    "carimbo_tempo": datetime.now(timezone.utc).isoformat(),
                    "regiao_visivel": None, "synthetic": False, "tipo": kind,
                    "dados": {**event, "origem": "pessoa", "contexto": "consulta_apos_tarefa"},
                })
        if self.app.scene == "S4":
            return {"closed": True, "events": self.history}
        content = next(e["text"] for e in self.app.elements() if e["id"] == "help-text")
        return {"closed": False, "layer": self.app.layer, "layers": LAYERS,
                "content": content, "events": self.history}
