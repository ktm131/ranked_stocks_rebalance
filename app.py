import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date

def fmt(x):
    return f"{x:.2f}" if isinstance(x, (int, float, np.floating)) else "—"

# ==================================================
# KONFIGURACJA STRONY
# ==================================================

st.set_page_config(
    page_title="Fundamental + Momentum Strategy",
    layout="wide"
)

st.title("📊 Fundamental + Momentum – Stock Selector")

# ==================================================
# PARAMETRY STRATEGII
# ==================================================

N_STOCKS = 15
MOM_LOOKBACK = 126       # 6 miesięcy
MIN_WEEKS = 210          # bezpieczeństwo dla EMA200
CACHE_TTL = 600          # 10 minut

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

# ==================================================
# CACHE: FILTR RYNKU
# ==================================================

@st.cache_data(ttl=CACHE_TTL)
def load_market_filter():
    spy = yf.download(
        "SPY",
        period="10y",
        auto_adjust=True,
        progress=False
    )["Close"]

    weekly = spy.resample("W-FRI").last()
    ema200 = weekly.ewm(span=200).mean()

    return weekly, ema200

# ==================================================
# CACHE: CENY AKCJI
# ==================================================

@st.cache_data(ttl=CACHE_TTL)
def load_prices(tickers):
    prices = yf.download(
        tickers,
        period="2y",
        auto_adjust=True,
        progress=False
    )["Close"]

    return prices.dropna(axis=1)

# ==================================================
# CACHE: FUNDAMENTY
# ==================================================

@st.cache_data(ttl=CACHE_TTL)
def load_fundamentals(tickers):
    rows = []

    for t in tickers:
        try:
            info = yf.Ticker(t).info

            rows.append({
                "Ticker": t,
                "ROE": info.get("returnOnEquity", np.nan),
                "FCF": info.get("freeCashflow", np.nan),
                "MarketCap": info.get("marketCap", np.nan),
                "Rev_Growth": info.get("revenueGrowth", np.nan),
                "EPS_Growth": info.get("earningsGrowth", np.nan),
            })
        except:
            continue

    df = pd.DataFrame(rows)
    df["FCF_Yield"] = df["FCF"] / df["MarketCap"]

    return df

# ==================================================
# FILTR RYNKU – RISK ON / OFF
# ==================================================

weekly_spy, ema200 = load_market_filter()

if len(weekly_spy) < MIN_WEEKS:
    st.error("❌ Za mało danych do obliczenia EMA200 (weekly)")
    st.stop()

spy_last = weekly_spy.dropna().iloc[-1] if not weekly_spy.dropna().empty else None
ema_last = ema200.dropna().iloc[-1] if not ema200.dropna().empty else None

if spy_last is None or ema_last is None:
    st.error("❌ Brak aktualnych danych SPY – spróbuj odświeżyć stronę za kilka minut.")
    st.stop()

risk_on = bool(float(spy_last) >= float(ema_last))

c1, c2, c3 = st.columns(3)
c1.metric("SPY (weekly)", fmt(spy_last))
c2.metric("EMA200 (weekly)", fmt(ema_last))
c3.metric("Market Regime", "RISK ON 🟢" if risk_on else "RISK OFF 🔴")

st.divider()

# ==================================================
# JEŚLI RISK OFF → STOP
# ==================================================

if not risk_on:
    st.warning("Strategia aktualnie NIE posiada ekspozycji na akcje.")
    st.caption(f"Stan na: {date.today().isoformat()}")
    st.stop()

# ==================================================
# MOMENTUM
# ==================================================

prices = load_prices(TICKERS)

momentum = prices.iloc[-1] / prices.iloc[-MOM_LOOKBACK] - 1

# ==================================================
# FUNDAMENTY
# ==================================================

fund = load_fundamentals(list(prices.columns))

df = fund.merge(
    momentum.rename("Momentum"),
    left_on="Ticker",
    right_index=True,
    how="inner"
)

# ==================================================
# FILTRY JAKOŚCIOWE
# ==================================================

df = df[
    (df["ROE"] > 0.10) &
    (df["FCF_Yield"] > 0) &
    (df["Momentum"] > 0)
]

# ==================================================
# SCORE
# ==================================================

df["Score"] = (
    df["ROE"].rank(pct=True) * 0.20 +
    df["FCF_Yield"].rank(pct=True) * 0.20 +
    df["Rev_Growth"].rank(pct=True) * 0.10 +
    df["EPS_Growth"].rank(pct=True) * 0.10 +
    df["Momentum"].rank(pct=True) * 0.40
)

df = df.sort_values("Score", ascending=False).head(N_STOCKS)

# ==================================================
# WYNIK
# ==================================================

st.subheader("🏆 Aktualne spółki w strategii")

st.dataframe(
    df[[
        "Ticker","Score","Momentum",
        "ROE","FCF_Yield","Rev_Growth","EPS_Growth"
    ]].style.format({
        "Score": "{:.3f}",
        "Momentum": "{:.2%}",
        "ROE": "{:.2%}",
        "FCF_Yield": "{:.2%}",
        "Rev_Growth": "{:.2%}",
        "EPS_Growth": "{:.2%}",
    }),
    use_container_width=True
)

st.caption(f"Stan na: {date.today().isoformat()}")

if st.sidebar.button("🔄 Wyczyść cache"):
    st.cache_data.clear()
    st.experimental_rerun()

