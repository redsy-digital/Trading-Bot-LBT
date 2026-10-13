import streamlit as st
import pandas as pd
import plotly.express as px
from lab.ingestion import load_uploaded_file, validate_ticks, export_ticks_json, export_ticks_csv
from lab.analysis import analyze_ticks, moving_average_reversion, parity_conditionals
from lab.backtest import run_parity_backtest, chronological_split

st.set_page_config(page_title="X-One Research Lab", page_icon="📊", layout="wide")
st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp { background: #0b0d12; }
section[data-testid="stSidebar"] { background: #11151d; }
h1,h2,h3 { letter-spacing: .2px; }
div[data-testid="stMetric"] { background: #141923; border: 1px solid #272d39; padding: 12px; border-radius: 10px; }
.lab-note { padding: 12px 14px; background: #171c26; border-left: 3px solid #e5484d; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

st.title("X-One Research Lab")
st.caption("Laboratório estatístico de ticks · Importação local · Backtests reproduzíveis")
st.markdown('<div class="lab-note"><b>Integridade científica:</b> resultados históricos descrevem a amostra analisada; não garantem previsibilidade nem lucro futuro. O laboratório não reproduz automaticamente cotações históricas de propostas/payouts da Deriv.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Dados")
    uploaded = st.file_uploader("Importar histórico de ticks", type=["json", "csv"])
    pasted = st.text_area("Ou colar JSON", height=120, placeholder='{"ticks":[{"epoch":...,"quote":...}]}')
    st.caption("Formatos suportados: JSON da API Deriv, arrays de ticks, CSV com timestamp/epoch e quote/price.")
    if st.button("Carregar JSON colado", use_container_width=True):
        if pasted.strip():
            try:
                import json
                import io
                uploaded_data = io.BytesIO(pasted.encode("utf-8"))
                uploaded_data.name = "ticks.json"
                st.session_state["loaded_ticks"] = load_uploaded_file(uploaded_data)
                st.session_state["source_name"] = "JSON colado"
                st.success("JSON carregado.")
            except Exception as e:
                st.error(f"Não foi possível ler o JSON: {e}")

if uploaded is not None:
    try:
        st.session_state["loaded_ticks"] = load_uploaded_file(uploaded)
        st.session_state["source_name"] = uploaded.name
    except Exception as e:
        st.error(f"Erro ao importar: {e}")

ticks = st.session_state.get("loaded_ticks")
if ticks is None or ticks.empty:
    st.info("Começa por importar um ficheiro JSON/CSV de ticks. Não são criados dados fictícios.")
    st.subheader("Fluxo recomendado")
    st.markdown("1. Exporta um lote real de ticks da fonte que estás a investigar.\n2. Importa o JSON/CSV aqui.\n3. Confere símbolo, ordem temporal, duplicados e precisão.\n4. Analisa reversão à média e probabilidades condicionais.\n5. Exporta o lote ou os resultados para revisão.")
    st.stop()

ticks, issues = validate_ticks(ticks)
if not issues.empty:
    with st.expander("Avisos de qualidade dos dados", expanded=True):
        st.dataframe(issues, use_container_width=True, hide_index=True)

symbol = str(ticks["symbol"].dropna().iloc[0]) if ticks["symbol"].notna().any() else "Não identificado"
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ticks válidos", f"{len(ticks):,}")
c2.metric("Símbolo", symbol)
c3.metric("Preço inicial", f"{ticks.iloc[0]['quote']:.8f}".rstrip("0").rstrip("."))
c4.metric("Preço final", f"{ticks.iloc[-1]['quote']:.8f}".rstrip("0").rstrip("."))
if len(ticks) < 30:
    st.warning("A amostra é pequena. Estatísticas e intervalos serão instáveis.")

tab_data, tab_stats, tab_backtest, tab_export = st.tabs(["Histórico", "Análise estatística", "Backtest", "Exportar"])

with tab_data:
    st.subheader("Série de preços")
    chart_df = ticks.copy()
    chart_df["index"] = range(len(chart_df))
    st.plotly_chart(px.line(chart_df, x="index", y="quote", title="Preço por ordem do tick", labels={"index":"Índice do tick","quote":"Preço"}), use_container_width=True)
    st.dataframe(ticks.tail(500).iloc[::-1], use_container_width=True, hide_index=True)
    st.caption("Tabela: até aos últimos 500 registos, do mais recente para o mais antigo. O dataset completo continua disponível para análise/exportação.")

with tab_stats:
    st.subheader("Resumo estatístico")
    stats = analyze_ticks(ticks)
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Variação positiva", f"{stats['up_pct']:.2f}%")
    m2.metric("Variação negativa", f"{stats['down_pct']:.2f}%")
    m3.metric("Autocorrelação lag 1", "N/D" if pd.isna(stats["return_autocorr_lag1"]) else f"{stats['return_autocorr_lag1']:.4f}")
    m4.metric("Mediana |retorno|", f"{stats['median_abs_return']:.8g}")
    st.markdown("#### Distribuição do último dígito")
    digits = pd.DataFrame({"Dígito": list(range(10)), "Contagem": [stats["digit_counts"].get(i,0) for i in range(10)]})
    digits["Percentagem"] = digits["Contagem"] / max(len(ticks),1) * 100
    st.plotly_chart(px.bar(digits, x="Dígito", y="Percentagem", title="Frequência observada dos dígitos (%)"), use_container_width=True)
    st.markdown("#### Paridade e sequências")
    st.json({"even_pct": stats["even_pct"], "odd_pct": stats["odd_pct"], "longest_even_run": stats["longest_even_run"], "longest_odd_run": stats["longest_odd_run"], "return_autocorr_lag1": stats["return_autocorr_lag1"], "mean_return": stats["mean_return"], "std_return": stats["std_return"]})
    st.markdown("#### Teste exploratório de reversão à média")
    window = st.slider("Janela da média móvel (ticks)", 5, min(200, max(5, len(ticks)//2)), min(20, max(5, len(ticks)//2)))
    buckets = moving_average_reversion(ticks, window=window)
    if buckets.empty:
        st.warning("Dados insuficientes para esta janela.")
    else:
        st.dataframe(buckets, use_container_width=True, hide_index=True)
        st.caption("Agrupa a distância do preço à média móvel e mede a variação seguinte. Retorno negativo após desvio positivo (e vice-versa) é compatível com reversão nesta amostra, mas não prova uma lei estável.")
    st.markdown("#### Probabilidade condicional de paridade")
    n = st.slider("Comprimento da sequência anterior", 1, min(12, max(1, len(ticks)//4)), min(4, max(1, len(ticks)//4)))
    cond = parity_conditionals(ticks, n)
    st.dataframe(cond, use_container_width=True, hide_index=True)
    st.caption("Compara a paridade seguinte após N dígitos pares/ímpares com a frequência-base. A diferença pode ser ruído amostral; confira contagens e teste fora da amostra.")

with tab_backtest:
    st.subheader("Backtest de regra determinística: paridade")
    st.write("Regra: após N dígitos consecutivos de uma paridade, apostar na paridade oposta no tick seguinte. O resultado usa apenas o dígito observado nesse tick.")
    n = st.slider("Sequência exigida (backtest)", 1, min(12, max(1, len(ticks)//4)), min(4, max(1, len(ticks)//4)), key="bt_n")
    trigger = st.selectbox("Sequência que ativa entrada", ["Ímpares consecutivos", "Pares consecutivos"])
    stake = st.number_input("Stake por operação (unidades)", min_value=0.01, value=1.0, step=0.25)
    payout = st.number_input("Lucro líquido por vitória / stake", min_value=0.01, value=0.9, step=0.05, help="Suposição manual. Não é cotação histórica real da Deriv.")
    train, valid, test = chronological_split(ticks)
    result, trades = run_parity_backtest(ticks, n, trigger == "Ímpares consecutivos", stake, payout)
    a,b,c = st.columns(3)
    a.metric("Operações", result["trades"])
    b.metric("Taxa de acerto", f"{result['win_rate']:.2f}%")
    c.metric("P/L simulado", f"{result['net_profit']:.4f}")
    st.json({k:v for k,v in result.items() if k not in ["equity_curve"]})
    st.markdown("#### Separação cronológica")
    st.write(f"Desenvolvimento: {len(train)} ticks · Validação: {len(valid)} ticks · Teste final: {len(test)} ticks.")
    st.warning("Este painel apresenta o backtest da amostra completa para exploração. Para uma avaliação rigorosa, escolha a regra na fase de desenvolvimento e reporte separadamente a validação e o teste final. Payout, latência, rejeições e execução real não são reconstruídos.")
    if not trades.empty:
        st.dataframe(trades.tail(300).iloc[::-1], use_container_width=True, hide_index=True)

with tab_export:
    st.subheader("Exportar lote de ticks")
    amount = st.selectbox("Quantidade de ticks", ["Últimos 100", "Últimos 500", "Últimos 1000", "Últimos 5000", "Todos"], index=2)
    count = {"Últimos 100":100, "Últimos 500":500, "Últimos 1000":1000, "Últimos 5000":5000, "Todos":len(ticks)}[amount]
    batch = ticks.tail(count).copy()
    st.write(f"Serão exportados **{len(batch)}** ticks.")
    json_bytes = export_ticks_json(batch, source=st.session_state.get("source_name", "importado"))
    csv_bytes = export_ticks_csv(batch)
    st.download_button("Descarregar JSON", json_bytes, file_name=f"ticks_{symbol}_{len(batch)}.json", mime="application/json", use_container_width=True)
    st.download_button("Descarregar CSV", csv_bytes, file_name=f"ticks_{symbol}_{len(batch)}.csv", mime="text/csv", use_container_width=True)
    st.caption("O JSON inclui versão do esquema, símbolo, origem, data de exportação e registos normalizados. Revê os avisos antes de partilhar a amostra.")
