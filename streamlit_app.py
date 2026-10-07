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
        "ticker": ticker,
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


def evaluate_alignment(
    bias,
    movement,
):
    if movement == "NO FRESH DATA":
        return "NO FRESH DATA"

    if bias == "BULLISH":
        if movement == "UP":
            return "MATCH"
        if movement == "DOWN":
            return "MISS"
        return "FLAT"

    if bias == "BEARISH":
        if movement == "DOWN":
            return "MATCH"
        if movement == "UP":
            return "MISS"
        return "FLAT"

    return "NEUTRAL"


st.set_page_config(
    page_title="Short-Term Paper Signal App",
    page_icon="📈",
    layout="wide",
)

st.title(
    "📈 Short-Term Paper Signal App"
)

st.caption(
    "Paper-testing and educational use only. "
    "This app uses 1-minute Yahoo Finance data. "
    "Scores are not probabilities and do not predict "
    "Pocket Option OTC prices."
)

if "observations" not in st.session_state:
    st.session_state.observations = []


st.subheader(
    "🔎 Check One Stock"
)

ticker = st.text_input(
    "Enter a stock ticker:",
    "MSFT",
    key="signal_ticker",
).upper().strip()

if st.button(
    "Check Short-Term Signal"
):
    try:
        result = analyze_short_term(
            ticker
        )

        if result is None:
            st.error(
                "Not enough 1-minute market data was found."
            )
        else:
            st.metric(
                "Latest price",
                f"${result['price']:.4f}",
            )

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "📈 Bullish Score",
                    f"{result['bullish']} / 100",
                )
                st.progress(
                    result["bullish"] / 100
                )

            with col2:
                st.metric(
                    "📉 Bearish Score",
                    f"{result['bearish']} / 100",
                )
                st.progress(
                    result["bearish"] / 100
                )

            if result["bias"] == "BULLISH":
                st.success(
                    "📈 PAPER BULLISH ALIGNMENT"
                )
            elif result["bias"] == "BEARISH":
                st.warning(
                    "📉 PAPER BEARISH ALIGNMENT"
                )
            else:
                st.info(
                    "⚖️ MIXED / NEUTRAL"
                )

            st.write(
                f"RSI(7): {result['rsi']:.2f}"
            )

            st.write(
                f"MACD: {result['macd']:.4f}"
            )

            st.write(
                "MACD signal line: "
                f"{result['macd_signal']:.4f}"
            )

            st.write(
                "3-minute momentum: "
                f"{result['momentum3']:.4f}"
            )

            st.line_chart(
                result["chart"]
            )

    except Exception as exc:
        st.error(
            f"Signal error: {exc}"
        )


st.divider()

st.subheader(
    "⏱️ 60-Second Paper Observation"
)

st.write(
    "The app records the newest 1-minute Yahoo Finance sample, "
    "waits 60 seconds, and checks again. "
    "If Yahoo did not publish a newer sample, the result is "
    "NO FRESH DATA instead of FLAT."
)

obs_ticker = st.text_input(
    "Ticker for 60-second observation:",
    "MSFT",
    key="observation_ticker",
).upper().strip()

if st.button(
    "Start 60-Second Observation"
):
    try:
        analysis = analyze_short_term(
            obs_ticker
        )

        start_time = now_local()

        start_sample = get_latest_sample(
            obs_ticker
        )

        if start_sample is None:
            st.error(
                "Could not get a starting market sample."
            )
        else:
            start_price = start_sample[
                "price"
            ]

            start_data_time = start_sample[
                "timestamp"
            ]

            st.info(
                "Observation started at "
                f"{fmt_time(start_time)}"
            )

            st.write(
                f"Starting price: "
                f"${start_price:.4f}"
            )

            st.write(
                "Yahoo sample time: "
                f"{fmt_time(start_data_time)}"
            )

            if analysis is None:
                bias = "NEUTRAL"
                bullish = None
                bearish = None

                st.warning(
                    "Short-term bias was unavailable, "
                    "so this observation will not count "
                    "toward directional accuracy."
                )
            else:
                bias = analysis["bias"]
                bullish = analysis["bullish"]
                bearish = analysis["bearish"]

                st.write(
                    f"Paper bias at start: {bias}"
                )

                st.write(
                    f"Bullish: {bullish} / 100"
                )

                st.write(
                    f"Bearish: {bearish} / 100"
                )

            with st.spinner(
                "Observing for 60 seconds..."
            ):
                time.sleep(60)

            end_time = now_local()

            end_sample = get_latest_sample(
                obs_ticker
            )

            if end_sample is None:
                st.error(
                    "Could not get an ending market sample."
                )
            else:
                end_price = end_sample[
                    "price"
                ]

                end_data_time = end_sample[
                    "timestamp"
                ]

                fresh_data = (
                    end_data_time
                    > start_data_time
                )

                if not fresh_data:
                    change = 0.0
                    movement = "NO FRESH DATA"
                else:
                    change = (
                        end_price
                        - start_price
                    )

                    if change > 0:
                        movement = "UP"
                    elif change < 0:
                        movement = "DOWN"
                    else:
                        movement = "FLAT"

                evaluation = (
                    evaluate_alignment(
                        bias,
                        movement,
                    )
                )

                st.subheader(
                    "60-Second Result"
                )

                st.write(
                    "Observation time: "
                    f"{fmt_time(start_time)} "
                    "→ "
                    f"{fmt_time(end_time)}"
                )

                st.write(
                    "Yahoo sample time: "
                    f"{fmt_time(start_data_time)} "
                    "→ "
                    f"{fmt_time(end_data_time)}"
                )

                st.write(
                    f"Start: "
                    f"${start_price:.4f}"
                )

                st.write(
                    f"End: "
                    f"${end_price:.4f}"
                )

                if movement == "NO FRESH DATA":
                    st.info(
                        "⏸️ Result: NO FRESH DATA"
                    )

                    st.write(
                        "Yahoo Finance did not publish "
                        "a newer 1-minute sample during "
                        "this test."
                    )

                else:
                    st.write(
                        f"Change: "
                        f"{change:.4f}"
                    )

                    if movement == "UP":
                        st.success(
                            "📈 Result: UP"
                        )
                    elif movement == "DOWN":
                        st.warning(
                            "📉 Result: DOWN"
                        )
                    else:
                        st.info(
                            "➖ Result: FLAT"
                        )

                if evaluation == "MATCH":
                    st.success(
                        "✅ Paper bias matched "
                        "the observed direction."
                    )

                elif evaluation == "MISS":
                    st.error(
                        "❌ Paper bias did not match "
                        "the observed direction."
                    )

                elif evaluation == "NO FRESH DATA":
                    st.info(
                        "⏸️ Not counted in accuracy "
                        "because there was no fresh data."
                    )

                elif evaluation == "FLAT":
                    st.info(
                        "➖ Fresh data was received, "
                        "but price finished flat. "
                        "Not counted as a match or miss."
                    )

                else:
                    st.info(
                        "⚖️ Neutral paper bias. "
                        "Not counted in accuracy."
                    )

                st.session_state.observations.append(
                    {
                        "Start Time": (
                            start_time.strftime(
                                "%Y-%m-%d %I:%M:%S %p"
                            )
                        ),
                        "End Time": (
                            end_time.strftime(
                                "%Y-%m-%d %I:%M:%S %p"
                            )
                        ),
                        "Start Data Time": (
                            start_data_time.strftime(
                                "%Y-%m-%d %I:%M:%S %p"
                            )
                        ),
                        "End Data Time": (
                            end_data_time.strftime(
                                "%Y-%m-%d %I:%M:%S %p"
                            )
                        ),
                        "Ticker": obs_ticker,
                        "Start Price": round(
                            start_price,
                            4,
                        ),
                        "End Price": round(
                            end_price,
                            4,
                        ),
                        "Change": round(
                            change,
                            4,
                        ),
                        "Movement": movement,
                        "Bullish": bullish,
                        "Bearish": bearish,
                        "Paper Bias": bias,
                        "Evaluation": evaluation,
                    }
                )

    except Exception as exc:
        st.error(
            f"Observation error: {exc}"
        )


st.divider()

st.subheader(
    "📊 Paper Accuracy Tracker"
)

if st.session_state.observations:
    observation_df = pd.DataFrame(
        st.session_state.observations
    )

    directional = observation_df[
        observation_df[
            "Evaluation"
        ].isin(
            [
                "MATCH",
                "MISS",
            ]
        )
    ]

    total = len(
        directional
    )

    matches = int(
        (
            directional[
                "Evaluation"
            ]
            == "MATCH"
        ).sum()
    )

    misses = int(
        (
            directional[
                "Evaluation"
            ]
            == "MISS"
        ).sum()
    )

    stale_count = int(
        (
            observation_df[
                "Evaluation"
            ]
            == "NO FRESH DATA"
        ).sum()
    )

    if total > 0:
        accuracy = (
            matches
            / total
            * 100
        )

        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:
            st.metric(
                "Directional Tests",
                total,
            )

        with col2:
            st.metric(
                "Matches",
                matches,
            )

        with col3:
            st.metric(
                "Paper Accuracy",
                f"{accuracy:.1f}%",
            )

        st.write(
            f"Misses: {misses}"
        )
    else:
        st.info(
            "No directional tests "
            "have been counted yet."
        )

    st.metric(
        "No Fresh Data Tests",
        stale_count,
    )

    bullish_tests = directional[
        directional[
            "Paper Bias"
        ]
        == "BULLISH"
    ]

    bearish_tests = directional[
        directional[
            "Paper Bias"
        ]
        == "BEARISH"
    ]

    bullish_total = len(
        bullish_tests
    )

    bearish_total = len(
        bearish_tests
    )

    bullish_matches = int(
        (
            bullish_tests[
                "Evaluation"
            ]
            == "MATCH"
        ).sum()
    )

    bearish_matches = int(
        (
            bearish_tests[
                "Evaluation"
            ]
            == "MATCH"
        ).sum()
    )

    st.subheader(
        "Direction Breakdown"
    )

    if bullish_total > 0:
        bullish_accuracy = (
            bullish_matches
            / bullish_total
            * 100
        )

        st.write(
            "📈 Bullish tests: "
            f"{bullish_matches} matches "
            f"out of {bullish_total} "
            f"({bullish_accuracy:.1f}%)"
        )
    else:
        st.write(
            "📈 Bullish tests: 0"
        )

    if bearish_total > 0:
        bearish_accuracy = (
            bearish_matches
            / bearish_total
            * 100
        )

        st.write(
            "📉 Bearish tests: "
            f"{bearish_matches} matches "
            f"out of {bearish_total} "
            f"({bearish_accuracy:.1f}%)"
        )
    else:
        st.write(
            "📉 Bearish tests: 0"
        )

    st.dataframe(
        observation_df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download Observation Log CSV",
        data=(
            observation_df
            .to_csv(index=False)
            .encode("utf-8")
        ),
        file_name=(
            "short_term_observation_log.csv"
        ),
        mime="text/csv",
    )

    if st.button(
        "Clear Observation Log"
    ):
        st.session_state.observations = []
        st.rerun()

else:
    st.info(
        "No observations yet."
    )


st.caption(
    "Paper-testing only. NO FRESH DATA means "
    "Yahoo Finance did not provide a newer 1-minute "
    "market sample during the observation. Those tests "
    "are excluded from the accuracy calculation."
)
