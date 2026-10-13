import numpy as np
import pandas as pd

def chronological_split(df, train_ratio=.60, validation_ratio=.20):
    n=len(df); a=int(n*train_ratio); b=int(n*(train_ratio+validation_ratio))
    return df.iloc[:a].copy(), df.iloc[a:b].copy(), df.iloc[b:].copy()

def run_parity_backtest(df, sequence_length=4, trigger_odd=True, stake=1.0, payout_profit_per_stake=.9):
    digits=df["digit"].astype(int).to_numpy()
    parity=digits%2
    rows=[]; equity=0.0; peak=0.0; max_dd=0.0; loss_streak=0; max_loss_streak=0
    # Signal uses only prior ticks; the outcome is the next tick's digit.
    for i in range(sequence_length, len(parity)):
        prior=parity[i-sequence_length:i]
        expected=1 if trigger_odd else 0
        if not np.all(prior==expected): continue
        predicted=0 if trigger_odd else 1
        win=parity[i]==predicted
        pnl=stake*payout_profit_per_stake if win else -stake
        equity += pnl; peak=max(peak,equity); max_dd=max(max_dd,peak-equity)
        loss_streak=0 if win else loss_streak+1
        max_loss_streak=max(max_loss_streak,loss_streak)
        rows.append({"signal_index":i-1,"outcome_index":i,"sequence":"odd" if trigger_odd else "even",
                     "contract":"EVEN" if predicted==0 else "ODD","observed_digit":int(digits[i]),
                     "win":bool(win),"stake":float(stake),"pnl":float(pnl),"equity":float(equity)})
    trades=pd.DataFrame(rows)
    n=len(trades); wins=int(trades["win"].sum()) if n else 0
    gains=float(trades.loc[trades.pnl>0,"pnl"].sum()) if n else 0.0
    losses=abs(float(trades.loc[trades.pnl<0,"pnl"].sum())) if n else 0.0
    p=wins/n if n else 0
    # Wilson interval for observed win rate (95%).
    z=1.96
    denom=1+z*z/n if n else 1
    center=(p+z*z/(2*n))/denom if n else 0
    margin=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/denom if n else 0
    result={"trades":n,"wins":wins,"losses":n-wins,"win_rate":p*100,
            "win_rate_95ci_low":max(0,center-margin)*100 if n else None,
            "win_rate_95ci_high":min(1,center+margin)*100 if n else None,
            "net_profit":float(trades.pnl.sum()) if n else 0.0,
            "expected_value_per_trade":float(trades.pnl.mean()) if n else 0.0,
            "profit_factor":gains/losses if losses else (float("inf") if gains else 0.0),
            "max_drawdown":max_dd,"max_losing_streak":max_loss_streak,
            "payout_profit_per_stake_assumption":float(payout_profit_per_stake)}
    return result,trades
