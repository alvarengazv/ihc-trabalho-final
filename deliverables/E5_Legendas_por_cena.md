# E5 · Legendas por cena

Texto exibido no vídeo `E5_Demonstracao_UXAgent.mp4` (04:47.7, 1920 × 1080, 30 fps). As legendas estão gravadas na imagem; o mesmo texto está em `E5_Demonstracao_UXAgent.srt`. A trilha de áudio é silenciosa; para narrar, leia cada bloco no intervalo indicado.

A gravação segue `E5_Roteiro_Demonstracao.md`. O visor e o terminal leem o pacote E3 entregue, extraído em `runs/E3_entregue`; nenhuma chamada à API é feita durante a demonstração. As saídas do terminal são as dos comandos do roteiro executados nesse pacote. A interface gravada tem o acabamento visual posterior a `0f54a89`; cenas, geometria, mecanismos e verificador são os da coleta.

## 00:00.0–00:06.0 · Abertura

_Cartão sem legenda._

## 00:06.0–00:20.1 · Preparação

- **00:06.0** Preparação: observatório e visor de registros do Gemini rodam localmente, um em cada terminal.
- **00:13.3** O visor lê o pacote E3 entregue; nenhuma chamada à API acontece durante a demonstração.

## 00:20.1–00:40.1 · 1 · A tarefa C2

- **00:20.1** Lívia usa ampliação de tela cheia para conferir o almoço que a irmã começou.
- **00:26.1** Em C2, ela precisa comparar o pedido com o combinado, corrigir o que estiver diferente e confirmar.
- **00:33.8** Queremos saber o que o agente realmente observou, fez e registrou.

## 00:40.1–01:01.0 · 2 · Versões A e B, e a MoLIC

- **00:40.1** A versão A usa uma lista contínua. A versão B reúne os mesmos itens em categorias e exibe um resumo no rodapé.
- **00:48.6** Para C2, os estados principais são o cardápio (S1), a revisão (S3) e a confirmação (S4).
- **00:55.5** A ajuda (S5) suspende a conversa e devolve a pessoa à cena de origem.

## 01:01.0–02:20.5 · 3 · Três passos do Gemini

- **01:01.0** Visor do E3: cada sessão do Gemini pode ser revista passo a passo, sem acesso à API.
- **01:07.6** Sessão C2-A-C-42-840b102d725e: o Gemini no perfil comparador C, passo 1.
- **01:13.4** O Gemini recebeu o enunciado e uma projeção da interface, com os gestos admissíveis.
- **01:20.0** A requisição arquivada traz orientação, um exemplo de treino, a tarefa literal e a observação — sem HTA, CTT, GOMS ou gabarito.
- **01:29.6** Primeiro, abriu a revisão: TOCAR(5) corresponde ao signo “Ver pedido (5)”.
- **01:35.5** Na interface, essa fala abre a revisão (S3) com as quatro linhas do pedido.
- **01:41.5** Depois, aumentou uma unidade do pudim: TOCAR(27) é o “+” da quarta linha.
- **01:47.3** O “−” de quantidade 1 vem sem gesto, como o botão esmaecido que a pessoa vê: o estado não é escrito por extenso.
- **01:55.9** No percurso, o pudim passa a 2 unidades e o total a R$ 83,40.
- **02:00.9** Por fim, confirmou: TOCAR(31) é “Confirmar pedido”. Cada passo teve uma única tentativa.
- **02:07.8** A cena de confirmação (S4) mostra a comanda corrigida.
- **02:12.2** O controlador aceita uma única fala válida por passo; o código de cada gesto só vale para aquela observação.

## 02:20.5–02:56.6 · 4 · Log e verificação externa

- **02:20.5** Aqui está o log da própria sessão, lido do pacote E3.
- **02:24.9** Cada passo registra a fala proposta, a ação executada e a mudança de estado; o resultado vem por último.
- **02:33.3** A comanda final: um frango com arroz, dois sucos de laranja, uma água sem gás e dois pudins.
- **02:40.5** O verificador externo leu esse estado e confirmou sucesso: S = 1.
- **02:45.7** Foram três ações; a referência também tem três, e a razão R_A é 1.
- **02:51.0** A confirmação na tela e o julgamento de sucesso são etapas diferentes.

## 02:56.6–03:42.6 · 5 · Mecanismos P fora do prompt

- **02:56.6** Inspeção manual de P: o operador escolhe o gesto; recorte, memória e deslizes seguem a configuração P.
- **03:04.5** O controlador sorteou cerca de 3,92 vezes de ampliação para esta sessão.
- **03:10.2** A política recebe só o trecho exposto e a memória de fragmentos já vistos.
- **03:16.1** TOCAR(4) é o trecho “Ver pe” do botão: a revisão abre, mas a quarta linha está fora do primeiro recorte.
- **03:24.2** Após mais um deslocamento, a memória guarda 4 trechos; os gestos mudam com a cena.
- **03:30.6** Recorte, varredura e memória são código parametrizado, fora do prompt do LLM.
- **03:36.7** A sessão Gemini que vimos usou C, o comparador em ampliação unitária (1×).

## 03:42.6–04:08.5 · 6 · Ajuda sob demanda

- **03:42.6** Em S3, a ajuda abre por uma ação registrada: F1 equivale ao gesto TOCAR(Ajuda).
- **03:48.9** A mesma fonte de conteúdo atende à pessoa e ao agente; só chega quando é solicitada.
- **03:55.5** O evento registra abertura, cena e camada: é a assinatura MAC “Socorro!”.
- **04:01.7** Esc fecha a ajuda: o registro mostra ajuda_fechada e o retorno de Ajuda para a Revisão.

## 04:08.5–04:41.7 · 7 · Resultados do piloto

- **04:08.5** C2/A confirmou a correção em três ações: S = 1, A = 3, R_A = 1.
- **04:13.6** Em C1, duas condições atingiram o limite de 150 ações; C2/B teve falha técnica da API (HTTP 429).
- **04:21.1** O KLM prevê 7,95 s de operadores — 3 × (M + P + K) — para um especialista com os alvos já localizados.
- **04:29.0** Esse valor e a latência do modelo são medidas distintas.
- **04:33.8** O pacote inclui as requisições, as ações e os resultados recalculáveis. V1 e V2 permanecem reservadas.

## 04:41.7–04:47.7 · Encerramento

_Cartão sem legenda._
