import numpy as np
import pandas as pd

def _longest_run(values, target):
    best = run = 0
    for x in values:
        if x == target:
            run += 1; best = max(best, run)
        else: run = 0
    return best

def analyze_ticks(df):
    q = df["quote"].astype(float).to_numpy()
    ret = np.diff(q)
    digits = df["digit"].astype(int).to_numpy()
    parity = digits % 2
    corr = float(np.corrcoef(ret[:-1], ret[1:])[0,1]) if len(ret) > 2 and np.std(ret[:-1]) and np.std(ret[1:]) else np.nan
    counts = {i:int((digits == i).sum()) for i in range(10)}
    return {"up_pct":float((ret>0).mean()*100) if len(ret) else 0.0,
            "down_pct":float((ret<0).mean()*100) if len(ret) else 0.0,
            "flat_pct":float((ret==0).mean()*100) if len(ret) else 0.0,
            "even_pct":float((parity==0).mean()*100) if len(parity) else 0.0,
            "odd_pct":float((parity==1).mean()*100) if len(parity) else 0.0,
            "digit_counts":counts,
            "longest_even_run":_longest_run(parity,0),
            "longest_odd_run":_longest_run(parity,1),
            "return_autocorr_lag1":corr,
            "mean_return":float(np.mean(ret)) if len(ret) else 0.0,
            "std_return":float(np.std(ret, ddof=1)) if len(ret)>1 else 0.0,
            "median_abs_return":float(np.median(np.abs(ret))) if len(ret) else 0.0}

def moving_average_reversion(df, window=20, buckets=5):
    q = df["quote"].astype(float)
    ma = q.rolling(window).mean()
    dev = q - ma
    future = q.shift(-1) - q
    valid = pd.DataFrame({"deviation":dev, "next_delta":future}).dropna()
    if len(valid) < 10: return pd.DataFrame()
    scale = valid["deviation"].abs().quantile(0.8)
    if not np.isfinite(scale) or scale == 0: scale = valid["deviation"].abs().max()
    if not np.isfinite(scale) or scale == 0: return pd.DataFrame()
    valid["bucket"] = pd.cut(valid["deviation"], bins=[-np.inf,-scale,-scale/2,scale/2,scale,np.inf],
                             labels=["Abaixo forte","Abaixo moderado","Perto da média","Acima moderado","Acima forte"], duplicates="drop")
    rows=[]
    for name, g in valid.groupby("bucket", observed=False):
        if len(g)==0: continue
        rows.append({"Zona de desvio":str(name),"Amostra":int(len(g)),
                     "Desvio médio":float(g["deviation"].mean()),
                     "Variação seguinte média":float(g["next_delta"].mean()),
                     "Seguinte subiu (%)":float((g["next_delta"]>0).mean()*100),
                     "Seguinte desceu (%)":float((g["next_delta"]<0).mean()*100)})
    return pd.DataFrame(rows)

def parity_conditionals(df, n=4):
    p = (df["digit"].astype(int).to_numpy() % 2) # 0 even, 1 odd
    rows=[]
    base_even=float((p==0).mean()*100) if len(p) else 0
    base_odd=float((p==1).mean()*100) if len(p) else 0
    for prev, label in [(0,"Pares"),(1,"Ímpares")]:
        idx=[]
        for i in range(n, len(p)):
            if np.all(p[i-n:i] == prev): idx.append(i)
        outcomes=p[idx] if idx else np.array([],dtype=int)
        rows.append({"Sequência anterior":f"{n} {label.lower()}","Ocorrências":len(idx),
                     "Seguinte par (%)":float((outcomes==0).mean()*100) if len(idx) else np.nan,
                     "Seguinte ímpar (%)":float((outcomes==1).mean()*100) if len(idx) else np.nan,
                     "Base par (%)":base_even,"Base ímpar (%)":base_odd,
                     "Diferença vs base par (p.p.)":float((outcomes==0).mean()*100-base_even) if len(idx) else np.nan})
    return pd.DataFrame(rows)
