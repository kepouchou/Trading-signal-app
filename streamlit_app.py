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
    return dt.strftime("%I:%M:%S %p").lstrip("0")


def get_intraday_data(ticker):
    data = yf.Ticker(ticker).history(
        period="1d",
        interval="1m",
        prepost=True,
    )

    if data.empty:
        return None

    data = data.copy()
    data = data.dropna(subset=["Close"])

    if len(data) < 30:
        return None

    return data


def latest_price(ticker):
    data = get_intraday_data(ticker)

    if data is None or data.empty:
        return None

    return float(data["Close"].iloc[-1])


def analyze_short_term(ticker):
    data = get_intraday_data(ticker)

    if data is None:
        return None

    close = data["Close"]

    data["EMA5"] = close.ewm(
        span=5,
        adjust=False,
    ).mean()

    data["EMA10"] = close.ewm(
        span=10,
        adjust=False,
    ).mean()

    delta = close.diff()

    gain = (
        delta.clip(lower=0)
        .rolling(7)
        .mean()
    )

    loss = (
        -delta.clip(upper=0)
        .rolling(7)
        .mean()
    )

    rs = gain / loss.replace(0, float("nan"))

    data["RSI7"] = (
        100 - (100 / (1 + rs))
    )

    ema12 = close.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
    ).mean()

    data["MACD"] = ema12 - ema26

    data["MACD_SIGNAL"] = (
        data["MACD"]
        .ewm(
            span=9,
            adjust=False,
        )
        .mean()
    )

    data["MOMENTUM3"] = close.diff(3)

    clean = data.dropna(
        subset=[
            "EMA5",
            "EMA10",
            "RSI7",
            "MACD",
            "MACD_SIGNAL",
            "MOMENTUM3",
        ]
    )

    if clean.empty:
        return None

    latest = clean.iloc[-1]

    bullish_points = 0
    bearish_points = 0

    if latest["EMA5"] > latest["EMA10"]:
        bullish_points += 1

    elif latest["EMA5"] < latest["EMA10"]:
        bearish_points += 1

    if latest["RSI7"] >= 55:
    bullish_points += 1

elif latest["RSI7"] <= 45:
    bearish_points += 1

