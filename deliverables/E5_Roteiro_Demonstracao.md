# E5 · Roteiro completo de 4 min 45 s

### Preparação

Use três janelas em abas ou alternância rápida. Deixe aberta a primeira página do E4 atualizado, o diagrama MoLIC do E1 e o resumo do E3 para o fechamento. Para máxima coerência de versão, execute o servidor/visor a partir de uma cópia de `0f54a89` e aponte o visor para os registros extraídos do E3 revisado. Os comandos abaixo funcionam a partir da raiz atual e permitem ensaiar com os logs locais. A interface atual tem acabamento posterior; se a usar, identifique na gravação a diferença de revisão. Configure Python 3.10 ou superior. Se o PowerShell resolver `python` para o atalho da Microsoft Store, teste `py -3.12 --version` ou invoque diretamente o executável de Python instalado e substitua o comando nos exemplos.

Terminal 1, observatório.

```powershell
python -m app.server --port 8765
```

Abra [Observatório de interação](http://127.0.0.1:8765/) em duas abas. Na primeira deixe **Interface manual / C2 / A**. Na segunda deixe **Inspeção manual dos mecanismos P / C2 / B / semente 42**. Use janela larga. Deixe legíveis o telefone, a lente e o registro de eventos.

Terminal 2, visor dos registros Gemini existentes. Use o caminho extraído do E3 revisado no argumento `--run` quando ele estiver disponível.

```powershell
python -m tools.view_gemini --run runs/E3_Gemini --port 8766
```

Abra [Ações do Gemini](http://127.0.0.1:8766/). Em **Sessão**, selecione `C2-A-C-42-840b102d725e`. Em **Passo e tentativa**, comece em `001-1`. Faça o ensaio com os três passos. As respostas esperadas são `TOCAR(5)`, `TOCAR(27)` e `TOCAR(31)`. Cada passo tem uma única tentativa.

Terminal 3, verificador. Aponte `$arquivo` para a cópia extraída do E3 revisado quando disponível. Use os dados locais para ensaiar.

```powershell
$arquivo = 'runs/E3_Gemini/logs/C2-A-C-42-840b102d725e.json'
$log = Get-Content -Raw -Encoding utf8 $arquivo | ConvertFrom-Json
$log.events |
  Where-Object { $_.tipo -in 'tarefa_iniciada','acao_proposta','acao_executada','tela_alterada','item_alterado','pedido_confirmado','tarefa_encerrada' } |
  Format-Table passo,tipo,tela,@{n='ação ou resultado';e={
    if ($_.dados.gesto) { $_.dados.gesto }
    elseif ($_.dados.acao) { $_.dados.acao }
    elseif ($_.dados.resultado) { $_.dados.resultado }
    elseif ($_.dados.nova) { $_.dados.nova }
  }} -AutoSize
$log.final_state.pedido | Format-Table nome,opcao,quantidade -AutoSize
$m = python -X utf8 -m verifier $arquivo | ConvertFrom-Json
$m | Select-Object resultado,S,A,N_ref,R_A,U
$m.Re
```

Para relação visual com a sessão do Gemini, a primeira aba também pode ser preparada no modo **Executor de referência R / C2 / A / semente 42 / ampliação 1×**. Há três cliques em **Avançar um passo**. Identifique cada trecho como *visualização do percurso com R*. O visor de 8766 é a gravação de decisões do Gemini. Ele lê os dados arquivados e pode reproduzir a auditoria sem acesso à API.

### Gravação

| Tempo | O que abrir e fazer | Narração proposta |
|---|---|---|
| **00:00–00:25** | Observatório, **Interface manual / C2 / A**. Mostre a instrução literal e o botão **Ver pedido (5)**. | “Lívia usa ampliação de tela cheia para conferir o almoço que a irmã começou. Em C2, ela precisa comparar o pedido com o combinado, corrigir o que estiver diferente e confirmar. Queremos saber o que o agente realmente observou, fez e registrou.” |
| **00:25–00:50** | Alterne brevemente para a versão B e mostre categorias e resumo no rodapé. Abra a MoLIC do E1. Aponte S1, S3, S4 e ajuda S5. Volte à aba A. | “A versão A usa uma lista contínua. A B reúne os mesmos itens em categorias e exibe um resumo no rodapé. Para C2, os estados principais são cardápio, revisão e confirmação. A ajuda suspende a conversa e retorna à origem.” |
| **00:50–01:55** | Visor **Ações do Gemini**, sessão C2/A. Mostre `001-1` e a requisição, incluindo a instrução, os signos e as opções. Mostre `TOCAR(5)` aplicado, avance a `002-1` e mostre `TOCAR(27)`, depois `003-1` e `TOCAR(31)`. Entre os passos, pode mostrar a tela correspondente no R, sempre identificado. Priorize mostrar os três passos do Gemini e o vínculo com o log. | “O Gemini recebeu o enunciado e uma projeção da interface, com os gestos admissíveis. Primeiro abriu a revisão, depois aumentou uma unidade do pudim e por fim confirmou. O controlador aceita uma única fala válida por passo. O código de cada gesto só vale para aquela observação.” |
| **01:55–02:40** | Terminal 3. Sublinhe `tarefa_iniciada`, uma dupla `acao_proposta/acao_executada`, `item_alterado`, `pedido_confirmado` e `tarefa_encerrada`. Mostre a comanda final, as quatro quantidades e rode o verificador com a mesma sessão do visor. | “Aqui está o log da própria sessão. A comanda final ficou com um frango com arroz, dois sucos de laranja, uma água sem gás e dois pudins. O verificador leu esse estado e confirmou sucesso. Foram três ações, a referência também tem três e a razão é um. A confirmação na tela e o julgamento de sucesso são etapas diferentes.” |
| **02:40–03:30** | Observatório, **Inspeção manual dos mecanismos P / C2 / B / 42**. Abra **Observação filtrada**. Use `DESLOCAR(próximo)` duas vezes e `TOCAR(4)` para abrir a revisão. Mostre o recorte inicial sem a quarta linha completa e desloque mais uma vez. Aponte os fragmentos da memória e os gestos. | “Esta inspeção manual mostra P. O controlador sorteou cerca de 3,92 vezes de ampliação. A política recebe o trecho exposto e a memória de fragmentos já vistos. A quarta linha está fora do primeiro recorte. As regras de recorte, varredura e memória são código. A sessão Gemini que vimos usou C, o comparador em ampliação unitária.” |
| **03:30–04:00** | Em S3, pressione **F1**, mostre **Dica local**, mude para **Sobre esta tela** se houver tempo, mostre `ajuda_aberta` e pressione **Esc**. Aponte `ajuda_fechada` e o retorno a S3. | “A ajuda abre por uma ação registrada. A mesma fonte de conteúdo atende à pessoa e ao agente. Pelo evento sabemos que a ajuda foi aberta, de qual cena ela saiu e a qual cena voltou. A abertura corresponde operacionalmente à etiqueta Socorro.” |
| **04:00–04:45** | E4 e resumo de E3. Mostre a linha de C2/A, os dois limites de C1 e a falha técnica de C2/B. Mostre `3(MPK)`, 7,95 s, e feche em `S=1` da sessão. | “C2/A confirmou a correção em três ações. Em C1, duas condições chegaram ao limite e, em C2/B, houve falha da API. O KLM prevê 7,95 segundos de operadores para um especialista com os alvos já localizados. Esse valor e a latência do modelo são medidas distintas. O pacote inclui as requisições, as ações e os resultados recalculáveis. V1 e V2 permanecem reservadas.” |

### Conferência do MP4

Confirme duração entre 3 e 5 minutos, áudio inteligível, instrução e números legíveis, mesma sessão Gemini no visor e no terminal e distinção explícita entre o comparador C, o executor de referência R e a inspeção P. Deixe editor de credenciais, arquivo `.env.gemini-key` e valores das chaves fora da gravação. Se faltar tempo, reduza a abertura sobre as versões ou o trecho de ajuda. Preserve o começo da tarefa, os três passos Gemini, o log e o verificador. Uma execução nova depende de acesso ao provedor e de um protocolo versionado. Os três passos já registrados cobrem o percurso demonstrado.

### Versão gravada

`E5_Demonstracao_UXAgent.mp4` segue esta tabela em 1920 × 1080, 30 fps, com cartões de abertura e encerramento e uma cena curta de preparação com os dois servidores. A narração proposta aparece como legenda gravada na imagem; a trilha de áudio é silenciosa. O mesmo texto está em `E5_Demonstracao_UXAgent.srt` e, com os tempos de cada cena, em `E5_Legendas_por_cena.md`, para quem quiser gravar a voz. O visor e o terminal leem o pacote E3 entregue, extraído em `runs/E3_entregue`; as saídas exibidas no terminal são as dos comandos acima nessa cópia. A gravação usa a interface com acabamento visual posterior a `0f54a89` e identifica essa diferença no cartão de abertura. Cada trecho do executor R aparece rotulado como visualização do percurso com R.
