# X-One Research Lab — Web Edition

Laboratório local para importar histórico de ticks da Deriv, explorar estatísticas e testar regras fixas de forma cronológica.

## Arquitetura

- `frontend/`: interface HTML, CSS e JavaScript sem framework.
- `backend/`: API Python com FastAPI, motor estatístico e backtest modular.
- Importação de JSON/CSV pelo navegador; os dados são enviados à API apenas quando se pede análise/backtest.
- Exportação dos ticks normalizados em JSON e CSV.

> Esta ferramenta é para investigação estatística. Não prevê o próximo tick, não garante lucro e não replica necessariamente todos os detalhes de liquidação/payout dos contratos da Deriv. Resultados históricos não garantem resultados futuros.

## Requisitos

- Python 3.10+
- Um navegador moderno
- Internet apenas para instalar dependências Python (ou dependências já instaladas)

## Executar localmente

Na pasta do projeto:

```bash
python -m venv .venv
```

Ativar o ambiente:

**Windows**
```bash
.venv\\Scripts\\activate
```

**Linux/macOS**
```bash
source .venv/bin/activate
```

Instalar dependências e iniciar a API:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Abrir no navegador:

`http://127.0.0.1:8000`

A API serve também a interface estática. O endpoint de saúde é `http://127.0.0.1:8000/api/health`.

## Formatos aceites

CSV com coluna de preço (`price`, `quote`, `close` ou `value`) e, opcionalmente, `epoch`/`time`/`timestamp`, `symbol` e `pip_size`.

JSON:
- lista de objetos com preços;
- objeto com `ticks` ou `data`;
- formato Deriv semelhante a `history.prices` e `history.times`;
- lista simples de preços numéricos.

O laboratório tenta inferir o último dígito a partir da precisão do preço. Quando o ficheiro inclui `pip_size`, esse valor tem prioridade.

## O que é calculado

- Distribuição de dígitos 0–9, paridade e frequência relativa.
- Mudanças de preço, retornos e autocorrelação de lag 1.
- Comprimentos de sequências consecutivas.
- Probabilidades empíricas após sequências de paridade do mesmo tipo.
- Backtest cronológico de regra fixa de paridade, com payout assumido, stake, P/L, drawdown e divisão temporal 60/20/20.

## Limitações

- A estratégia de paridade serve como exemplo de execução determinística, não como recomendação de aposta.
- O payout introduzido no backtest é uma hipótese simplificada; confirme o payout efetivo no contrato e na plataforma.
- A API local não é um serviço público. Para publicar online, o frontend pode ser hospedado estaticamente, mas a API Python tem de ser publicada num serviço que execute Python. Não coloque tokens de conta Deriv no frontend.
