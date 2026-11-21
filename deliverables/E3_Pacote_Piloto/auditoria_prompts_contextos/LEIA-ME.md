# Auditoria do contexto enviado

As quatro sessões incluídas neste pacote executaram o método de referência R. Esse executor opera localmente e não constrói um prompt. Os eventos `observacao` preservam a vista e a memória de cada passo. O campo `dados.estado_interface` pertence ao registro do analista, fora do canal da política.

As variáveis `GEMINI_API_KEY` e `ANTHROPIC_API_KEY` estavam ausentes durante a verificação. A quantidade de requisições a provedores neste pacote é **zero**. O ensaio de mecanismos de `python -m agent.demo` é uma demonstração roteirizada e fica fora da amostra.

Para executar um piloto com credenciais e um identificador de modelo disponível configurados no ambiente, use na raiz do projeto:

```powershell
# Defina GEMINI_API_KEY e GEMINI_MODEL antes de iniciar o processo.
foreach ($profileId in 'P','P2','P6','C','G') {
    foreach ($taskId in 'C1','C2') {
        foreach ($layoutId in 'A','B') {
            python -m agent.run --config $profileId --task $taskId --version $layoutId --seed 42 --provider gemini --out deliverables/E3_Pacote_Piloto
        }
    }
}
# Para Claude, defina ANTHROPIC_API_KEY e ANTHROPIC_MODEL.
python -m agent.run --config P --task C1 --version A --seed 42 --provider claude --out deliverables/E3_Pacote_Piloto
```

Cada tentativa grava `<sessão>/<passo>-<tentativa>.json` antes do envio. O arquivo contém a URL do método, o corpo exato da requisição, a observação, o modelo solicitado, a semente da API quando aceita e a temperatura (nula indica o padrão do provedor). Após o retorno, o arquivo recebe a resposta e a latência em milissegundos. A execução registra a versão informada pelo provedor. As chaves ficam nos cabeçalhos HTTPS e não são copiadas para o pacote. As respostas fora da gramática admitem duas novas tentativas. O campo `falha_tecnica` distingue interrupções técnicas de decisões incorretas.

