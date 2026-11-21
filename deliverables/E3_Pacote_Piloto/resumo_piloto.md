# Piloto de instrumentação

Resultados sintéticos recalculados sobre cada registro de execução. A referência é um percurso independente de R na mesma versão e ampliação inicial. Cada linha representa uma sessão.

| Tarefa | Versão | Executor | S | A | Toques | Desloc. | Nref | R_A | D | V | O | Erros E1–E6 | U |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| C1 | A | R | 1 | 8 | 5 | 3 | 8 | 1 | 1 | 0 | 0 | 0 / 0 / 0 / 0 / 0 / 0 | 0 |
| C1 | B | R | 1 | 7 | 6 | 1 | 7 | 1 | 0,333 | 0,333 | 0 | 0 / 0 / 0 / 0 / 0 / 0 | 0 |
| C2 | A | R | 1 | 3 | 3 | 0 | 3 | 1 | 0 | 0 | 0 | 0 / 0 / 0 / 0 / 0 / 0 | 0 |
| C2 | B | R | 1 | 3 | 3 | 0 | 3 | 1 | 0 | 0 | 0 | 0 / 0 / 0 / 0 / 0 / 0 | 0 |

## Taxas de erro por oportunidade

Cada célula mostra erros/oportunidades (taxa). O travessão identifica taxa indefinida. As oportunidades de E1 e E3 contam as escolhas efetivamente registradas. As de E5 contam as discrepâncias introduzidas no protocolo.

| Tarefa / versão / executor | E1 | E2 | E3 | E4 | E5 | E6 |
|---|---|---|---|---|---|---|
| C1 / A / R | 0/1 (0) | 0/0 (—) | 0/1 (0) | 0/3 (0) | 0/0 (—) | 0/0 (—) |
| C1 / B / R | 0/1 (0) | 0/0 (—) | 0/1 (0) | 0/1 (0) | 0/0 (—) | 0/0 (—) |
| C2 / A / R | 0/0 (—) | 0/0 (—) | 0/1 (0) | 0/0 (—) | 0/1 (0) | 0/0 (—) |
| C2 / B / R | 0/0 (—) | 0/0 (—) | 0/1 (0) | 0/0 (—) | 0/1 (0) | 0/0 (—) |

## Agregação por condição

| Tarefa / versão / executor | Iniciadas | S médio entre execuções sem falha técnica | Mediana de A | Proporção com ajuda por camada (1 / 2 / 3) |
|---|---:|---:|---:|---|
| C1 / A / R | 1 | 1 | 8 | 0 / 0 / 0 |
| C1 / B / R | 1 | 1 | 7 | 0 / 0 / 0 |
| C2 / A / R | 1 | 1 | 3 | 0 / 0 / 0 |
| C2 / B / R | 1 | 1 | 3 | 0 / 0 / 0 |

## Comparação com o método especialista

A HTA prevê cinco toques em C1/A, seis em C1/B e três em C2/A e B. A inclui também deslocamentos ou mudanças de ampliação. Pela aproximação especialista do caderno E1, três acionamentos independentes de C2 correspondem a 3 × (1,35 + 1,10 + 0,20) = 7,95 s de preparação, apontamento e acionamento, sob a premissa de alvos localizados. A razão R_A compara contagens de ações do mesmo percurso geométrico. A latência e o tempo de relógio do registro não medem o desempenho humano.

## Proveniência

- [C1-A-R-42-659ece35d501.json](logs/C1-A-R-42-659ece35d501.json)
- [C1-B-R-42-ba2d70506949.json](logs/C1-B-R-42-ba2d70506949.json)
- [C2-A-R-42-e53c277b4424.json](logs/C2-A-R-42-e53c277b4424.json)
- [C2-B-R-42-c62e9616b71a.json](logs/C2-B-R-42-c62e9616b71a.json)

Todas as sessões deste pacote usaram R. O ambiente não dispunha de credenciais dos provedores. Nenhuma requisição foi enviada a um LLM. Não há observações de desempenho de P, P2, P6, C ou G.
