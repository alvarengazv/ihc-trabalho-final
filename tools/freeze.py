"""Verify the exact instrument snapshot associated with a calibration package."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "deliverables" / "E3_Pacote_Piloto" / "manifesto_instrumento.json"


def freeze_manifest():
    paths = []
    for folder in ("app", "agent", "verifier", "design"):
        paths.extend(p for p in (ROOT / folder).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts
                     and p.suffix in {".py", ".js", ".css", ".html", ".json", ".tex", ".pdf"})
    files = {}
    for path in sorted(paths):
        contents = path.read_bytes()
        if path.suffix != ".pdf":
            contents = contents.replace(b"\r\n", b"\n")
        files[path.relative_to(ROOT).as_posix()] = hashlib.sha256(contents).hexdigest()
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, ensure_ascii=False,
                                       separators=(",", ":")).encode()).hexdigest()
    return {"algoritmo": "SHA-256 (texto com quebras LF, binários preservados)", "hash_instrumento": digest, "arquivos": files,
            "uso": "Instantâneo do instrumento de calibração. A validação futura requer protocolo próprio.",
            "tarefas_calibracao": ["C1", "C2"], "tarefas_reservadas": ["V1", "V2"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT)
    saved = json.loads(parser.parse_args().manifest.read_text(encoding="utf8"))
    current = freeze_manifest()
    if saved != current:
        differences = [k for k in sorted(saved["arquivos"].keys() | current["arquivos"].keys())
                       if saved["arquivos"].get(k) != current["arquivos"].get(k)]
        raise SystemExit("Instrument snapshot differs: " + ", ".join(differences))
    print(current["hash_instrumento"])

