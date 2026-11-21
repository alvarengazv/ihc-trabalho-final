# Dicionário de eventos do cardápio

O arquivo de execução reúne `meta` (parâmetros sorteados, executor e número de ações de referência), `events` (sequência em ordem de inserção) e `final_state` (estado para verificação independente). A chave `dados` contém a carga específica do evento. Os campos de análise e as referências internas de itens pertencem ao registro do pesquisador. A requisição ao provedor conserva somente a instrução, a orientação funcional, o exemplo de treino e a observação filtrada com as ações permitidas.

## Campos comuns

| Campo | Tipo | Significado |
|---|---|---|
| id_evento | texto | Chave única do evento na execução. |
| id_sessao | texto | Identificador compartilhado pelos eventos da mesma sessão. |
| id_configuracao | texto | P, P2, P6, C, G, R ou identificação da interação manual. |
| id_tarefa | texto | C1 ou C2 no piloto. As tarefas reservadas não integram o pacote. |
| versao_interface | texto | A, lista contínua, ou B, organização em categorias. |
| versao_mecanismos | texto | Revisão do controlador comportamental. |
| hash_configuracao | texto | SHA-256 da configuração serializada com chaves ordenadas. |
| modelo_llm | texto ou nulo | Identificador solicitado ao provedor. Nulo para R. |
| versao_llm | texto ou nulo | Identificador devolvido pelo provedor quando conhecido. |
| semente | inteiro ou nulo | Semente do controlador local. O suporte do serviço à semente é registrado à parte. |
| passo | inteiro | Ciclo do executor. Vários eventos podem compartilhar um passo. |
| carimbo_tempo | texto | Instante ISO 8601 com fuso. A ordem interna conserva empates. |
| tela | texto | Cena S0 a S5 no instante de registro. |
| regiao_visivel | objeto ou nulo | x, y, z, largura e altura do recorte, em coordenadas CSS e fator de ampliação. Região desconhecida é nula. |
| synthetic | lógico | Verdadeiro para as execuções do agente e de R. |
| temperatura | número ou nulo | Temperatura solicitada, quando definida para o provedor. |
| tipo | texto | Um dos 23 nomes da lista fechada. |
| dados | objeto | Campos específicos, descritos a seguir. |

## Lista fechada

| Evento | Campos e interpretação |
|---|---|
| sessao_iniciada | parametros registra o perfil, a semente e os valores sorteados. Inicia a execução. |
| tarefa_iniciada | estado_inicial e pedido permitem reconstruir a condição inicial. |
| observacao | observacao contém a projeção pública, memoria contém trechos de exposições anteriores. elementos, estado_interface e rolagem servem à auditoria. |
| acao_proposta | acao, alvo e latencia_ms registram a escolha válida recebida do modelo. A resposta bruta de cada tentativa fica na auditoria. |
| acao_rejeitada | motivo e tentativa identificam formato ou escolha incompatível. A proposta rejeitada não incrementa A. |
| deslize_injetado | proposta, executada, alvo e ponto_inicial registram a substituição de um deslocamento por toque. |
| acao_executada | acao, alvo, origem e gesto identificam a fala realmente aplicada. Origem distingue LLM, R, pessoa, acionador e deslize. |
| vista_deslocada | anterior e nova descrevem as regiões antes e depois do deslocamento. |
| zoom_alterado | anterior e novo são os fatores de ampliação. |
| tela_alterada | anterior e nova são as cenas; a navegação entre categorias pode manter a mesma cena e registrar categoria. |
| elemento_visto | elemento, item_id, campo, texto, legivel, fragmentado e fracao_visivel descrevem a exposição geométrica. criterio_visivel exige o span numérico integral do preço ou quantidade, ou um prefixo nítido de até quatro caracteres no nome da linha. novo, entrada e reentrada distinguem primeira exposição, entrada e retorno. |
| opcao_selecionada | item e opcao registram o acompanhamento ou tamanho marcado. |
| item_adicionado | item, linha, opcao, quantidade e estado_posterior registram a inserção ou a soma de unidades. |
| item_alterado | linha, item, anterior, novo, quantidade e estado_posterior identificam a alteração. |
| item_removido | linha e anterior identificam o elemento removido; estado_posterior permite conferir o efeito. |
| ajuda_aberta | camada, topico, tela_origem e origem registram a primeira abertura ou o acesso a outra camada. |
| ajuda_fechada | camada, topico, tela_origem, retorno e origem identificam o encerramento do subdiálogo. |
| pedido_confirmado | pedido e estado_final preservam a comanda no ato de confirmação. |
| desistencia | A ação explícita de desistir interrompe a tarefa. |
| limite_atingido | numero_acoes registra o limite de ações executadas. |
| falha_tecnica | classe e mensagem identificam a causa técnica. Esta execução sai do denominador de sucesso. |
| tarefa_encerrada | resultado, categorias e metricas são calculados pelo verificador externo. |
| sessao_encerrada | Evento terminal sem carga obrigatória. |

## Unidades e interpretação

Dinheiro é armazenado em centavos inteiros, e a quantidade representa unidades da opção escolhida. Frações variam entre zero e um. O valor JSON nulo indica ausência, desconhecimento ou denominador nulo, conforme o campo. Um item geometricamente exposto pode permanecer sem leitura pela pessoa. A latência da API mede o serviço e não informa o tempo humano.

Cada tentativa remota conserva o corpo enviado, a projeção, o modelo solicitado, a resposta recebida quando disponível, a latência e eventuais rejeições. A semente do controlador garante a repetição de seus próprios sorteios. A resposta do serviço externo pode variar entre chamadas idênticas.
