# UX-Agent · inspeção do cardápio e conferência do pedido

Cardápio móvel local e instrumentado do projeto de Interação Humano-Computador do CEFET-MG. A aplicação, as instruções experimentais, os documentos acadêmicos e a ajuda pública estão em português do Brasil. O piloto consolidado contém quatro sessões determinísticas de R e nove sessões do comparador com Gemini. Os adaptadores de modelo usam as APIs reais dos provedores.

O repositório hospedado para avaliação é <https://github.com/alvarengazv/ihc-trabalho-final>. Clone-o com `git clone https://github.com/alvarengazv/ihc-trabalho-final.git`. O pacote Git portátil do E2 (`deliverables/E2_Repositorio_Git.bundle`) fica fora do repositório hospedado; quando estiver disponível, `git clone deliverables/E2_Repositorio_Git.bundle ux-agent` restaura o mesmo histórico localmente.

## Entrega P3

Os PDFs de envio estão em `entregas/SIGAA_A3/` e `entregas/SIGAA_P3/` na cópia do grupo. Para recompilar os documentos, use as fontes de `deliverables/`. O PDF combinado `P3_E4_com_Apendice_E1.pdf` contém o E4 seguido do apêndice E1. O vídeo `E5_Demonstracao_UXAgent.mp4` reproduz a observação arquivada e as escolhas executadas, com legendas em português.

O instrumento da coleta corresponde à revisão `fc0ba7a`. O acabamento visual da branch principal é posterior. O E3 consolidado é `deliverables/E3_Piloto_Gemini.zip`. Extraia-o em uma pasta e execute `python -m tools.view_gemini --run CAMINHO_DA_PASTA` para abrir a sessão C2-A-C-42-840b102d725e. O artigo E4 e o apêndice E1 descrevem as condições do piloto. Para conferir o manifesto extraído, execute `python tools/freeze.py` na revisão da coleta, passando o caminho de `manifesto_instrumento.json` como argumento.

## Execução local

Para experimentar a demonstração manual com fotos ilustrativas dos 30 itens do restaurante, execute `python -m demo_photos` e abra [a demonstração com fotos](http://127.0.0.1:8768/). Escolha a lista contínua ou o leiaute por categorias e abra um item. As fotos aparecem depois dos controles de composição, na cena de detalhes. A demonstração usa o mesmo cardápio e as mesmas regras de pedido, sem tarefas do estudo, políticas do agente ou registros do piloto.

Use Python 3.10 ou superior. O cardápio, o executor, o verificador e os testes unitários usam apenas a biblioteca padrão do Python. A partir da raiz do projeto:

```powershell
python -m app.server --port 8765
```

Abra [o cardápio local](http://127.0.0.1:8765/). O console do pesquisador carrega as fontes Inter e JetBrains Mono do Google Fonts e, sem conexão, usa as fontes do sistema. O telefone simulado mantém fontes próprias, porque a geometria dos signos espelha `app/geometry.py`. Use uma janela de 360 × 800 pixels CSS para o telefone instrumentado. O experimentador pode inspecionar a vista ampliada, a observação permitida, as ações e o fluxo de eventos. C1 começa com o pedido vazio. C2 começa com o pedido da irmã já carregado; a revisão é aberta pela primeira ação do método de referência. O cardápio de treino tem cinco itens e instruções próprias.

```powershell
python -m unittest discover -s tests -v
python -m agent.run --config R --task C1 --version A --seed 42 --out runs
python -m agent.run --config R --task C2 --version B --seed 42 --out runs
Get-ChildItem runs/logs/*.json | ForEach-Object { python -m verifier $_.FullName }
```

O último comando recalcula os resultados das tarefas a partir do pedido e dos fatos registrados. R não usa modelo de linguagem. Sua contagem de ações de referência vem de um percurso separado na ampliação inicial medida. Carimbos de tempo e identificadores de sessão variam entre repetições. Com a mesma configuração local e a mesma semente, o caminho das regras e as métricas de estado são reproduzíveis.

## Piloto com modelo de linguagem

Para a calibração pareada completa com Gemini, defina `GEMINI_API_KEY` ou salve apenas a chave, em uma linha, no arquivo `.env.gemini-key` da raiz do projeto (ignorado pelo Git). Os comandos abaixo mostram as condições planejadas sem fazer requisições, conferem a chave e executam o piloto.

```powershell
python -m tools.run_gemini_pilot --plan
python -m tools.run_gemini_pilot --check-key
python -m tools.run_gemini_pilot
```

O executor pareia C, P, P2 e P6 em C1/C2 e A/B, com a semente 42 e um único modelo. O padrão é `gemini-3.5-flash-lite`. Defina `GEMINI_MODEL` ou `--model` para escolher outro modelo antes de criar o protocolo. A conferência da chave consulta os metadados do modelo sem gerar texto e imprime apenas os códigos de erro do provedor. O executor espaça as requisições em pelo menos seis segundos, no padrão de dez requisições por minuto. Ajuste `--rpm` à vazão disponível no projeto.

Uma falha transitória de rede ou um HTTP 408, 429, 500, 502, 503 ou 504 pode provocar até quatro novas tentativas do mesmo passo. O executor aplica espera exponencial, respeita o atraso sugerido pelo provedor quando ele é viável e registra cada tentativa separadamente. Use `--retries` e `--retry-base` para ajustar o número de tentativas e a espera inicial. Cotas diárias, erros de autenticação e atrasos maiores que o limite de dois minutos encerram a sessão como falha técnica. O limite de respostas JSON rejeitadas por ação é aplicado de forma independente.

As saídas e os registros de auditoria de cada requisição vão para `runs/E3_Gemini`. Se todas as tentativas falharem, corrija a causa e execute o mesmo comando novamente. As condições concluídas são puladas, e a condição que terminou em falha técnica recomeça do estado original com um novo identificador de sessão. As tentativas anteriores continuam arquivadas.

Quando o executor terminar, combine as sessões obtidas com as quatro execuções de referência. O ZIP gerado registra quantas condições planejadas terminaram sem falha técnica.

```powershell
python tools/package_pilot.py --gemini-run runs/E3_Gemini
```

Para acompanhar as ações do Gemini durante o lote ou inspecionar passos anteriores, execute `python -m tools.view_gemini` em um segundo terminal e abra [o visor local dos registros do Gemini](http://127.0.0.1:8766/). O visor lê os arquivos de auditoria do disco. Use `--run` para inspecionar outra pasta de saída. Os eventos executados ficam disponíveis quando a sessão grava seu registro final.

Defina `GEMINI_API_KEY` e `GEMINI_MODEL` com uma credencial e o identificador exato de um modelo da API Gemini habilitado na conta. Como alternativa, defina `ANTHROPIC_API_KEY` e `ANTHROPIC_MODEL`. Essas variáveis devem estar no ambiente do terminal que inicia o processo. A conta do provedor precisa permitir o modelo escolhido e a saída JSON estruturada. Cada comando pode fazer uma requisição paga por ação e repetir duas vezes uma escolha malformada. `--temperature` define um valor aceito pelo provedor; sem ele, vale o padrão do provedor. A semente local é sempre registrada. O Gemini também recebe uma semente do provedor; o Claude não recebe parâmetro de semente.

```powershell
python -m agent.run --config P --task C1 --version A --provider gemini --seed 42 --out runs
python -m agent.run --config C --task C1 --version A --provider gemini --seed 42 --out runs
python -m agent.run --config P2 --task C2 --version B --provider gemini --seed 42 --out runs
python -m agent.run --config P6 --task C2 --version B --provider gemini --seed 42 --out runs
python -m agent.run --config G --task C1 --version A --provider claude --seed 42 --out runs
```

Para a matriz completa de calibração com um único modelo e uma única semente:

```powershell
foreach ($profile in 'P','P2','P6','C','G') {
    foreach ($task in 'C1','C2') {
        foreach ($version in 'A','B') {
            python -m agent.run --config $profile --task $task --version $version --provider gemini --seed 42 --out runs
        }
    }
}
```

A linha de comando rejeita V1 e V2 antes de criar a aplicação ou contatar um provedor. A aplicação contém os estados iniciais e as operações dessas tarefas, mas um estudo de validação futuro exige um protocolo congelado à parte. O piloto não tem execuções de validação. Uma falha do provedor é uma interrupção técnica. Propostas inválidas nunca alteram o pedido. Os resultados dos demais perfis não podem ser inferidos a partir de R.

## Componentes e fluxo de dados

| Local | Responsabilidade |
|---|---|
| `app/catalog.py` | Conteúdo canônico do domínio e enunciados literais das tarefas, herdados das entregas anteriores. Valores monetários em centavos inteiros. |
| `app/model.py`, `app/geometry.py` | Transições entre cenas MoLIC, mudanças de estado permitidas e signos posicionados, usados pelo navegador e pelo executor. |
| `app/server.py` | Interface local no navegador para o participante e para a demonstração do pesquisador. |
| `design/` | Texto da ajuda, CTT, MoLIC, diagramas, paridade de signos e justificativas. |
| `agent/configs/v1.json` | Valores padrão versionados e distribuições de amostragem por perfil. |
| `agent/mechanisms/` | Recorte da vista, memória FIFO, fragmentação, deslize, revisão, estratégia de varredura e tratamento de impasse. |
| `agent/policies/` | Método R e políticas independentes, apenas com JSON, para Gemini e Claude. |
| `agent/run.py` | Bloqueio das tarefas de validação, orquestração, vocabulário fechado de eventos, captura de auditoria, arquivamento e chamada final ao verificador. |
| `verifier/` | Predicados sobre o pedido e análise de eventos. Recebe um registro concluído e não importa nenhum adaptador de modelo. |
| `tests/` | Dados sintéticos de teste, execuções de referência determinísticas e verificações de fronteira. |
| `deliverables/` | Artigos IEEE, E1, E3, roteiro e legendas do E5 e conferência das citações. |

O prompt do modelo é composto pela projeção visível, pelas ações permitidas, pelos fragmentos FIFO elegíveis, pela instrução funcional, pelo enunciado literal da tarefa e por um exemplo de treino. Fragmentos FIFO podem vir de cenas visitadas antes, se entraram na região visível e continuam na memória. G usa de propósito toda a cena renderizada como linha de base genérica. O registro de auditoria também guarda o estado completo da aplicação para o pesquisador. Depois de cada ação aceita, a interface emite seus eventos de domínio. O verificador compara o pedido com os critérios do analista, independentemente da política.

A extensão posterior ao piloto aceita `--hesitation-max-ms 500` em `agent.run` com perfil remoto. O valor é um teto experimental em milissegundos, sem calibração humana. A política de execução sorteia uma duração uniforme discreta antes de aplicar cada escolha aceita do LLM. O campo `dados.hesitacao_simulada_ms` no evento `acao_proposta` mede o atraso sorteado. A extensão possui versão própria e a sequência de sorteios é independente do gerador de deslizes. Os perfis da coleta arquivada usam os parâmetros originais.

## Perfis

| Perfil | Ampliação inicial | Limiar de legibilidade | Estratégia de varredura | Probabilidade de deslize | Memória |
|---|---|---:|---|---:|---|
| P | Uniforme [3, 5] | 3 | Linear | 0,05 | Uniforme em {3, 4, 5} |
| P2 | Uniforme [1,5; 2,5] | 1,5 | Linear 9/11, salto 2/11 | 0,05 | Igual |
| P6 | Uniforme [5,5; 7] | 3 | Linear 9/11, salto 2/11 | 0,05 | Igual |
| C | 1 | 1 | Livre | 0 | Igual |
| G | 1 | 1 | Página atual inteira | 0 | Ilimitada |
| R | 1 (ou `--reference-zoom`) | 1 | Método de referência | 0 | Por regras |

P, P2, P6 e C compartilham o mesmo limiar de ajuda (cinco ações sem progresso) e a mesma probabilidade de ajuda (0,5). A capacidade da memória é pareada pela semente, independentemente do sorteio da ampliação. Os signos elegíveis da cena e sua morfologia determinam as ações disponíveis. Cada execução tem limite de 150 ações. Os perfis podem desligar mecanismos individuais com `--disable M1` a `--disable M7`, repetível. Ablações pertencem à calibração. O hash da configuração cobre os parâmetros sorteados, a versão, os mecanismos ligados e a semente. Exemplo:

```powershell
python -m agent.run --config P --task C2 --version A --seed 42 --disable M7 --out runs
```

## Medidas e interpretação

S exige confirmação e pedido final correto. Um erro corrigido pode coexistir com sucesso. Falhas técnicas são relatadas à parte. Desistência e limite de ações contam como fracasso. E1–E6 distinguem seleção, associação, opção/quantidade, deslize motor, divergência na revisão e violação de regras. A conta as ações executadas. R_A divide A pelo comprimento de referência medido de forma independente. D conta deslocamentos e mudanças de ampliação por alvo localizado. V mede revisitas. O conta os signos obrigatórios ausentes antes da decisão. U registra aberturas de ajuda, acessos por camada e o primeiro acesso na sequência de ações. Uma oportunidade não observada resulta em `null` no JSON. As seis assinaturas MAC são hipóteses operacionais. O piloto não tem tempos de resposta comportamentais nem resultados com pessoas.

## Recompilar o pacote acadêmico

Os três documentos IEEE compartilham `deliverables/preambulo.tex`, `deliverables/referencias.bib` e o material vetorial de `design/`. Edite a macro `institution` no preâmbulo para mudar a linha institucional. Instale o Tectonic com acesso ao pacote TeX padrão, ou uma distribuição TeX com IEEEtran. Execute a partir do diretório indicado para que as entradas relativas sejam encontradas.

```powershell
Push-Location deliverables
tectonic DesignUXAgent_IHC_Grupo_Amorim_Alvarenga_Cruz.tex
tectonic UXAgent_P3_Artigo_E4.tex
tectonic UXAgent_P3_Anexo_E1.tex
Pop-Location
python -m pip install reportlab
python tools/build_dictionary.py
python tools/package_pilot.py
python tools/freeze.py
```

O montador do pacote recalcula o resultado de cada registro incluído, confere se todas as execuções usam C1/C2, regenera o resumo medido e verifica o CRC do ZIP. O arquivo registra quando nenhuma requisição foi enviada a um provedor. Consulte `deliverables/REFERENCIAS_PDF_CHECKLIST.md` para os arquivos das referências e `deliverables/E5_Roteiro_Demonstracao.md` para a demonstração.

O manifesto do instrumento registra o hash dos arquivos exatos da aplicação, das políticas, do verificador, da ajuda e do design no momento do empacotamento. Execute o último comando para conferir uma cópia do repositório contra esse retrato. O manifesto identifica o instrumento de calibração independentemente do hash de configuração de cada sessão. O console visual do pesquisador e os dados sintéticos de teste podem ser demonstrados sem conexão com `python -m agent.demo`. O atalho F1 da interface abre a ajuda, e Esc retorna à cena anterior quando ela permite.
