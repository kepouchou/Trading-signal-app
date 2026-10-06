import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf


TZ = ZoneInfo("America/New_York")


def now_local():
    return datetime.now(TZ)


def fmt_time(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


def latest_price(ticker):
    data = yf.Ticker(ticker).history(
        period="1d",
        interval="1m",
        prepost=True,
    )

    
return {
    "ticker": ticker,
    "price": float(latest["Close"]),
    "rsi": float(latest["RSI"]),
    "macd": float(latest["MACD"]),
    "macd_signal": float(latest["MACD_SIGNAL"]),
    "bullish": bullish,
    "bearish": bearish,
    "bias": bias,
    "chart": clean[
        [
            "Close",
            "SMA5",
            "SMA10",
            "BB_MIDDLE",
        ]
    ],
}

def analyze(ticker):
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

    clean = data.dropna()

    if clean.empty:
        return None

    latest = clean.iloc[-1]

    bullish = 0

    if latest["SMA5"] > latest["SMA10"]:
        bullish += 25

    if latest["RSI"] > 50:
        bullish += 25

    if latest["MACD"] > latest["MACD_SIGNAL"]:
        bullish += 25

    if latest["Close"] > latest["BB_MIDDLE"]:
        bullish += 25

    bearish = 100 - bullish

    if bullish >= 75:
        bias = "BULLISH"

    elif bearish >= 75:
        bias = "BEARISH"

    else:
        bias = "NEUTRAL"

    return {
        "ticker": ticker,
        "price": float(latest["Close"]),
        "rsi":
