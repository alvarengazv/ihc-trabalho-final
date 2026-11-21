"""Serve a read-only view of actual Gemini pilot calls on localhost."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(__file__).with_suffix(".html")


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return None


def response_text(record):
    candidates = record.get("resposta", {}).get("candidates", [])
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def make_handler(run):
    audit = run / "auditoria_prompts_contextos"

    class Viewer(BaseHTTPRequestHandler):
        def send(self, payload, kind="application/json", status=200):
            body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", kind + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/":
                return self.send(PAGE.read_bytes(), "text/html")
            if url.path != "/api/registro":
                return self.send({"erro": "Endereço indisponível."}, status=404)
            sessions = sorted((p for p in audit.glob("*") if p.is_dir()),
                              key=lambda p: p.stat().st_mtime, reverse=True)
            scope = parse_qs(url.query)
            name = scope.get("sessao", [sessions[0].name if sessions else ""])[0]
            selected = next((p for p in sessions if p.name == name), None)
            result = {"sessoes": [p.name for p in sessions], "sessao": name, "passos": []}
            if selected:
                calls = sorted(selected.glob("*.json"), key=lambda p: p.name)
                result["passos"] = [p.stem for p in calls]
                attempt = scope.get("passo", [calls[-1].stem if calls else ""])[0]
                path = next((p for p in calls if p.stem == attempt), None)
                if path and (record := read_json(path)):
                    result.update(passo=attempt, registro=record, resposta=response_text(record))
                    log = read_json(run / "logs" / f"{name}.json")
                    if log:
                        result["desfecho"] = log["events"][-2]["dados"]["resultado"]
                        step = int(attempt.split("-")[0])
                        if record.get("modelo_retornado"):
                            result["executada"] = next((e["dados"] for e in log["events"]
                                                        if e["tipo"] == "acao_executada"
                                                        and e["passo"] == step), None)
            return self.send(result)

    return Viewer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--run", type=Path, default=ROOT / "runs" / "E3_Gemini")
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.run)) as server:
        print(f"http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
