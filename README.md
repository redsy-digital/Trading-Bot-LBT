# X-One Forex Research Lab v1

Laboratório independente, single-file, sem framework e sem execução de ordens.

## Objetivo
Investigar hipóteses direcionais no EUR/USD usando candles históricos da Deriv, mantendo pesquisa separada do X-One operacional.

## Primeira hipótese
ATR14/preço em percentil recente, com relação INVERSE: <=40% → CALL; >=60% → PUT; 40–60% → NONE. Estes thresholds são parâmetros experimentais, não evidência confirmada.

## Metodologia
- M5/M15/M30/H1.
- Horizontes +15/+30/+60/+120.
- Split temporal treino/validação/holdout.
- AUC, skill, IC95%, expectancy direcional e drawdown unitário.
- Matriz 3D mantém a feature congelada entre células compatíveis.

## Limitações
O laboratório avalia direção pelo close futuro. Não modela payout, spread, slippage, execução, MFE/MAE ou caminho intrabar. Nenhum BUY é enviado.

## Uso
Abra `index.html` num navegador com internet, carregue candles e execute a hipótese. O WebSocket público da Deriv é usado apenas para dados históricos.
