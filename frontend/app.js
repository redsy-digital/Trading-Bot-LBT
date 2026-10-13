let ticks = [];
let filename = "ticks";
const $ = (id) => document.getElementById(id);

async function checkApi() {
  try {
    const r = await fetch("/api/health");
    if (!r.ok) throw new Error();
    $("apiStatus").textContent = "API ligada";
    document.querySelector(".status").classList.add("online");
  } catch {
    $("apiStatus").textContent = "API indisponível";
    toast("Inicia o servidor Python para usar análise e backtest.");
  }
}
checkApi();

function toast(message) {
  const el = $("toast"); el.textContent = message; el.classList.add("show");
  clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove("show"), 3000);
}
function setReady() {
  const ready = ticks.length >= 2;
  ["analyzeBtn","exportJson","exportCsv"].forEach(id => $(id).disabled = !ready);
  $("backtestBtn").disabled = ticks.length < 10;
  $("fileInfo").textContent = `${filename} · ${ticks.length.toLocaleString()} ticks válidos`;
  $("tickCount").textContent = `${ticks.length.toLocaleString()} ticks`;
  $("previewWrap").classList.toggle("hidden", !ready);
  renderPreview();
}
function digitFor(price, pipSize) {
  let decimals;
  if (Number.isFinite(pipSize) && pipSize > 0) decimals = Math.max(0, Math.min(10, Math.round(-Math.log10(pipSize))));
  else {
    const s = String(Number(price));
    decimals = s.includes(".") ? s.split(".")[1].length : 0;
  }
  return Math.abs(Math.round(Number(price) * 10 ** decimals)) % 10;
}
function normalizeRows(raw) {
  if (raw && !Array.isArray(raw)) {
    if (raw.history && Array.isArray(raw.history.prices)) {
      raw = raw.history.prices.map((price, i) => ({
        price, epoch: raw.history.times?.[i] ?? null,
        symbol: raw.echo_req?.ticks_history ?? ""
      }));
    } else raw = raw.ticks ?? raw.data ?? raw.prices ?? [];
  }
  if (!Array.isArray(raw)) throw new Error("Formato inválido: esperava uma lista de ticks.");
  const result = [];
  raw.forEach((item, index) => {
    let row = typeof item === "object" && item !== null ? item : {price:item};
    const price = Number(row.price ?? row.quote ?? row.close ?? row.value ?? row.tick);
    if (!Number.isFinite(price)) return;
    const epoch = row.epoch ?? row.time ?? row.timestamp ?? row.date ?? null;
    const pipSize = Number(row.pip_size);
    const digit = digitFor(price, Number.isFinite(pipSize) && pipSize > 0 ? pipSize : null);
    result.push({
      index, epoch, symbol: row.symbol ?? row.underlying ?? "",
      price, pip_size: Number.isFinite(pipSize) && pipSize > 0 ? pipSize : null,
      digit, parity: digit % 2 === 0 ? "even" : "odd"
    });
  });
  if (!result.length) throw new Error("Não foram encontrados preços válidos no ficheiro.");
  return result;
}
async function readFile(file) {
  filename = file.name.replace(/\.[^.]+$/, "") || "ticks";
  const content = await file.text();
  let raw;
  if (file.name.toLowerCase().endsWith(".csv")) raw = parseCsv(content);
  else raw = JSON.parse(content);
  ticks = normalizeRows(raw);
  setReady();
  toast(`Carregados ${ticks.length} ticks.`);
}
function parseCsv(text) {
  const lines = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  if (lines.length < 2) throw new Error("CSV vazio ou sem linhas de dados.");
  const headers = lines[0].split(",").map(x => x.trim().replace(/^"|"$/g,"").toLowerCase());
  return lines.slice(1).map(line => {
    const values = line.split(",").map(x => x.trim().replace(/^"|"$/g,""));
    return Object.fromEntries(headers.map((h,i) => [h, values[i]]));
  });
}
function renderPreview() {
  $("previewBody").innerHTML = ticks.slice(0, 20).map((t,i) => `<tr>
    <td>${i+1}</td><td>${escapeHtml(t.epoch ?? "—")}</td><td>${escapeHtml(t.symbol || "—")}</td>
    <td>${t.price}</td><td><span class="digit-badge">${t.digit}</span></td>
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
      ${metric("Ticks válidos",fmt(s.ticks,0))}${metric("Variação líquida",fmt(s.net_change,8),`${fmt(s.first_price,8)} → ${fmt(s.last_price,8)}`)}
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
  const a = document.createElement("a"); a.href=url; a.download=name; a.click(); URL.revokeObjectURL(url);
}
$("exportJson").addEventListener("click",()=>downloadBlob(JSON.stringify({source:filename,count:ticks.length,ticks},null,2),`${filename}-normalized.json`,"application/json"));
$("exportCsv").addEventListener("click",()=>{
  const keys=["index","epoch","symbol","price","pip_size","digit","parity"];
  const csv=[keys.join(","),...ticks.map(t=>keys.map(k=>`"${String(t[k] ?? "").replace(/"/g,'""')}"`).join(","))].join("\n");
  downloadBlob(csv,`${filename}-normalized.csv`,"text/csv;charset=utf-8");
});
$("fileInput").addEventListener("change", async e => {
  const file=e.target.files?.[0]; if(!file)return;
  try { await readFile(file); } catch(err) { toast(err.message || "Não foi possível ler o ficheiro."); }
  e.target.value="";
});
const dz=$("dropzone");
dz.addEventListener("dragover",e=>{e.preventDefault();dz.classList.add("dragging")});
dz.addEventListener("dragleave",()=>dz.classList.remove("dragging"));
dz.addEventListener("drop",async e=>{e.preventDefault();dz.classList.remove("dragging");const file=e.dataTransfer.files?.[0];if(file){try{await readFile(file)}catch(err){toast(err.message||"Ficheiro inválido.")}}});
$("loadDemo").addEventListener("click",()=>{
  let price=1000.1234;
  ticks=Array.from({length:500},(_,i)=>{
    // Deterministic synthetic sample, explicitly not live market data.
    price += (((i*7)%11)-5)*0.0001;
    const p=Number(price.toFixed(4));
    const digit=digitFor(p,0.0001);
    return {index:i,epoch:1700000000+i,symbol:"DEMO_SYNTHETIC",price:p,pip_size:0.0001,digit,parity:digit%2===0?"even":"odd"};
  });
  filename="synthetic-demo"; setReady(); toast("Demonstração sintética carregada.");
});
