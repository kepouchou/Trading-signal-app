import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/New_York")


def local_now():
    return datetime.now(LOCAL_TZ)


def format_time(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


st.set_page_config(
    page_title="Paper Trading Signal App",
    page_icon="📈",
    layout="wide"
)

st.title("📈 My Paper Trading Signal App")

st.write(
    "Paper-testing and learning only. "
    "Bullish and Bearish scores show indicator alignment, "
    "not the probability of winning a trade."
)

if "signal_log" not in st.session_state:
    st.session_state.signal_log = []

if "observation_log" not in st.session_state:
    st.session_state.observation_log = []


def get_latest_price(ticker):
    stock = yf.Ticker(ticker)

    data = stock.history(
        period="1d",
        interval="1m",
        prepost=True
    )

    if data.empty:
        return None

    return float(data["Close"].iloc[-1])


def analyze_ticker(ticker):
    data = yf.Ticker(ticker).history(
        period="6mo"
    )

    if data.empty or len(data) < 30:
        return None

    close = data["Close"]

    data["SMA5"] = close.rolling(5).mean()
    data["SMA10"] = close.rolling(10).mean()

    delta = close.diff()

    gain = (
        delta.clip(lower=0)
        .rolling(14)
        .mean()
    )

    loss = (
        -delta.clip(upper=0)
        .rolling(14)
        .mean()
    )

    rs = gain / loss

    data["RSI"] = (
        100 - (100 / (1 + rs))
    )

    ema12 = close.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False
    ).mean()

    data["MACD"] = ema12 - ema26

    data["MACD_SIGNAL"] = (
        data["MACD"]
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    data["BB_MIDDLE"] = (
        close.rolling(20).mean()
    )

    clean_data = data.dropna()

    if clean_data.empty:
        return None

    latest = clean_data.iloc[-1]

    bullish_score = 0

    if latest["SMA5"] > latest["SMA10"]:
        bullish_score += 25

    if latest["RSI"] > 50:
        bullish_score += 25

    if latest["MACD"] > latest["MACD_SIGNAL"]:
        bullish_score += 25

    if latest["Close"] > latest["BB_MIDDLE"]:
        bullish_score += 25

    bearish_score = 100 - bullish_score

    if bullish_score >= 75:
        paper_bias = "PAPER BULLISH ALIGNMENT"

    elif bearish_score >= 75:
        paper_bias = "PAPER BEARISH ALIGNMENT"

    else:
        paper_bias = "MIXED / NEUTRAL"

    return {
        "ticker": ticker,
        "price": float(latest["Close"]),
        "rsi": float(latest["RSI"]),
        "macd": float(latest["MACD"]),
        "macd_signal": float(
            latest["MACD_SIGNAL"]
        ),
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "paper_bias": paper_bias,
        "chart_data": clean_data[
            [
                "Close",
                "SMA5",
                "SMA10",
                "BB_MIDDLE"
            ]
        ]
    }


def add_signal_log(result):
    st.session_state.signal_log.append({
        "Time": local_now().strftime(
            "%Y-%m-%d %I:%M:%S %p"
        ),
        "Ticker": result["ticker"],
        "Price": round(
            result["price"],
            2
        ),
        "RSI": round(
            result["rsi"],
            2
        ),
        "MACD": round(
            result["macd"],
            4
        ),
        "Bullish Score": result[
            "bullish_score"
        ],
        "Bearish Score": result[
            "bearish_score"
        ],
        "Paper Bias": result[
            "paper_bias"
        ]
    })


st.subheader("🔎 Check One Stock")

ticker = st.text_input(
    "Enter a stock ticker:",
    "AAPL",
    key="single_ticker"
).upper().strip()


if st.button("Check Signal"):
    try:
        result = analyze_ticker(ticker)

        if result is None:
            st.error(
                "Not enough market data was found."
            )

        else:
            st.subheader(
                f"{ticker} Paper Signal"
            )

            st
