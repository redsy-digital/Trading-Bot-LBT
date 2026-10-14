# X-One Research Lab — Vercel Edition

Laboratório web para pedir históricos de ticks diretamente à API pública da Deriv, executar análises estatísticas e testar regras fixas com a mesma amostra.

## Estrutura

- `index.html` — página principal na raiz do repositório.
- `styles.css` e `app.js` — interface e ligação direta ao WebSocket da Deriv.
- `main.py` — ponto de entrada ASGI para o Vercel.
- `backend/` — API FastAPI, análise estatística e backtest.
- `pyproject.toml` — dependências e versão de Python suportada.

## Como funciona

1. Escolhe o símbolo Deriv.
2. Define a quantidade de ticks (100 a 5 000).
3. Carrega em **Carregar histórico da Deriv**.
4. O navegador pede o histórico através do WebSocket oficial da Deriv, sem upload manual e sem token de conta.
5. A mesma amostra fica disponível para análise, backtest e exportação em JSON ou CSV.

O App ID predefinido é `1089`. Se a Deriv deixar de aceitar esse ID, usa um App ID válido da tua aplicação Deriv. O App ID não é um token de conta. Não coloques tokens privados nesta aplicação.

## Publicar no Vercel

1. Extrai o ZIP.
2. Envia todo o conteúdo da pasta para um repositório GitHub.
3. No Vercel, escolhe **Add New → Project** e importa esse repositório.
4. Mantém a raiz do projeto como **Root Directory** (não escolhas `backend`).
5. Deixa o Vercel detetar a aplicação Python/FastAPI e publica.
6. Testa:
   - `/` — interface;
   - `/api/health` — estado da API;
   - `/docs` — documentação da API.

A aplicação usa Python 3.12 e o entrypoint ASGI `main:app`. O `index.html` fica na raiz como solicitado. Não é necessária base de dados para esta versão.

## Executar localmente

```bash
python -m venv .venv
```

Ativa o ambiente e instala dependências:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Abre `http://127.0.0.1:8000`.

## Notas e limitações

- O histórico é pedido à Deriv pelo navegador. O backend recebe a amostra apenas quando pedes análise ou backtest.
- O projeto não guarda dados entre sessões. Exporta JSON/CSV para arquivar o histórico.
- A quantidade de histórico disponível pode variar conforme símbolo, disponibilidade da API e limites da Deriv.
- A derivação do último dígito usa a precisão devolvida no preço e a informação de pip size quando estiver disponível.
- O backtest é uma simulação estatística com payout configurável; não garante execução, lucro nem reprodução exata da liquidação de contratos.
- Dados históricos não predizem o próximo tick.
