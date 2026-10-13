# X-One Research Lab

Laboratório local e modular para análise estatística de históricos de ticks. Interface em português, desenhada para funcionar também em ecrãs pequenos.

## O que inclui
- Importação de JSON e CSV, incluindo formatos comuns da resposta `ticks_history` da Deriv (`history.prices` + `history.times`).
- Normalização de timestamps, símbolo, cotação, precisão e último dígito.
- Avisos para timestamps em falta, símbolos misturados, duplicados, ordem invertida e possíveis lacunas.
- Exportação do lote selecionado para JSON versionado e CSV.
- Estatísticas de variações, distribuição de dígitos, paridade, sequências e autocorrelação lag 1.
- Teste exploratório da variação do tick seguinte condicionado ao desvio face à média móvel.
- Probabilidades condicionais após sequências de N pares/ímpares.
- Backtest determinístico de paridade com stake e payout líquido hipotético, intervalo de confiança Wilson, P/L, valor esperado, profit factor, drawdown e sequência máxima de perdas.
- Separação cronológica 60/20/20 como orientação de pesquisa.
- Testes automatizados básicos.

## Executar no computador
Requer Python 3.10 ou superior.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

A aplicação abre no navegador. Para abrir no telemóvel, o computador e o telemóvel precisam de estar na mesma rede e deve-se iniciar Streamlit com `streamlit run app.py --server.address 0.0.0.0`; em redes públicas, não exponhas a aplicação sem proteção.

## Exportar ticks para análise comigo
1. Importa um JSON/CSV real.
2. Abre **Exportar**.
3. Escolhe “Últimos 1000” ou “Todos”.
4. Descarrega o JSON e anexa-o numa conversa ChatGPT.
5. Pede análise de reversão à média, autocorrelação, distribuição dos dígitos, dependências condicionais, sensibilidade por janelas e testes fora da amostra.

O JSON exportado tem a forma:

```json
{
  "schema": "x-one-research-lab.ticks.v1",
  "metadata": {
    "symbol": "R_10",
    "source": "ficheiro-importado.json",
    "exported_at_utc": "2026-01-01T00:00:00+00:00",
    "tick_count": 1000,
    "notes": "Dados normalizados; não altera a cotação original."
  },
  "ticks": [
    {
      "epoch": 1700000000,
      "datetime_utc": "2023-11-14T22:13:20+00:00",
      "symbol": "R_10",
      "quote": 123.45,
      "pip_size": 2,
      "digit": 5
    }
  ]
}
```

## Testes
```bash
pytest -q
```

## Limitações científicas importantes
- Um lote de 1000 ticks é útil para exploração inicial, mas normalmente é insuficiente para afirmar que existe uma vantagem robusta. Padrões podem surgir por acaso.
- “Reversão à média” aqui significa testar se o retorno seguinte depende do desvio atual face a uma média móvel. Isso não demonstra que o preço tenha uma lei universal de retorno à média.
- A autocorrelação é calculada sobre diferenças de preço, não sobre nível de preço. Autocorrelação zero não prova independência.
- O dígito final é extraído com `pip_size` quando fornecido. Se não houver precisão, usa-se até 8 casas decimais; confirma a precisão real do símbolo antes de confiar na análise de dígitos.
- O backtest de paridade é uma simulação de investigação. O payout é uma suposição configurável, não uma cotação histórica real. Não modela latência, rejeições, limites, custos ou regras exatas do contrato da Deriv.
- O separador cronológico é disponibilizado para ajudar a planear a validação; o resultado do backtest principal não deve ser confundido com validação fora da amostra.
- O laboratório não contém dados inventados nem afirma conhecer os algoritmos internos da Deriv.
