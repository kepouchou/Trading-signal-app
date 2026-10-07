import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf


TZ = ZoneInfo("America/New_York")
MAX_FRESH_AGE_SECONDS = 180


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


def get_latest_sample(ticker):
    data = get_intraday_data(ticker)

    if data is None or data.empty:
        return None

    timestamp = data.index[-1]

    if getattr(timestamp, "tzinfo", None) is None:
        timestamp = timestamp.tz_localize(TZ)
    else:
        timestamp = timestamp.tz_convert(TZ)

    return {
        "price": float(data["Close"].iloc[-1]),
        "timestamp": timestamp.to_pydatetime(),
    }


def sample_age_seconds(sample_time):
    return max(
        0.0,
        (now_local() - sample_time).total_seconds(),
    )


def is_sample_fresh(sample_time):
    return (
        sample_age_seconds(sample_time)
        <= MAX_FRESH_AGE_SECONDS
    )


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

    rs = gain / loss.replace(
        0,
        float("nan"),
    )

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

    if latest["MACD"] > latest["MACD_SIGNAL"]:
        bullish_points += 1
    elif latest["MACD"] < latest["MACD_SIGNAL"]:
        bearish_points += 1

    if latest["MOMENTUM3"] > 0:
        bullish_points += 1
    elif latest["MOMENTUM3"] < 0:
        bearish_points += 1

    bullish_score = bullish_points * 25
    bearish_score = bearish_points * 25

    if (
        bullish_score >= 75
        and bullish_score > bearish_score
    ):
        bias = "BULLISH"
    elif (
        bearish_score >= 75
        and bearish_score > bullish_score
    ):
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return {
        "price": float(latest["Close"]),
        "rsi": float(latest["RSI7"]),
        "macd": float(latest["MACD"]),
        "macd_signal": float(
            latest["MACD_SIGNAL"]
        ),
        "momentum3": float(
            latest["MOMENTUM3"]
        ),
        "bullish": bullish_score,
        "bearish": bearish_score,
        "bias": bias,
        "chart": clean[
            [
                "Close",
                "EMA5",
                "EMA10",
            ]
        ],
    }


def evaluate_forecast(forecast, movement):
    if movement == "NO FRESH DATA":
        return "NO FRESH DATA"

    if forecast == "BULLISH":
        if movement == "UP":
            return "MATCH"
        if movement == "DOWN":
            return "MISS"
        return "FLAT"

    if forecast == "BEARISH":
        if movement == "DOWN":
            return "MATCH"
        if movement == "UP":
            return "MISS"
        return "FLAT"

    return "NEUTRAL"


st.set_page_config(
    page_title="Next-Minute Paper Forecast",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Next-Minute Paper Forecast")

st.caption(
    "Paper/demo testing only. This uses 1-minute Yahoo Finance "
    "stock data to estimate a short-term BULLISH, BEARISH, or "
    "NEUTRAL bias for the next observation minute. It is not a "
    "guaranteed prediction or a win probability."
)

if "forecast_log" not in st.session_state:
    st.session_state.forecast_log = []


st.subheader("🔎 Check Current Short-Term Bias")

ticker = st.text_input(
    "Stock ticker:",
    "MSFT",
    key="signal_ticker",
).upper().strip()

if st.button("Check Current Bias"):
    try:
        sample = get_latest_sample(ticker)
        result = analyze_short_term(ticker)

        if sample is None or result is None:
            st.error(
                "Not enough 1-minute market data was found."
            )

        elif not is_sample_fresh(sample["timestamp"]):
            st.warning(
                "⏸️ Market data is not live right now — test later."
            )

            st.write(
                "Latest Yahoo sample: "
                f"{fmt_time(sample['timestamp'])}"
            )

        else:
            st.metric(
                "Latest price",
                f"${sample['price']:.4f}",
            )

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "📈 Bullish Score",
                    f"{result['bullish']} / 100",
                )

            with col2:
                st.metric(
                    "📉 Bearish Score",
                    f"{result['bearish']} / 100",
                )

            if result["bias"] == "BULLISH":
                st.success(
                    "📈 Current paper bias: BULLISH"
                )

            elif result["bias"] == "BEARISH":
                st.warning(
                    "📉 Current paper bias: BEARISH"
                )

            else:
                st.info(
                    "⚖️ Current paper bias: NEUTRAL"
                )

            st.line_chart(
                result["chart"]
            )

    except Exception as exc:
        st.error(
            f"Signal error: {exc}"
        )


st.divider()

st.subheader("⏱️ Next 60-Second Forecast Test")

st.write(
    "Stage 1: observe for 60 seconds. "
    "Then the app calculates a forecast for the NEXT 60 seconds. "
    "Stage 2: wait another 60 seconds and automatically verify "
    "whether that forecast matched the actual direction."
)

forecast_ticker = st.text_input(
    "Ticker for forecast test:",
    "MSFT",
    key="forecast_ticker",
).upper().strip()

if st.button("Run Next 60-Second Forecast Test"):
    try:
        initial_sample = get_latest_sample(
            forecast_ticker
        )

        if initial_sample is None:
            st.error(
                "Could not get the initial market sample."
            )

        elif not is_sample_fresh(
            initial_sample["timestamp"]
        ):
            st.warning(
                "⏸️ Market data is not live right now — test later."
            )

        else:
            stage1_start = now_local()

            st.info(
                "Stage 1 started at "
                f"{fmt_time(stage1_start)}. "
                "Collecting 60 seconds of fresh data..."
            )

            with st.spinner(
                "Collecting the first 60 seconds..."
            ):
                time.sleep(60)

            forecast_sample = get_latest_sample(
                forecast_ticker
            )

            if forecast_sample is None:
                st.error(
                    "Could not get the forecast-time market sample."
                )

            elif (
                forecast_sample["timestamp"]
                <= initial_sample["timestamp"]
            ):
                st.warning(
                    "⏸️ NO FRESH DATA. No forecast was created."
                )

            else:
                analysis = analyze_short_term(
                    forecast_ticker
                )

                if analysis is None:
                    st.error(
                        "Could not calculate the short-term forecast."
                    )

                else:
                    forecast = analysis["bias"]
                    bullish = analysis["bullish"]
                    bearish = analysis["bearish"]

                    forecast_start_time = now_local()
                    forecast_start_data_time = (
                        forecast_sample["timestamp"]
                    )
                    forecast_start_price = (
                        forecast_sample["price"]
                    )

                    forecast_end_label = (
                        forecast_start_time
                        + timedelta(seconds=60)
                    )

                    st.subheader(
                        "🔮 Next 60-Second Forecast"
                    )

                    st.write(
                        "Forecast window: "
                        f"{fmt_time(forecast_start_time)} "
                        "→ "
                        f"{fmt_time(forecast_end_label)}"
                    )

                    st.write(
                        f"Forecast start price: "
                        f"${forecast_start_price:.4f}"
                    )

                    st.write(
                        f"Bullish score: "
                        f"{bullish} / 100"
                    )

                    st.write(
                        f"Bearish score: "
                        f"{bearish} / 100"
                    )

                    if forecast == "BULLISH":
                        st.success(
                            "📈 Forecast bias: BULLISH"
                        )

                    elif forecast == "BEARISH":
                        st.warning(
                            "📉 Forecast bias: BEARISH"
                        )

                    else:
                        st.info(
                            "⚖️ Forecast bias: NEUTRAL"
                        )

                    st.caption(
                        "Paper forecast only — not a trade instruction."
                    )

                    with st.spinner(
                        "Waiting 60 seconds to verify the forecast..."
                    ):
                        time.sleep(60)

                    verify_time = now_local()

                    end_sample = get_latest_sample(
                        forecast_ticker
                    )

                    if end_sample is None:
                        st.error(
                            "Could not get the verification market sample."
                        )

                    elif (
                        end_sample["timestamp"]
                        <= forecast_start_data_time
                    ):
                        movement = "NO FRESH DATA"
                        evaluation = "NO FRESH DATA"

                        st.info(
                            "⏸️ Verification result: NO FRESH DATA"
                        )

                    else:
                        forecast_end_price = (
                            end_sample["price"]
                        )

                        change = (
                            forecast_end_price
                            - forecast_start_price
                        )

                        if change > 0:
                            movement = "UP"

                        elif change < 0:
                            movement = "DOWN"

                        else:
                            movement = "FLAT"

                        evaluation = evaluate_forecast(
                            forecast,
                            movement,
                        )

                        st.subheader(
                            "✅ Forecast Verification"
                        )

                        st.write(
                            "Verification time: "
                            f"{fmt_time(verify_time)}"
                        )

                        st.write(
                            f"Forecast start: "
                            f"${forecast_start_price:.4f}"
                        )

                        st.write(
                            f"Verification price: "
                            f"${forecast_end_price:.4f}"
                        )

                        if movement == "UP":
                            st.success(
                                "📈 Actual movement: UP"
                            )

                        elif movement == "DOWN":
                            st.warning(
                                "📉 Actual movement: DOWN"
                            )

                        else:
                            st.info(
                                "➖ Actual movement: FLAT"
                            )

                        if evaluation == "MATCH":
                            st.success(
                                "✅ Forecast MATCHED."
                            )

                        elif evaluation == "MISS":
                            st.error(
                                "❌ Forecast MISSED."
                            )

                        elif evaluation == "FLAT":
                            st.info(
                                "➖ Flat result. Not counted."
                            )

                        else:
                            st.info(
                                "⚖️ Neutral forecast. Not counted."
                            )

                    end_data_time_text = None
                    end_price_for_log = None
                    change_for_log = None

                    if end_sample is not None:
                        end_data_time_text = (
                            end_sample["timestamp"].strftime(
                                "%Y-%m-%d %I:%M:%S %p"
                            )
                        )

                        end_price_for_log = round(
                            end_sample["price"],
                            4,
                        )

                        if (
                            end_sample["timestamp"]
                            > forecast_start_data_time
                        ):
                            change_for_log = round(
                                end_sample["price"]
                                - forecast_start_price,
                                4,
                            )

                    st.session_state.forecast_log.append(
                        {
                            "Ticker": forecast_ticker,
                            "Forecast Created": (
                                forecast_start_time.strftime(
                                    "%Y-%m-%d %I:%M:%S %p"
                                )
                            ),
                            "Forecast": forecast,
                            "Bullish": bullish,
                            "Bearish": bearish,
                            "Start Price": round(
                                forecast_start_price,
                                4,
                            ),
                            "End Data Time": end_data_time_text,
                            "End Price": end_price_for_log,
                            "Movement": movement,
                            "Change": change_for_log,
                            "Evaluation": evaluation,
                        }
                    )

    except Exception as exc:
        st.error(
            f"Forecast test error: {exc}"
        )


st.divider()

st.subheader("📊 Forecast Accuracy Tracker")

if st.session_state.forecast_log:
    forecast_df = pd.DataFrame(
        st.session_state.forecast_log
    )

    directional = forecast_df[
        forecast_df[
            "Evaluation"
        ].isin(
            [
                "MATCH",
                "MISS",
            ]
        )
    ]

    total = len(directional)

    matches = int(
        (
            directional["Evaluation"]
            == "MATCH"
        ).sum()
    )

    misses = int(
        (
            directional["Evaluation"]
            == "MISS"
        ).sum()
    )

    if total > 0:
        accuracy = (
            matches
            / total
            * 100
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Directional Forecasts",
                total,
            )

        with col2:
            st.metric(
                "Matches",
                matches,
            )

        with col3:
            st.metric(
                "Paper Forecast Accuracy",
                f"{accuracy:.1f}%",
            )

        st.write(
            f"Misses: {misses}"
        )

    else:
        st.info(
            "No directional forecasts have been verified yet."
        )

    st.dataframe(
        forecast_df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download Forecast Log CSV",
        data=(
            forecast_df
            .to_csv(index=False)
            .encode("utf-8")
        ),
        file_name="next_60_second_forecast_log.csv",
        mime="text/csv",
    )

    if st.button(
        "Clear Forecast Log"
    ):
        st.session_state.forecast_log = []
        st.rerun()

else:
    st.info(
        "No forecast tests yet."
    )


st.caption(
    "Paper/demo testing only. The forecast is calculated "
    "before the verification minute happens, but it cannot "
    "know future prices with certainty. Yahoo Finance data "
    "may be delayed and does not match Pocket Option OTC pricing."
                    )
