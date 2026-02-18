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
    page_title="Pure Momentum Strategy",
    layout="wide"
)

st.title("📈 Pure Momentum – Stock Selector (MTL)")

# ==================================================
# PARAMETRY STRATEGII
# ==================================================

N_STOCKS = 15
MOM_LOOKBACK = 126       # 6 miesięcy
VOL_LOOKBACK = 63        # 3 miesiące (risk adjustment)
MIN_WEEKS = 210          # bezpieczeństwo dla EMA200
CACHE_TTL = 600          # 10 minut

TICKERS = [
        # ===== MEGA / BIG TECH =====
    "AAPL","MSFT","GOOGL","GOOG","AMZN","META","NVDA","TSLA",
    "AVGO","ORCL","CRM","IBM","INTC","AMD","QCOM","TXN","MU",
    "SHOP","PYPL","UBER","LYFT","SNOW","PLTR","RIVN",
    "LCID","ZM","DOCU","SPOT","ROKU","PINS","SNAP",


    # ===== FINANCIALS =====
    "JPM","BAC","WFC","C","GS","MS","BLK","SCHW",
    "V","MA","AXP","COF","PNC","USB","TFC","AIG","MET","PRU","ALL",
    "CB","TRV","AJG","WTW","MTB","FITB",


    # ===== HEALTHCARE =====
    "UNH","JNJ","PFE","MRK","ABBV","LLY","BMY","AMGN",
    "GILD","VRTX","REGN","ISRG","TMO","DHR","ABT","MDT",
    "CVS","CI","HCA","ZBH","EW","ILMN","BIIB",
    "MRNA","BNTX","DXCM","ALGN","IDXX","TECH",


    # ===== CONSUMER STAPLES =====
    "PG","KO","PEP","COST","WMT","TGT","CL","KMB","MDLZ",
    "KR","SYY","HSY","GIS","KHC","CPB","EL",
    "STZ","BF-B","TAP",


    # ===== CONSUMER DISCRETIONARY =====
    "HD","LOW","NKE","SBUX","MCD","BKNG","ABNB","TJX",
    "ROST","ORLY","AZO","ULTA","DPZ","EBAY","ETSY","W",
    "CHWY","BBY","BBWI","LEN","DHI","NVR","PHM",

    # ===== INDUSTRIALS =====
    "CAT","DE","HON","GE","RTX","LMT","NOC",
    "ETN","EMR","PH","ROK","ITW","FAST","GWW",
    "BA","GD","TDG","JCI","CARR","OTIS",
    "DAL","AAL","UAL","LUV",


    # ===== ENERGY =====
    "XOM","CVX","COP","SLB","EOG","MPC","VLO","OXY",
    "DVN","HAL","BKR","KMI","WMB",
    "PSX","FANG",


    # ===== MATERIALS =====
    "LIN","APD","ECL","SHW","FCX","NEM","DOW","RIO",
    "BHP","VALE","AA","NUE","STLD","MLM","VMC",


    # ===== REAL ESTATE =====
    "PLD","AMT","CCI","EQIX","PSA","O","SPG","DLR","WELL",
    "AVB","EQR","ESS","VICI","ARE",

    # ===== SOFTWARE / CLOUD =====
    "ADBE","INTU","NOW","SNPS","CDNS","ADSK",
    "TEAM","MDB","DDOG","NET","CRWD","ZS","OKTA",
    "PANW","FTNT","ESTC","AI",
    "PATH","HUBS","WDAY",


    # ===== SEMICONDUCTORS =====
    "AMAT","LRCX","KLAC","ASML","ON","MPWR","SWKS","QRVO",
    "NXPI","ADI","MCHP","TER","ENTG",
    "LSCC","COHR","IPGP",


    # ===== EXCHANGES / DATA =====
    "ICE","CME","SPGI","MCO","MSCI","NDAQ","FICO",

    # ===== TELECOM / MEDIA =====
    "T","VZ","TMUS","CMCSA","CHTR",
    "DIS","WBD"
]

# ==================================================
# CACHE: FILTR RYNKU (SPY WEEKLY)
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
# FILTR RYNKU – RISK ON / OFF
# ==================================================

weekly_spy, ema200 = load_market_filter()

if len(weekly_spy) < MIN_WEEKS:
    st.error("❌ Za mało danych do obliczenia EMA200 (weekly)")
    st.stop()

spy_last = weekly_spy.dropna().iloc[-1]
ema_last = ema200.dropna().iloc[-1]

risk_on = bool(float(spy_last) >= float(ema_last))

c1, c2, c3 = st.columns(3)
c1.metric("SPY (weekly)", fmt(spy_last))
c2.metric("EMA200 (weekly)", fmt(ema_last))
c3.metric("Market Regime", "RISK ON 🟢" if risk_on else "RISK OFF 🔴")

st.divider()

if not risk_on:
    st.warning("Strategia aktualnie NIE posiada ekspozycji na akcje.")
    st.caption(f"Stan na: {date.today().isoformat()}")
    st.stop()

# ==================================================
# MOMENTUM + VOLATILITY
# ==================================================

prices = load_prices(TICKERS)
returns = prices.pct_change()

momentum = prices.iloc[-1] / prices.iloc[-MOM_LOOKBACK] - 1
volatility = returns.rolling(VOL_LOOKBACK).std().iloc[-1]

df = pd.DataFrame({
    "Ticker": momentum.index,
    "Momentum": momentum.values,
    "Volatility": volatility.values
}).dropna()

# Absolute momentum filter
df = df[df["Momentum"] > 0]

# Risk-adjusted momentum score
df["Score"] = df["Momentum"] / df["Volatility"]

df = df.sort_values("Score", ascending=False).head(N_STOCKS)

# ==================================================
# WYNIK
# ==================================================

st.subheader("🏆 Aktualne spółki w strategii (Pure Momentum)")

st.dataframe(
    df[["Ticker","Score","Momentum","Volatility"]].style.format({
        "Score": "{:.3f}",
        "Momentum": "{:.2%}",
        "Volatility": "{:.2%}"
    }),
    use_container_width=True
)

st.caption(f"Stan na: {date.today().isoformat()}")

if st.sidebar.button("🔄 Wyczyść cache"):
    st.cache_data.clear()
    st.experimental_rerun()
