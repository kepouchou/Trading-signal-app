import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
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

    sma_bullish = (
        latest["SMA5"]
        > latest["SMA10"]
    )

    rsi_bullish = (
        latest["RSI"] > 50
    )

    macd_bullish = (
        latest["MACD"]
        > latest["MACD_SIGNAL"]
    )

    price_bullish = (
        latest["Close"]
        > latest["BB_MIDDLE"]
    )

    if sma_bullish:
        bullish_score += 25

    if rsi_bullish:
        bullish_score += 25

    if macd_bullish:
        bullish_score += 25

    if price_bullish:
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

            st.metric(
                "Latest price",
                f"${result['price']:.2f}"
            )

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "📈 Bullish Score",
                    f"{result['bullish_score']} / 100"
                )

                st.progress(
                    result["bullish_score"] / 100
                )

            with col2:
                st.metric(
                    "📉 Bearish Score",
                    f"{result['bearish_score']} / 100"
                )

                st.progress(
                    result["bearish_score"] / 100
                )

            if (
                result["paper_bias"]
                == "PAPER BULLISH ALIGNMENT"
            ):
                st.success(
                    "📈 PAPER BULLISH ALIGNMENT"
                )

            elif (
                result["paper_bias"]
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
                result["chart_data"]
            )

            add_signal_log(result)

    except Exception as e:
        st.error(
            f"Something went wrong: {e}"
        )


st.divider()

st.subheader(
    "⏱️ 60-Second Paper Observation"
)

st.write(
    "This records a starting market price, "
    "waits 60 seconds, checks again, "
    "and labels the movement UP, DOWN, "
    "or FLAT. No trade is placed."
)

observation_ticker = st.text_input(
    "Ticker for 60-second observation:",
    "MSFT",
    key="observation_ticker"
).upper().strip()


if st.button(
    "Start 60-Second Observation"
):
    try:
        analysis = analyze_ticker(
            observation_ticker
        )

        start_price = get_latest_price(
            observation_ticker
        )

        if start_price is None:
            st.error(
                "Could not get a starting price."
            )

        else:
            start_time = local_now()

            st.write(
                f"Starting price: "
                f"${start_price:.4f}"
            )

            st.write(
                "Started at: "
                f"{format_time(start_time)}"
            )

            with st.spinner(
                "Waiting 60 seconds..."
            ):
                time.sleep(60)

            end_price = get_latest_price(
                observation_ticker
            )

            end_time = local_now()

            if end_price is None:
                st.error(
                    "Could not get the ending price."
                )

            else:
                difference = (
                    end_price
                    - start_price
                )

                if difference > 0:
                    movement = "UP"

                elif difference < 0:
                    movement = "DOWN"

                else:
                    movement = "FLAT"

                st.subheader(
                    "60-Second Result"
                )

                st.write(
                    "Observation time: "
                    f"{format_time(start_time)}"
                    " → "
                    f"{format_time(end_time)}"
                )

                st.write(
                    f"Start: ${start_price:.4f}"
                )

                st.write(
                    f"End: ${end_price:.4f}"
                )

                st.write(
                    f"Change: {difference:.4f}"
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

                bullish_score = None
                bearish_score = None
                paper_bias = None

                if analysis is not None:
                    bullish_score = analysis[
                        "bullish_score"
                    ]

                    bearish_score = analysis[
                        "bearish_score"
                    ]

                    paper_bias = analysis[
                        "paper_bias"
                    ]

                st.session_state.observation_log.append({
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
                    "Ticker": observation_ticker,
                    "Start Price": round(
                        start_price,
                        4
                    ),
                    "End Price": round(
                        end_price,
                        4
                    ),
                    "Change": round(
                        difference,
                        4
                    ),
                    "Movement": movement,
                    "Bullish Score": bullish_score,
                    "Bearish Score": bearish_score,
                    "Paper Bias": paper_bias
                })

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
    key="watchlist"
)

watchlist = [
    item.strip().upper()
    for item in watchlist_text.split(",")
    if item.strip()
]


if st.button("Scan Watchlist"):
    results = []

    for symbol in watchlist:
        try:
            result = analyze_ticker(
                symbol
            )

            if result is not None:
                results.append({
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
                        "bullish_score"
                    ],
                    "Bearish": result[
                        "bearish_score"
                    ],
                    "Paper Bias": result[
                        "paper_bias"
                    ]
                })

                add_signal_log(result)

        except Exception:
            pass

    if results:
        st.dataframe(
            pd.DataFrame(results),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.warning(
            "No watchlist results available."
        )


st.divider()

st.subheader("📝 Signal Log")

if st.session_state.signal_log:
    signal_df = pd.DataFrame(
        st.session_state.signal_log
    )

    st.dataframe(
        signal_df,
        use_container_width=True,
        hide_index=True
    )

    signal_csv = (
        signal_df
        .to_csv(index=False)
        .encode("utf-8")
    )

    st.download_button(
        "Download Signal Log CSV",
        data=signal_csv,
        file_name="paper_signal_log.csv",
        mime="text/csv"
    )

else:
    st.info(
        "No signals logged yet."
    )


st.divider()

st.subheader(
    "⏱️ 60-Second Observation Log"
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

    observation_csv = (
        observation_df
        .to_csv(index=False)
        .encode("utf-8")
    )

    st.download_button(
        "Download Observation Log CSV",
        data=observation_csv,
        file_name=(
            "60_second_observation_log.csv"
        ),
        mime="text/csv"
    )

else:
    st.info(
        "No 60-second observations yet."
    )


st.divider()

st.caption(
    "Paper-testing and educational use only. "
    "The 60-second observation uses Yahoo Finance "
    "market data, which may be delayed or update "
    "slower than 60 seconds. It does not match "
    "Pocket Option OTC pricing and should not be "
    "used as live entry timing or as an instruction "
    "to buy or sell."
            )
