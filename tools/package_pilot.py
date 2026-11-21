"""Verify all E3 logs, write the measured summary, then build its ZIP."""
from pathlib import Path
import json
import sys
import zipfile
from collections import Counter
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verifier import evaluate
from agent.run import EVENTS
from freeze import freeze_manifest

folder = ROOT / "deliverables" / "E3_Pacote_Piloto"
summary = []
groups = {}
for path in sorted((folder / "logs").glob("*.json")):
    log = json.loads(path.read_text(encoding="utf8"))
    events = log["events"]
    head = events[0]
    key = head["id_tarefa"], head["versao_interface"], head["id_configuracao"]
    assert key[0] in ("C1", "C2"), path
    assert all(e["tipo"] in EVENTS and e["synthetic"] is True for e in events), path
    assert len(set(e["id_evento"] for e in events)) == len(events), path
    fields = set("id_evento id_sessao id_configuracao id_tarefa versao_interface "
                 "versao_mecanismos hash_configuracao modelo_llm versao_llm semente "
                 "passo carimbo_tempo tela regiao_visivel synthetic tipo dados".split())
    assert all(fields <= e.keys() and e["id_sessao"] == head["id_sessao"] for e in events), path
    assert head["tipo"] == "sessao_iniciada" and events[-1]["tipo"] == "sessao_encerrada", path
    result = evaluate(log)
    stored = next(e["dados"]["metricas"] for e in events if e["tipo"] == "tarefa_encerrada")
    assert result == stored, f"Recorded and recomputed metrics differ: {path.name}"
    if key[2] == "R":
        assert result["S"] == 1 and result["R_A"] == 1 and not any(result["erros"].values()), path
    groups.setdefault(key, []).append(result)
    ops = Counter(e["dados"]["acao"] for e in events if e["tipo"] == "acao_executada")
    summary.append((key, path.name, result, ops))

def fmt(value):
    return "—" if value is None else f"{value:.3g}".replace(".", ",")

lines = ["# Piloto de instrumentação", "",
         "Resultados sintéticos recalculados sobre cada registro de execução. A referência é um percurso independente de R na mesma versão e ampliação inicial. Cada linha representa uma sessão.", "",
         "| Tarefa | Versão | Executor | S | A | Toques | Desloc. | Nref | R_A | D | V | O | Erros E1–E6 | U |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
for (task, version, executor), name, m, ops in summary:
    values = [task, version, executor, fmt(m["S"]), str(m["A"]), str(ops["TOCAR"]),
              str(ops["DESLOCAR"]), str(m["N_ref"]), fmt(m["R_A"]), fmt(m["D"]),
              fmt(m["V"]), fmt(m["O"]), " / ".join(str(v) for v in m["erros"].values()), str(m["U"])]
    lines.append("| " + " | ".join(values) + " |")
lines.extend(["", "## Taxas de erro por oportunidade", "",
              "Cada célula mostra erros/oportunidades (taxa). O travessão identifica taxa indefinida. As oportunidades de E1 e E3 contam as escolhas efetivamente registradas. As de E5 contam as discrepâncias introduzidas no protocolo.", "",
              "| Tarefa / versão / executor | E1 | E2 | E3 | E4 | E5 | E6 |",
              "|---|---|---|---|---|---|---|"])
for key, name, m, ops in summary:
    cells = [f"{m['erros'][k]}/{fmt(m['oportunidades'][k])} ({fmt(m['Re'][k])})"
             for k in m["erros"]]
    lines.append("| " + " | ".join([" / ".join(key), *cells]) + " |")
lines.extend(["", "## Agregação por condição", "",
              "| Tarefa / versão / executor | Iniciadas | S médio entre execuções sem falha técnica | Mediana de A | Proporção com ajuda por camada (1 / 2 / 3) |",
              "|---|---:|---:|---:|---|"])
for key, metrics in sorted(groups.items()):
    valid = [m["S"] for m in metrics if m["S"] is not None]
    support = [mean(m["U_por_camada"][str(layer)] > 0 for m in metrics) for layer in range(1, 4)]
    lines.append("| " + " | ".join([" / ".join(key), str(len(metrics)), fmt(mean(valid) if valid else None),
                                      fmt(median(m["A"] for m in metrics)), " / ".join(map(fmt, support))]) + " |")
lines.extend(["", "## Comparação com o método especialista", "",
              "A HTA prevê cinco toques em C1/A, seis em C1/B e três em C2/A e B. A inclui também deslocamentos ou mudanças de ampliação. Pela aproximação especialista do caderno E1, três acionamentos independentes de C2 correspondem a 3 × (1,35 + 1,10 + 0,20) = 7,95 s de preparação, apontamento e acionamento, sob a premissa de alvos localizados. A razão R_A compara contagens de ações do mesmo percurso geométrico. A latência e o tempo de relógio do registro não medem o desempenho humano.", "",
              "## Proveniência", ""])
for key, name, m, ops in summary:
    lines.append(f"- [{name}](logs/{name})")
if all(key[2] == "R" for key in groups):
    lines.extend(["", "Todas as sessões deste pacote usaram R. O ambiente não dispunha de credenciais dos provedores. Nenhuma requisição foi enviada a um LLM. Não há observações de desempenho de P, P2, P6, C ou G."])
(folder / "resumo_piloto.md").write_text("\n".join(lines) + "\n", encoding="utf8")
assert {("C1", "A", "R"), ("C1", "B", "R"), ("C2", "A", "R"), ("C2", "B", "R")} <= groups.keys()
(folder / "manifesto_instrumento.json").write_text(
    json.dumps(freeze_manifest(), ensure_ascii=False, indent=2) + "\n", encoding="utf8")
archive = folder.with_suffix(".zip")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            zipped.write(path, path.relative_to(folder))
with zipfile.ZipFile(archive) as zipped:
    assert zipped.testzip() is None
print(f"{archive.name}: {len(summary)} verified sessions")

