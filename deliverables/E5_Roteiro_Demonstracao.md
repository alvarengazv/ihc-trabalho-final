# E5 · Do pedido da irmã à verificação externa

**Duração prevista de 4 min 30 s.** O percurso principal mostra uma execução completa e reproduzível de R em C2/B. A inspeção de P e a sequência roteirizada de mecanismos têm identificação própria na gravação. A última seção orienta a substituição de um trecho por uma execução real em API, caso o grupo disponha de credenciais.

## Preparação

1. Abra dois terminais PowerShell na raiz do projeto. No primeiro, inicie o servidor e deixe-o ativo.

   ```powershell
   python -m app.server --port 8765
   ```

2. Abra [o observatório local](http://127.0.0.1:8765/) em duas abas. Na primeira, selecione **Interface manual**, **C2 · Pedido da irmã**, **A** e **Iniciar sessão**. Na segunda, repita com **B**. Mantenha a largura da janela do navegador acima de 1.160 pixels para enquadrar o restaurante à esquerda e a instrumentação à direita. A tela simulada mede 360 × 800 pixels CSS. Na gravação, amplie o enquadramento do vídeo quando precisar mostrar texto, preservando o zoom do navegador e a ampliação configurada no experimento.

3. No segundo terminal, prepare a saída dos mecanismos e o resumo de uma sessão arquivada. A demonstração roteirizada usa C1/C2 e não grava dados de piloto. O comando de verificação lê o pacote entregue.

   ```powershell
   $mecanismos = python -X utf8 -m agent.demo
   $arquivo = (Get-ChildItem 'deliverables/E3_Pacote_Piloto/logs/C2-B-R-42-*.json' | Select-Object -First 1).FullName
   $medidas = python -X utf8 -m verifier $arquivo | ConvertFrom-Json
   ```

   Mantenha o navegador em primeiro plano. Alterne para o terminal durante os trechos indicados. Para a exposição ao vivo, disponha o navegador à esquerda e o terminal à direita em um monitor largo. Para a gravação, prefira alternar janelas em tela cheia para conservar a legibilidade.

## Sequência de gravação

### 00:00–00:30 · O combinado

**Imagem e gesto.** Primeira aba. Enquadre a instrução de C2 e leia a última parte do combinado. Aponte para o cardápio. Mostre o primeiro grupo de alimentos e role até o seguinte.

**Narração.** “Lívia quer terminar o almoço que a irmã começou. Elas combinaram um frango com arroz, dois sucos, uma água e dois pudins. Quem usa ampliação de tela cheia pode enxergar o nome de um alimento enquanto a quantidade já está fora de vista. Projetamos um cardápio para permitir que Lívia confira e corrija o pedido antes de enviá-lo. Nesta demonstração, uma mesma interface atende à pessoa e fornece os signos que o agente pode observar.”

### 00:30–01:10 · Duas interfaces e uma conversa

**Imagem e gesto.** Aponte para **Ver pedido** na versão A. Na segunda aba, mostre as categorias e o rodapé com linhas e total. Escolha **Executor de referência R**, mantenha **C2**, **B**, semente **42**, ampliação **1×**, e clique em **Iniciar sessão**. Mostre a instrução e acione **Avançar um passo**. Desça no documento até enquadrar a quarta linha do pedido.

**Narração.** “Na versão A, os trinta itens aparecem em sequência e o pedido tem uma tela de revisão. A versão B organiza os mesmos itens por categoria. Seu rodapé acompanha a seleção e pode sair da região ampliada. Agora R executa o método especialista. Sua primeira ação abre a revisão. A interface permite alterar uma linha ou confirmar o pedido nessa cena. Cada mudança de assunto segue a conversa descrita pela MoLIC. O pesquisador pode consultar o modelo completo, enquanto o agente recebe somente as ações disponíveis.”

### 01:10–01:45 · Resultado completo em C2

**Imagem e gesto.** Clique em **Avançar um passo**, enquadre **Pudim de leite** com duas unidades e clique em **Avançar um passo** novamente. Mostre **Registro de eventos**, abra **Eventos em JSON** e encontre `pedido_confirmado` e `tarefa_encerrada`. Em **Verificação externa**, realce `S`, `A` e `R_A`.

**Narração.** “R corrigiu a quarta linha e confirmou. O registro conserva separadamente a alteração, a confirmação e o resultado calculado. O verificador confere os quatro alimentos, as opções e as quantidades do pedido final. Temos sucesso igual a um, três ações executadas e razão de ações igual a um. Isso confirma o funcionamento deste percurso de referência. Se o pudim permanecesse com uma unidade, a confirmação registraria a discrepância E5.”

### 01:45–02:35 · O que chega ao outro receptor

**Imagem e gesto.** Na primeira aba, selecione **Inspeção manual dos mecanismos P**, **C2**, **B**, semente **42** e **Iniciar sessão**. Abra **Observação filtrada**. Execute **DESLOCAR(próximo)** duas vezes. Localize o trecho **Ver pe** com o gesto **TOCAR(4)**, selecione esse gesto e execute-o para abrir a revisão. Enquadre o detalhe da quarta linha no cartão à esquerda e o recorte inicial de S3 na lente. Execute mais um **DESLOCAR(próximo)** e mostre os trechos já registrados na memória. No terminal, mostre a parte inicial da demonstração.

```powershell
$mecanismos | Select-Object -First 39
```

**Narração.** “Aqui o operador escolhe os gestos e o controlador aplica P. Com esta semente, a ampliação é de aproximadamente 3,92 vezes. M1 recorta a geometria, e M5 aplica essa restrição também à revisão. A discrepância do pudim fica fora da primeira janela ampliada. M6 restringe a varredura disponível. M2 conserva um número limitado de trechos que já saíram da vista. Observe agora o exemplo roteirizado de M3: aparece o preço de trinta e seis reais e noventa centavos. O nome do prato ficou acima do recorte. Entregar o nome juntamente com o preço revelaria uma associação que a pessoa ainda teria de reconstruir.”

### 02:35–03:20 · Deslize, impasse e ajuda

**Imagem e gesto.** No terminal, mostre os dois trechos de saída:

```powershell
$mecanismos | Select-String 'M4 •' -Context 0,17
$mecanismos | Select-String 'M7 •' -Context 0,19
```

Volte à primeira aba. Pressione **F1**, mostre o título **Ajuda** e o registro `ajuda_aberta`. Pressione **Esc** e mostre o retorno ao cardápio.

**Narração.** “A sequência de teste usa a semente sete para tornar visível um deslize. M4 troca o deslocamento por um toque no início do gesto; o registro preserva a proposta, o ponto e a transição observada. Na sequência de impasse, cinco ações sem progresso habilitam M7. Neste exemplo, o sorteio aciona a ajuda. Na aplicação, também podemos solicitá-la diretamente. O acesso fica registrado antes da próxima observação. As três camadas apresentam o mesmo conteúdo para ambos os receptores. A assinatura operacional ‘Socorro!’ conta uma abertura de ajuda. Ela descreve um evento observável.”

### 03:20–04:00 · Auditoria e comparação

**Imagem e gesto.** No terminal, recalcule as medidas, exiba os contadores de erro e depois abra o resumo do pacote:

```powershell
$medidas = python -X utf8 -m verifier $arquivo | ConvertFrom-Json
$medidas | Select-Object S,A,N_ref,R_A,U
$medidas.erros
Get-Content -Encoding utf8 deliverables/E3_Pacote_Piloto/resumo_piloto.md | Select-Object -First 10
```

**Narração.** “O mesmo verificador consegue recalcular o resultado a partir do arquivo entregue. Nos quatro ensaios de R, cada tarefa terminou com o pedido esperado, sem ocorrências de E1 a E6 e sem acesso à ajuda. Em C1, A exigiu cinco toques e três deslocamentos. B precisou de seis toques e um deslocamento. Em C2, os três toques coincidem com o método previsto. A estimativa KLM de sete vírgula noventa e cinco segundos para esse método supõe um especialista, alvos já localizados e ausência de erro.”

### 04:00–04:30 · Alcance do piloto

**Imagem e gesto.** Mantenha a tabela visível, destaque a coluna **Executor** e a sigla R. Aponte para **Proveniência** ao final do resumo. Termine na janela do restaurante com a confirmação.

**Narração.** “O comparador C compartilha com P a memória sorteada e a disposição para pedir ajuda. Começa com ampliação unitária, varredura livre e probabilidade de deslize zero. Neste pacote, todas as execuções pertencem a R. Comparar o desempenho de C e P requer executar o mesmo protocolo com um modelo real. Os sinais observados aqui permitem auditar a instrumentação. A comparação com pessoas depende de dados humanos independentes e das tarefas de validação preservadas para o estudo futuro.”

## Trecho alternativo quando houver acesso ao provedor

Antes da gravação, execute uma sessão real nos perfis desejados, usando o mesmo modelo e semente. Configure no ambiente as variáveis `GEMINI_API_KEY` e `GEMINI_MODEL` com acesso e identificador válidos. Mantenha as credenciais fora do enquadramento.

```powershell
python -m agent.run --provider gemini --model $env:GEMINI_MODEL --config P --task C2 --version B --seed 42 --out runs/demo-real
python -m agent.run --provider gemini --model $env:GEMINI_MODEL --config C --task C2 --version B --seed 42 --out runs/demo-real
Get-ChildItem runs/demo-real/logs/*.json | ForEach-Object { python -X utf8 -m verifier $_.FullName }
```

Substitua os últimos 30 segundos por um recorte da sessão real. Mostre a primeira observação e a ação recebida em `runs/demo-real/auditoria_prompts_contextos`, depois a última ocorrência de `tarefa_encerrada` no log correspondente. Leia o identificador do modelo e o desfecho efetivamente registrados, inclusive se houver desistência, limite ou falha técnica. Identifique o material como sessão adicional de demonstração. O pacote E3 acima descreve as quatro sessões de R.
