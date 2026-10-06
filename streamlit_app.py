import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

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


def analyze_ticker(ticker):
    data = yf.Ticker(ticker).history(period="6mo")

    if data.empty or len(data) < 30:
        return None

    close = data["Close"]

    # Moving averages
    data["SMA5"] = close.rolling(5).mean()
    data["SMA10"] = close.rolling(10).mean()

    # RSI 14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False
    ).mean()

    data["MACD"] = ema12 - ema26

    data["MACD_SIGNAL"] = data["MACD"].ewm(
        span=9,
        adjust=False
    ).mean()

    # Bollinger middle band
    data["BB_MIDDLE"] = close.rolling(20).mean()

    clean_data = data.dropna()

    if clean_data.empty:
        return None

    latest = clean_data.iloc[-1]

    bullish_points = 0

    # Indicator 1: short trend
    sma_bullish = (
        latest["SMA5"] >
        latest["SMA10"]
    )

    if sma_bullish:
        bullish_points += 25

    # Indicator 2: RSI momentum
    rsi_bullish = (
        latest["RSI"] > 50
    )

    if rsi_bullish:
        bullish_points += 25

    # Indicator 3: MACD momentum
    macd_bullish = (
        latest["MACD"] >
        latest["MACD_SIGNAL"]
    )

    if macd_bullish:
        bullish_points += 25

    # Indicator 4: price trend
    price_bullish = (
        latest["Close"] >
        latest["BB_MIDDLE"]
    )

    if price_bullish:
        bullish_points += 25

    bullish_score = bullish_points
    bearish_score = 100 - bullish_score

    if bullish_score >= 75:
        paper_bias = "PAPER BULLISH ALIGNMENT"

    elif bearish_score >= 75:
        paper_bias = "PAPER BEARISH ALIGNMENT"

    else:
        paper_bias = "MIXED / NEUTRAL"

    return {
        "ticker": ticker,
        "price": latest["Close"],
        "rsi": latest["RSI"],
        "macd": latest["MACD"],
        "macd_signal": latest["MACD_SIGNAL"],
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "paper_bias": paper_bias,
        "sma_bullish": sma_bullish,
        "rsi_bullish": rsi_bullish,
        "macd_bullish": macd_bullish,
        "price_bullish": price_bullish,
        "chart_data": clean_data[
            [
                "Close",
                "SMA5",
                "SMA10",
                "BB_MIDDLE"
            ]
        ]
    }


def add_to_log(result):
    st.session_state.signal_log.append({
        "Time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
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
    "AAPL"
).upper().strip()

if st.button("Check Signal"):
    try:
        result = analyze_ticker(ticker)

        if result is None:
            st.error(
                "Not enough market data "
                "was found for this ticker."
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
                result["paper_bias"] ==
                "PAPER BULLISH ALIGNMENT"
            ):
                st.success(
                    "📈 PAPER BULLISH ALIGNMENT"
                )

            elif (
                result["paper_bias"] ==
                "PAPER BEARISH ALIGNMENT"
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

            st.subheader(
                "Indicator Check"
            )

            indicator_table = pd.DataFrame({
                "Indicator": [
                    "SMA5 above SMA10",
                    "RSI above 50",
                    "MACD above signal line",
                    "Price above Bollinger middle"
                ],
                "Bullish": [
                    result["sma_bullish"],
                    result["rsi_bullish"],
                    result["macd_bullish"],
                    result["price_bullish"]
                ]
            })

            st.dataframe(
                indicator_table,
                use_container_width=True,
                hide_index=True
            )

            st.line_chart(
                result["chart_data"]
            )

            add_to_log(result)

    except Exception as e:
        st.error(
            f"Something went wrong: {e}"
        )


st.divider()

st.subheader(
    "📋 Paper Trading Watchlist"
)

watchlist_text = st.text_input(
    "Enter tickers separated by commas:",
    "AAPL, MSFT, NVDA"
)

watchlist = [
    item.strip().upper()
    for item in watchlist_text.split(",")
    if item.strip()
]

if st.button("Scan Watchlist"):
    watchlist_results = []

    for symbol in watchlist:
        try:
            result = analyze_ticker(
                symbol
            )

            if result is not None:
                watchlist_results.append({
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

                add_to_log(result)

        except Exception:
            pass

    if watchlist_results:
        watchlist_df = pd.DataFrame(
            watchlist_results
        )

        st.dataframe(
            watchlist_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.warning(
            "No watchlist results "
            "were available."
        )


st.divider()

st.subheader("📝 Signal Log")

if st.session_state.signal_log:
    log_df = pd.DataFrame(
        st.session_state.signal_log
    )

    st.dataframe(
        log_df,
        use_container_width=True,
        hide_index=True
    )

    csv_data = log_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="Download Signal Log CSV",
        data=csv_data,
        file_name=(
            "paper_trading_signal_log.csv"
        ),
        mime="text/csv"
    )

    if st.button("Clear Signal Log"):
        st.session_state.signal_log = []
        st.rerun()

else:
    st.info(
        "No signals logged yet."
    )


st.divider()

st.subheader(
    "ℹ️ How to read the paper scores"
)

st.write(
    "75 to 100 Bullish = strong bullish "
    "indicator alignment for paper testing."
)

st.write(
    "75 to 100 Bearish = strong bearish "
    "indicator alignment for paper testing."
)

st.write(
    "Scores between those levels are treated "
    "as mixed or neutral."
)

st.caption(
    "These are indicator-alignment scores, "
    "not probabilities and not instructions "
    "to buy or sell. This app uses historical "
    "daily market data and is for paper testing "
    "and educational use only."
        )
