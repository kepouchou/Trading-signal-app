import time
from datetime import datetime, timedelta
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
        prepost=True
    )

    if data.empty:
        return None

    return float(data["Close"].iloc[-1])


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
        bias = "PAPER BULLISH ALIGNMENT"

    elif bearish >= 75:
        bias = "PAPER BEARISH ALIGNMENT"

    else:
        bias = "MIXED / NEUTRAL"

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
                "BB_MIDDLE"
            ]
        ]
    }


def log_signal(result):
    st.session_state.signal_log.append(
        {
            "Time": now_local().strftime(
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
            "Bullish": result[
                "bullish"
            ],
            "Bearish": result[
                "bearish"
            ],
            "Paper Bias": result[
                "bias"
            ]
        }
    )


st.set_page_config(
    page_title="Paper Trading Signal App",
    page_icon="📈",
    layout="wide"
)

st.title(
    "📈 My Paper Trading Signal App"
)

st.caption(
    "Paper-testing and educational use only. "
    "Scores are indicator alignment, "
    "not trade probabilities."
)


if "signal_log" not in st.session_state:
    st.session_state.signal_log = []

if "observation_log" not in st.session_state:
    st.session_state.observation_log = []


st.subheader(
    "🔎 Check One Stock"
)

ticker = st.text_input(
    "Enter a stock ticker:",
    "AAPL"
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
                f"${result['price']:.2f}"
            )

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "📈 Bullish Score",
                    f"{result['bullish']} / 100"
                )

                st.progress(
                    result["bullish"] / 100
                )

            with col2:
                st.metric(
                    "📉 Bearish Score",
                    f"{result['bearish']} / 100"
                )

                st.progress(
                    result["bearish"] / 100
                )

            if (
                result["bias"]
                == "PAPER BULLISH ALIGNMENT"
            ):
                st.success(
                    "📈 PAPER BULLISH ALIGNMENT"
                )

            elif (
                result["bias"]
                == "PAPER BEARISH ALIGNMENT"
            ):
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

            log_signal(
                result
            )

    except Exception as e:
        st.error(
            f"Signal error: {e}"
        )


st.divider()

st.subheader(
    "⏱️ Future 60-Second Paper Observation"
)

st.write(
    "Press the button now. "
    "The app schedules the observation "
    "for two minutes ahead, then watches "
    "that future one-minute window."
)

obs_ticker = st.text_input(
    "Ticker for future observation:",
    "MSFT",
    key="obs"
).upper().strip()


if st.button(
    "Start Future 60-Second Observation"
):
    try:
        analysis = analyze(
            obs_ticker
        )

        current = now_local()

        target_start = (
            current.replace(
                second=0,
                microsecond=0
            )
            + timedelta(minutes=2)
        )

        target_end = (
            target_start
            + timedelta(minutes=1)
        )

        st.info(
            "Scheduled observation: "
            f"{fmt_time(target_start)} → "
            f"{fmt_time(target_end)}"
        )

        wait_seconds = (
            target_start
            - now_local()
        ).total_seconds()

        if wait_seconds > 0:
            with st.spinner(
                "Waiting for the scheduled "
                "observation time..."
            ):
                time.sleep(
                    wait_seconds
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
            st.write(
                "Observation started at: "
                f"{fmt_time(start_time)}"
            )

            st.write(
                f"Starting price: "
                f"${start_price:.4f}"
            )

            with st.spinner(
                "Observing for 60 seconds..."
            ):
                time.sleep(
                    60
                )

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

                st.subheader(
                    "60-Second Result"
                )

                st.write(
                    "Observation time: "
                    f"{fmt_time(start_time)} → "
                    f"{fmt_time(end_time)}"
                )

                st.write(
                    f"Start: ${start_price:.4f}"
                )

                st.write(
                    f"End: ${end_price:.4f}"
                )

                st.write(
                    f"Change: {change:.4f}"
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

                st.session_state.observation_log.append(
                    {
                        "Scheduled Start": (
                            target_start.strftime(
                                "%Y-%m-%d %I:%M:%S %p"
                            )
                        ),
                        "Scheduled End": (
                            target_end.strftime(
                                "%Y-%m-%d %I:%M:%S %p"
                            )
                        ),
                        "Actual Start": (
                            start_time.strftime(
                                "%Y-%m-%d %I:%M:%S %p"
                            )
                        ),
                        "Actual End": (
                            end_time.strftime(
                                "%Y-%m-%d %I:%M:%S %p"
                            )
                        ),
                        "Ticker": obs_ticker,
                        "Start Price": round(
                            start_price,
                            4
                        ),
                        "End Price": round(
                            end_price,
                            4
                        ),
                        "Change": round(
                            change,
                            4
                        ),
                        "Movement": movement,
                        "Bullish": (
                            None
                            if analysis is None
                            else analysis["bullish"]
                        ),
                        "Bearish": (
                            None
                            if analysis is None
                            else analysis["bearish"]
                        ),
                        "Paper Bias": (
                            None
                            if analysis is None
                            else analysis["bias"]
                        )
                    }
                )

    except Exception as e:
        st.error(
            f"Observation error: {e}"
        )


st.divider()

st.subheader(
    "📋 Paper Trading Watchlist"
)

watchlist_text = st.text_input(
    "Enter tickers separated by commas:",
    "AAPL, MSFT, NVDA",
    key="watch"
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
                            2
                        ),
                        "RSI": round(
                            result["rsi"],
                            2
                        ),
                        "Bullish": result[
                            "bullish"
                        ],
                        "Bearish": result[
                            "bearish"
                        ],
                        "Paper Bias": result[
                            "bias"
                        ]
                    }
                )

                log_signal(
                    result
                )

        except Exception:
            pass

    if rows:
        st.dataframe(
            pd.DataFrame(
                rows
            ),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.warning(
            "No watchlist results available."
        )


st.divider()

st.subheader(
    "📝 Signal Log"
)

if st.session_state.signal_log:
    signal_df = pd.DataFrame(
        st.session_state.signal_log
    )

    st.dataframe(
        signal_df,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download Signal Log CSV",
        data=(
            signal_df
            .to_csv(index=False)
            .encode("utf-8")
        ),
        file_name=(
            "paper_signal_log.csv"
        ),
        mime="text/csv"
    )

else:
    st.info(
        "No signals logged yet."
    )


st.divider()

st.subheader(
    "⏱️ Future Observation Log"
)

if st.session_state.observation_log:
    observation_df = pd.DataFrame(
        st.session_state.observation_log
    )

    st.dataframe(
        observation_df,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download Observation Log CSV",
        data=(
            observation_df
            .to_csv(index=False)
            .encode("utf-8")
        ),
        file_name=(
            "future_60_second_observation_log.csv"
        ),
        mime="text/csv"
    )

else:
    st.info(
        "No future observations yet."
    )


st.caption(
    "Yahoo Finance data may be delayed "
    "and does not match Pocket Option OTC pricing. "
    "This app records paper observations only."
        )
