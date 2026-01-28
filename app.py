import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date

st.set_page_config(page_title="Stock Strategy Dashboard", layout="wide")

# =============================
# PARAMETRY
# =============================

N_STOCKS = 15
LOOKBACK_MOM = 126
START_DATE = "2012-01-01"

TICKERS = [
    "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA",
    "JPM","V","MA","HD","UNH","JNJ","PG","KO","PEP",
    "XOM","CVX","ABBV","MRK","COST","AVGO","ADBE",
    "ADSK","INTU","NOW","SNPS","CDNS","TEAM","MDB","DDOG","NET",
    "AMAT","LRCX","KLAC","MCHP","ON","MPWR","QRVO","SWKS",
    "REGN","VRTX","BIIB","IDXX","IQV","EW","ISRG","DXCM",
    "ROK","PH","ITW","EMR","ETN","AME","FAST","GWW",
    "POOL","ULTA","ORLY","AZO","DPZ","SBUX","LOW","TJX",
    "ICE","CME","SPGI","MCO","MSCI","FIS","FICO","NDAQ"
]

st.title("📊 Fundamental + Momentum Strategy")

# =============================
# FILTR RYNKU
# =============================

spy = yf.download("SPY", start=START_DATE, auto_adjust=True, progress=False)["Close"]
weekly_spy = spy.resample("W-FRI").last()
ema200 = weekly_spy.ewm(span=200).mean()

risk_on = weekly_spy.iloc[-1] >= ema200.iloc[-1]

col1, col2 = st.columns(2)

with col1:
    st.metric("SPY (weekly)", f"{weekly_spy.iloc[-1]:.2f}")

with col2:
    st.metric("EMA200 (weekly)", f"{ema200.iloc[-1]:.2f}")

st.divider()

# =============================
# STATUS RYNKU
# =============================

if risk_on:
    st.success("🟢 RISK ON — strategia MA ekspozycję na akcje")
else:
    st.error("🔴 RISK OFF — strategia BEZ ekspozycji (cash)")

# =============================
# JEŚLI RISK OFF → KONIEC
# =============================

if not risk_on:
    st.stop()

# =============================
# DANE CENOWE
# =============================

prices = yf.download(
    TICKERS,
    period="2y",
    auto_adjust=True,
    progress=False
)["Close"]

prices = prices.dropna(axis=1)
momentum = prices.iloc[-1] / prices.iloc[-LOOKBACK_MOM] - 1

# =============================
# FUNDAMENTY
# =============================

rows = []

with st.spinner("Pobieranie danych fundamentalnych..."):
    for t in prices.columns:
        try:
            info = yf.Ticker(t).info

            roe = info.get("returnOnEquity", np.nan)
            fcf = info.get("freeCashflow", np.nan)
            mkt = info.get("marketCap", np.nan)
            rev = info.get("revenueGrowth", np.nan)
            eps = info.get("earningsGrowth", np.nan)

            fcf_yield = fcf / mkt if fcf and mkt else np.nan

            rows.append([t, roe, fcf_yield, rev, eps, momentum[t]])

        except:
            continue

df = pd.DataFrame(
    rows,
    columns=["Ticker","ROE","FCF_Yield","Rev_Growth","EPS_Growth","Momentum"]
)

# =============================
# FILTRY
# =============================

df = df[
    (df["ROE"] > 0.10) &
    (df["FCF_Yield"] > 0) &
    (df["Momentum"] > 0)
]

# =============================
# SCORE
# =============================

df["Score"] = (
    df["ROE"].rank(pct=True) * 0.20 +
    df["FCF_Yield"].rank(pct=True) * 0.20 +
    df["Rev_Growth"].rank(pct=True) * 0.10 +
    df["EPS_Growth"].rank(pct=True) * 0.10 +
    df["Momentum"].rank(pct=True) * 0.40
)

df = df.sort_values("Score", ascending=False).head(N_STOCKS)

# =============================
# WYNIKI
# =============================

st.subheader("🏆 Aktualne spółki w portfelu")

st.dataframe(
    df.style.format({
        "ROE": "{:.2%}",
        "FCF_Yield": "{:.2%}",
        "Rev_Growth": "{:.2%}",
        "EPS_Growth": "{:.2%}",
        "Momentum": "{:.2%}",
        "Score": "{:.3f}"
    }),
    use_container_width=True
)

st.caption(f"Stan na: {date.today().isoformat()}")
