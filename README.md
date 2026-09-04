# X-One Forex Research Lab v4

Laboratório independente de pesquisa direcional para EUR/USD, sem execução de ordens.

## O que mudou na v2
- **Paginação de candles:** pedidos acima de 5.000 são divididos automaticamente em blocos de até 5.000, usando o candle mais antigo retornado como novo `end`.
- **Diagnóstico do dataset:** mostra solicitado, carregado, número de blocos e cobertura temporal.
- **Mobile-first reforçado:** controles, estatísticas, dataset, tabelas e matriz se adaptam a ecrãs pequenos; tabelas mantêm scroll horizontal quando necessário.
- **Código separado:** `index.html`, `styles.css` e `app.js`.
- **Sem execução:** o laboratório continua apenas com pesquisa histórica.

## Limitações preservadas
A avaliação mede direção comparando o close futuro com o close de entrada. Não modela payout, spread, slippage, MFE/MAE ou caminho intrabar.
