let ticks = [];
let filename = "deriv-history";
let currentSymbol = "";
const $ = (id) => document.getElementById(id);

async function checkApi() {
  try {
    const r = await fetch("/api/health");
    if (!r.ok) throw new Error();
    $("apiStatus").textContent = "API ligada";
    $("status").classList.add("online");
  } catch {
    $("apiStatus").textContent = "API indisponível";
    toast("A API de análise não está disponível. Confirma a implantação no Vercel.");
  }
}
checkApi();

function toast(message) {
  const el = $("toast"); el.textContent = message; el.classList.add("show");
  clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove("show"), 4500);
}
function setReady() {
  const ready = ticks.length >= 2;
  ["analyzeBtn","exportJson","exportCsv"].forEach(id => $(id).disabled = !ready);
  $("backtestBtn").disabled = ticks.length < 10;
  $("fileInfo").textContent = ticks.length
    ? `${currentSymbol} · ${ticks.length.toLocaleString()} ticks carregados`
    : "Nenhum histórico carregado";
  $("tickCount").textContent = `${ticks.length.toLocaleString()} ticks`;
  $("previewWrap").classList.toggle("hidden", !ready);
  renderPreview();
}
function inferPipSize(priceText) {
  const s = String(priceText);
  if (!s.includes(".")) return 1;
  const decimals = s.split(".")[1].length;
  return 10 ** (-Math.min(decimals, 10));
}
function digitFor(priceText, pipSize) {
  const price = Number(priceText);
  let decimals;
  if (Number.isFinite(pipSize) && pipSize > 0) decimals = Math.max(0, Math.min(10, Math.round(-Math.log10(pipSize))));
  else decimals = String(priceText).includes(".") ? String(priceText).split(".")[1].length : 0;
  return Math.abs(Math.round(price * 10 ** decimals)) % 10;
}
function normalizeDerivHistory(payload, symbol) {
  const history = payload?.history;
  if (!history || !Array.isArray(history.prices) || !Array.isArray(history.times)) {
    throw new Error(payload?.error?.message || "A Deriv não devolveu um histórico válido.");
  }
  const rawPipSize = Number(history.pip_size ?? payload?.tick?.pip_size);
  // Deriv's pip_size is commonly a decimal-place count (e.g. 2 or 4),
  // while this app stores the actual price increment (e.g. 0.01 or 0.0001).
  const pipSize = Number.isFinite(rawPipSize) && rawPipSize > 0
    ? (rawPipSize >= 1 ? 10 ** (-Math.min(10, Math.round(rawPipSize))) : rawPipSize)
    : null;
  const rows = history.prices.map((rawPrice, i) => {
    const priceText = String(rawPrice);
    const price = Number(rawPrice);
    const epoch = Number(history.times[i]);
    const inferredPip = Number.isFinite(pipSize) && pipSize > 0 ? pipSize : inferPipSize(priceText);
    const digit = digitFor(priceText, inferredPip);
    return {
      index: i,
      epoch: Number.isFinite(epoch) ? epoch : null,
      symbol,
      price,
      price_text: priceText,
      pip_size: Number.isFinite(inferredPip) && inferredPip > 0 ? inferredPip : null,
      digit,
      parity: digit % 2 === 0 ? "even" : "odd"
    };
  }).filter(t => Number.isFinite(t.price));
  if (rows.length < 2) throw new Error("A Deriv devolveu menos de 2 ticks válidos.");
  return rows;
}
function renderPreview() {
  $("previewBody").innerHTML = ticks.slice(0, 25).map((t,i) => `<tr>
    <td>${i+1}</td><td>${escapeHtml(t.epoch == null ? "—" : new Date(t.epoch*1000).toLocaleString())}</td><td>${escapeHtml(t.symbol || "—")}</td>
    <td>${escapeHtml(t.price_text ?? t.price)}</td><td><span class="digit-badge">${t.digit}</span></td>
    <td class="${t.parity}">${t.parity === "even" ? "Par" : "Ímpar"}</td></tr>`).join("");
}
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
async function apiPost(path, body) {
  const r = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || "A API devolveu um erro.");
  return data;
}
function fmt(v, digits=4) { return v === null || v === undefined ? "—" : typeof v === "number" ? v.toLocaleString("pt-PT",{maximumFractionDigits:digits}) : v; }
function metric(label, value, note="") { return `<div class="metric"><span>${label}</span><strong>${value}</strong>${note?`<small>${note}</small>`:""}</div>`; }

function requestDerivHistory(symbol, count, appId) {
  return new Promise((resolve, reject) => {
    let socket;
    let finished = false;
    const timer = setTimeout(() => finish(new Error("Tempo limite ao contactar a Deriv. Tenta novamente.")), 20000);
    function finish(error, result) {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      try { if (socket && socket.readyState <= 1) socket.close(); } catch {}
      error ? reject(error) : resolve(result);
    }
    try {
      socket = new WebSocket(`wss://ws.derivws.com/websockets/v3?app_id=${encodeURIComponent(appId)}`);
    } catch {
      finish(new Error("Não foi possível abrir WebSocket. Confirma a ligação à internet e o App ID."));
      return;
    }
    socket.addEventListener("open", () => {
      socket.send(JSON.stringify({
        ticks_history: symbol,
        count,
        end: "latest",
        style: "ticks",
        adjust_start_time: 1
      }));
    });
    socket.addEventListener("message", event => {
      let data;
      try { data = JSON.parse(event.data); } catch { return; }
      if (data.error) {
        finish(new Error(data.error.message || "Erro devolvido pela Deriv."));
        return;
      }
      if (data.msg_type === "history" || data.history) finish(null, data);
    });
    socket.addEventListener("error", () => finish(new Error("Falha na ligação WebSocket à Deriv. Verifica a rede ou tenta outro App ID.")));
    socket.addEventListener("close", () => {
      if (!finished) finish(new Error("A ligação à Deriv foi encerrada antes de receber o histórico."));
    });
  });
}

$("fetchHistory").addEventListener("click", async () => {
  const button = $("fetchHistory");
  const symbol = $("symbol").value;
  const count = Number($("historyCount").value);
  const appId = Number($("appId").value);
  if (!Number.isInteger(appId) || appId < 1) { toast("Introduz um App ID válido."); return; }
  button.disabled = true; button.textContent = "A pedir dados à Deriv...";
  $("connectionNote").textContent = `A solicitar ${count.toLocaleString()} ticks de ${symbol} diretamente à Deriv...`;
  try {
    const payload = await requestDerivHistory(symbol, count, appId);
    const received = normalizeDerivHistory(payload, symbol);
    ticks = received;
    currentSymbol = symbol;
    filename = `deriv-${symbol}-${received.length}-ticks`;
    $("connectionNote").textContent = `Histórico recebido diretamente da Deriv. ${received.length.toLocaleString()} ticks disponíveis para análise, backtest e exportação.`;
    $("analysisResult").className = "result-area empty";
    $("analysisResult").textContent = "Histórico carregado. Executa a análise estatística.";
    $("backtestResult").className = "result-area empty";
    $("backtestResult").textContent = "Histórico carregado. Configura a regra e executa o backtest.";
    setReady();
    toast(`Carregados ${received.length.toLocaleString()} ticks de ${symbol}.`);
  } catch (e) {
    $("connectionNote").textContent = "Não foi possível carregar o histórico. Confirma a ligação e tenta novamente.";
    toast(e.message || "Falha ao carregar o histórico.");
  } finally {
    button.disabled = false; button.textContent = "Carregar histórico da Deriv";
  }
});

$("analyzeBtn").addEventListener("click", async () => {
  const button = $("analyzeBtn"); button.disabled = true; button.textContent = "A analisar...";
  try {
    const data = await apiPost("/api/analyze", {ticks});
    const s = data.summary;
    const digitBars = data.digit_distribution.map(d => `<div class="bar-row"><b>${d.digit}</b><div class="bar-track"><div class="bar-fill" style="width:${d.frequency*100}%"></div></div><span class="bar-value">${(d.frequency*100).toFixed(1)}%</span></div>`).join("");
    const parity = data.parity_distribution.map(d => `${d.parity === "even" ? "Pares" : "Ímpares"}: ${(d.frequency*100).toFixed(2)}%`).join(" · ");
    const conditional = data.conditional_parity.map(d => `<tr><td>${d.sequence_length}</td><td>${d.samples}</td><td>${d.next_even_probability == null ? "—" : (d.next_even_probability*100).toFixed(1)+"%"}</td><td>${d.next_odd_probability == null ? "—" : (d.next_odd_probability*100).toFixed(1)+"%"}</td></tr>`).join("");
    $("analysisResult").className = "result-area";
    $("analysisResult").innerHTML = `<div class="metric-grid">
      ${metric("Ticks analisados",fmt(s.ticks,0))}${metric("Variação líquida",fmt(s.net_change,8),`${fmt(s.first_price,8)} → ${fmt(s.last_price,8)}`)}
      ${metric("Autocorrelação retornos (lag 1)",fmt(s.price_return_autocorrelation_lag1,4))}${metric("Maior sequência par/ímpar",fmt(s.max_same_parity_run,0))}
    </div><div class="result-title">Distribuição dos últimos dígitos</div>${digitBars}
    <div class="result-title">Paridade</div><p class="panel-description">${parity}</p>
    <div class="result-title">Probabilidade observada após sequência uniforme</div><div class="table-scroll"><table><thead><tr><th>N</th><th>Amostras</th><th>Próximo par</th><th>Próximo ímpar</th></tr></thead><tbody>${conditional}</tbody></table></div>
    <div class="warning">${data.notes.map(escapeHtml).join("<br>")}</div>`;
  } catch(e) { toast(e.message); }
  finally { button.disabled = ticks.length < 2; button.textContent = "Executar análise"; }
});
$("backtestBtn").addEventListener("click", async () => {
  const button = $("backtestBtn"); button.disabled = true; button.textContent = "A testar...";
  try {
    const data = await apiPost("/api/backtest", {
      ticks, sequence_length:Number($("seqLength").value), stake:Number($("stake").value),
      payout:Number($("payout").value), mode:$("mode").value
    });
    const labels = {train_60_percent:"Treino · primeiros 60%",validation_20_percent:"Validação · 20% seguintes",test_20_percent:"Teste final · últimos 20%",full_sample:"Amostra completa"};
    $("backtestResult").className = "result-area";
    $("backtestResult").innerHTML = `<div class="segments">${Object.entries(data.segments).map(([key,s])=>`<div class="segment"><div class="segment-head">${labels[key]}<span>${s.trades} operações</span></div><div class="segment-stats"><div>Taxa de vitória<b>${s.win_rate == null ? "—" : (s.win_rate*100).toFixed(2)+"%"}</b></div><div>P/L estimado<b class="${s.pnl >= 0 ? "even":"odd"}">${fmt(s.pnl,4)}</b></div><div>Drawdown máximo<b>${fmt(s.max_drawdown,4)}</b></div><div>Vitórias / derrotas<b>${s.wins} / ${s.losses}</b></div><div>Maior série de perdas<b>${s.max_losing_streak}</b></div><div>IC 95% da taxa<b>${s.wilson_95_ci ? (s.wilson_95_ci[0]*100).toFixed(1)+"–"+(s.wilson_95_ci[1]*100).toFixed(1)+"%" : "—"}</b></div></div></div>`).join("")}</div><div class="warning">${escapeHtml(data.warning)}</div><button class="button secondary full" id="exportTrades">Exportar registo completo do backtest (JSON)</button>`;
    $("exportTrades").addEventListener("click",()=>downloadBlob(JSON.stringify(data,null,2),`${filename}-backtest.json`,"application/json"));
  } catch(e) { toast(e.message); }
  finally { button.disabled = ticks.length < 10; button.textContent = "Executar backtest"; }
});
function downloadBlob(content, name, type) {
  const blob = new Blob([content],{type}); const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href=url; a.download=name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("exportJson").addEventListener("click",()=>downloadBlob(JSON.stringify({
  source:"Deriv WebSocket API", symbol:currentSymbol, count:ticks.length,
  fetched_at:new Date().toISOString(), ticks
},null,2),`${filename}.json`,"application/json"));
$("exportCsv").addEventListener("click",()=>{
  const keys=["index","epoch","symbol","price_text","price","pip_size","digit","parity"];
  const csv=[keys.join(","),...ticks.map(t=>keys.map(k=>`"${String(t[k] ?? "").replace(/"/g,'""')}"`).join(","))].join("\r\n");
  downloadBlob(csv,`${filename}.csv`,"text/csv;charset=utf-8");
});
