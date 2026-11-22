"""Serve the manual photo demonstration outside the pilot console."""
import argparse
from collections import OrderedDict
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from app.catalog import MENU
from app.geometry import projected_layout
from app.model import MenuApp
from app.server import ASSETS, LOCK, Handler

HERE = Path(__file__).resolve().parent


class DemoHandler(Handler):
    sessions = OrderedDict()

    def do_GET(self):
        path = urlsplit(self.path).path
        assets = {"/": (HERE / "index.html", "text/html"),
                  "/demo.js": (HERE / "demo.js", "text/javascript"),
                  "/style.css": (ASSETS / "style.css", "text/css")}
        if path in assets:
            file, mime = assets[path]
            return self.reply(200, file.read_bytes(), mime + "; charset=utf-8")
        for item in MENU:
            if path == f"/fotos/{item:02d}.webp":
                image = HERE / "fotos" / f"{item:02d}.webp"
                if image.is_file():
                    return self.reply(200, image.read_bytes(), "image/webp")
                break
        return self.reply(404, {"error": "Recurso inexistente."})

    def do_POST(self):
        if self.headers.get("Origin") not in (None, "http://" + self.headers.get("Host", "")):
            return self.reply(403, {"error": "Origem inválida."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 2048:
                raise ValueError("Solicitação inválida.")
            args = json.loads(self.rfile.read(size))
            with LOCK:
                if self.path == "/api/start":
                    # C1 supplies the existing empty restaurant order. This route
                    # serves no task instruction, agent observation or study log.
                    app = MenuApp("C1", args["version"])
                    session = uuid4().hex
                    self.sessions[session] = app
                    if len(self.sessions) > 40:
                        self.sessions.popitem(last=False)
                elif self.path == "/api/action":
                    session = args["session"]
                    app = self.sessions[session]
                    if any(e["tipo"] == "acao_rejeitada" for e in app.apply(args["action"])):
                        raise ValueError("Ação indisponível nesta tela.")
                else:
                    return self.reply(404, {"error": "Recurso inexistente."})
                elements, height, _ = projected_layout(app)
                photo = f"/fotos/{app.item:02d}.webp" if app.scene == "S2" else None
                return self.reply(200, {"session": session, "scene": app.scene, "elements": elements,
                                        "height": height, "photo": photo})
        except (KeyError, TypeError, ValueError) as exc:
            return self.reply(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler) as server:
        print(f"http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
