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


def latest_price(ticker):
    data = yf.Ticker(ticker).history(
        period="1d",
        interval="1m",
        prepost=True,
    )

    if data.empty:
        return None

    return float(data["Close"].iloc[-1])


def analyze(ticker):
    data = yf.Ticker(ticker).history(period="6mo")

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
        "rsi": float(latest["RSI"]),
        "macd": float(latest["MACD"]),
        "macd_signal": float(
            latest["MACD_SIGNAL"]
        ),
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


def evaluate_alignment(
    bias,
    movement,
):
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
    page_title="Paper Trading Signal App",
    page_icon="📈",
    layout="wide",
)

st.title(
    "📈 My Paper Trading Signal App"
)

st.caption(
    "Paper-testing and educational use only. "
    "Scores show indicator alignment, "
    "not a probability of winning."
)


if "observations" not in st.session_state:
    st.session_state.observations = []


st.subheader(
    "🔎 Check One Stock"
)

ticker = st.text_input(
    "Enter a stock ticker:",
    "AAPL",
    key="signal_ticker",
).upper().strip()


if st.button(
    "Check Signal"
):
    try:
        result = analyze(
            ticker
        )

        if result is None:
            st.error(
                "Not enough market data was found."
            )

        else:
            st.metric(
                "Latest price",
                f"${result['price']:.2f}",
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
                f"RSI: {result['rsi']:.2f}"
            )

            st.write(
                f"MACD: {result['macd']:.4f}"
            )

            st.write(
                "MACD signal line: "
                f"{result['macd_signal']:.4f}"
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
    "The observation starts immediately, "
    "waits 60 seconds, then records whether "
    "the market price moved UP, DOWN, or FLAT."
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
        analysis = analyze(
            obs_ticker
        )

        start_time = now_local()

        start_price = latest_price(
            obs_ticker
        )

        if start_price is None:
            st.error(
                "Could not get a starting price."
            )

        else:
            st.info(
                "Observation started at "
                f"{fmt_time(start_time)}"
            )

            st.write(
                f"Starting price: "
                f"${start_price:.4f}"
            )

            if analysis is not None:
                st.write(
                    "Paper bias at start: "
                    f"{analysis['bias']}"
                )

                st.write(
                    f"Bullish: "
                    f"{analysis['bullish']} / 100"
                )

                st.write(
                    f"Bearish: "
                    f"{analysis['bearish']} / 100"
                )

            with st.spinner(
                "Observing for 60 seconds..."
            ):
                time.sleep(60)

            end_time = now_local()

            end_price = latest_price(
                obs_ticker
            )

            if end_price is None:
                st.error(
                    "Could not get the ending price."
                )

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

                if analysis is None:
                    bias = "NEUTRAL"
                    bullish = None
                    bearish = None

                else:
                    bias = analysis["bias"]
                    bullish = analysis[
                        "bullish"
                    ]
                    bearish = analysis[
                        "bearish"
                    ]

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
                    f"Start: "
                    f"${start_price:.4f}"
                )

                st.write(
                    f"End: "
                    f"${end_price:.4f}"
                )

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

                elif evaluation == "FLAT":
                    st.info(
                        "➖ Flat result. "
                        "Not counted as a match "
                        "or miss."
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
                                "%Y-%m-%d "
                                "%I:%M:%S %p"
                            )
                        ),
                        "End Time": (
                            end_time.strftime(
                                "%Y-%m-%d "
                                "%I:%M:%S %p"
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

    st.dataframe(
        observation_df,
        use_container_width=True,
        hide_index=True,
    )

    csv_data = (
        observation_df
        .to_csv(index=False)
        .encode("utf-8")
    )

    st.download_button(
        "Download Observation Log CSV",
        data=csv_data,
        file_name=(
            "60_second_observation_log.csv"
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


st.divider()


st.subheader(
    "📋 Paper Trading Watchlist"
)

watchlist_text = st.text_input(
    "Enter tickers separated by commas:",
    "AAPL, MSFT, NVDA",
    key="watchlist",
)

watchlist = [
    item.strip().upper()
    for item in watchlist_text.split(",")
    if item.strip()
]


if st.button(
    "Scan Watchlist"
):
    rows = []

    for symbol in watchlist:
        try:
            result = analyze(
                symbol
            )

            if result is not None:
                rows.append(
                    {
                        "Ticker": symbol,
                        "Price": round(
                            result["price"],
                            2,
                        ),
                        "RSI": round(
                            result["rsi"],
                            2,
                        ),
                        "Bullish": result[
                            "bullish"
                        ],
                        "Bearish": result[
                            "bearish"
                        ],
                        "Paper Bias": result[
                            "bias"
                        ],
                    }
                )

        except Exception:
            pass

    if rows:
        st.dataframe(
            pd.DataFrame(
                rows
            ),
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.warning(
            "No watchlist results available."
        )


st.caption(
    "Paper-testing only. Yahoo Finance data "
    "may be delayed and does not match "
    "Pocket Option OTC pricing. Results are "
    "observations, not instructions to buy or sell."
)
