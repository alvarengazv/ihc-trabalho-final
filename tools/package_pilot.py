"""Verify all E3 logs, write the measured summary, then build its ZIP."""
import argparse
from pathlib import Path
import json
import shutil
import sys
from tempfile import TemporaryDirectory
import zipfile
from collections import Counter
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verifier import evaluate
from agent.run import EVENTS
from freeze import freeze_manifest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--gemini-run", type=Path, help="Include a measured Gemini run alongside the R reference")
args = parser.parse_args()
folder = ROOT / "deliverables" / "E3_Pacote_Piloto"
archive = folder.with_suffix(".zip")
protocol = None
recorded_conditions = set()
audit_records = Counter()
versions = set()
if args.gemini_run:
    protocol_path = args.gemini_run / "protocolo_gemini.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf8"))
    assert protocol["hash_instrumento"] == freeze_manifest()["hash_instrumento"], protocol_path
    assert protocol["provedor"] == "gemini"
    assert any((args.gemini_run / "logs").glob("*.json")), "No persisted Gemini runs"
    staging = TemporaryDirectory(prefix="ux-agent-e3-")
    staging_path = Path(staging.name) / "E3_Piloto_Gemini"
    shutil.copytree(folder, staging_path)
    folder = staging_path
    archive = ROOT / "deliverables" / "E3_Piloto_Gemini.zip"
    shutil.copytree(args.gemini_run / "logs", folder / "logs", dirs_exist_ok=True)
    shutil.copytree(args.gemini_run / "auditoria_prompts_contextos",
                    folder / "auditoria_prompts_contextos", dirs_exist_ok=True)
    shutil.copyfile(protocol_path, folder / protocol_path.name)

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
    if protocol and log["meta"]["executor"] == "gemini":
        condition = (key[2], key[0], key[1])
        assert list(condition) in protocol["condicoes"], path
        assert (head["modelo_llm"], head["semente"], head["temperatura"]) == (
            protocol["modelo"], protocol["semente"], protocol["temperatura"]), path
        public = {e["passo"]: e["dados"]["observacao"] for e in events if e["tipo"] == "observacao"}
        audit_path = folder / "auditoria_prompts_contextos" / head["id_sessao"]
        accepted = 0
        for attempt in sorted(audit_path.glob("*.json")):
            request = json.loads(attempt.read_text(encoding="utf8"))
            step, _ = attempt.stem.split("-")
            prompt = json.loads(request["requisicao"]["contents"][0]["parts"][0]["text"])
            assert (request["observacao"] == prompt["observacao"] == public[int(step)]), attempt
            audit_records["tentativas"] += 1
            if "resposta" in request:
                audit_records["respostas"] += 1
            if request.get("modelo_retornado"):
                accepted += 1
                versions.add(request["modelo_retornado"])
        assert accepted == sum(e["tipo"] == "acao_proposta" for e in events), path
        if result["resultado"] != "falha_tecnica":
            recorded_conditions.add(condition)
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
if protocol:
    planned = len(protocol["condicoes"])
    completed = len(recorded_conditions)
    lines.extend(["", "## Chamadas ao Gemini", "",
                  f"Foram concluídas {completed} de {planned} condições planejadas. "
                  f"O diretório de auditoria contém {audit_records['tentativas']} tentativas de requisição, "
                  f"com {audit_records['respostas']} respostas registradas. "
                  "Falhas técnicas aparecem como registros distintos, com S indefinido.", "",
                  f"Modelo solicitado: {protocol['modelo']}. "
                  f"Versões retornadas: {', '.join(sorted(versions)) or 'nenhuma'}. "
                  f"Semente local e da API: {protocol['semente']}. "
                  "Uma execução por condição serve à calibração e não estima uma distribuição de desempenho."])
    (folder / "auditoria_prompts_contextos" / "LEIA-ME.md").write_text(
        "# Auditoria do contexto enviado\n\n"
        "Cada diretório de sessão contém os arquivos de tentativa com o corpo da requisição, "
        "a observação, a resposta do provedor quando recebida, a latência e a identificação do modelo. "
        "As quatro sessões R não geraram chamadas. "
        "Consulte protocolo_gemini.json para a matriz prevista e resumo_piloto.md para o que foi observado.\n",
        encoding="utf8")
elif all(key[2] == "R" for key in groups):
    lines.extend(["", "Todas as sessões deste pacote usaram R. O ambiente não dispunha de credenciais dos provedores. Nenhuma requisição foi enviada a um LLM. Não há observações de desempenho de P, P2, P6, C ou G."])
(folder / "resumo_piloto.md").write_text("\n".join(lines) + "\n", encoding="utf8")
assert {("C1", "A", "R"), ("C1", "B", "R"), ("C2", "A", "R"), ("C2", "B", "R")} <= groups.keys()
(folder / "manifesto_instrumento.json").write_text(
    json.dumps(freeze_manifest(), ensure_ascii=False, indent=2) + "\n", encoding="utf8")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            zipped.write(path, path.relative_to(folder))
with zipfile.ZipFile(archive) as zipped:
    assert zipped.testzip() is None
print(f"{archive.name}: {len(summary)} verified sessions")

