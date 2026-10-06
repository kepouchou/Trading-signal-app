import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Trading Signal App",
    page_icon="📈",
    layout="wide"
)

st.title("📈 My Paper Trading Signal App")
st.write("Market signal analysis for paper trading and learning only.")

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
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

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

    score = 0

    if latest["SMA5"] > latest["SMA10"]:
        score += 1

    if latest["RSI"] > 50:
        score += 1

    if latest["MACD"] > latest["MACD_SIGNAL"]:
        score += 1

    if latest["Close"] > latest["BB_MIDDLE"]:
        score += 1

    if score >= 3:
        signal = "PAPER BUY SIGNAL"
    else:
        signal = "WAIT / NO SIGNAL"

    return {
        "ticker": ticker,
        "price": latest["Close"],
        "rsi": latest["RSI"],
        "macd": latest["MACD"],
        "macd_signal": latest["MACD_SIGNAL"],
        "score": score,
        "signal": signal,
        "chart_data": clean_data[
            ["Close", "SMA5", "SMA10", "BB_MIDDLE"]
        ]
    }


st.subheader("🔎 Check One Stock")

ticker = st.text_input(
    "Enter a stock ticker:",
    "AAPL"
).upper().strip()

if st.button("Check Signal"):
    try:
        result = analyze_ticker(ticker)

        if result is None:
            st.error("Not enough market data found for this ticker.")

        else:
            st.subheader(f"{ticker} Signal")

            st.write(
                f"Latest price: ${result['price']:.2f}"
            )

            st.write(
                f"RSI: {result['rsi']:.2f}"
            )

            st.write(
                f"MACD: {result['macd']:.4f}"
            )

            st.write(
                f"MACD signal line: "
                f"{result['macd_signal']:.4f}"
            )

            st.write(
                f"Signal score: {result['score']} / 4"
            )

            if result["score"] >= 3:
                st.success(
                    "✅ PAPER ENTRY CONDITIONS ALIGNED"
                )

                st.subheader(
                    "✅ PAPER BUY SIGNAL"
                )

            else:
                st.warning(
                    "⏳ WAIT / NO SIGNAL"
                )

            st.line_chart(
                result["chart_data"]
            )

            st.session_state.signal_log.append({
                "Time": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Ticker": ticker,
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
                "Score": result["score"],
                "Signal": result["signal"]
            })

    except Exception as e:
        st.error(
            f"Something went wrong: {e}"
        )


st.divider()

st.subheader("📋 Paper Trading Watchlist")

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
            result = analyze_ticker(symbol)

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
                    "Score": result["score"],
                    "Signal": result["signal"]
                })

                st.session_state.signal_log.append({
                    "Time": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "Ticker": symbol,
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
                    "Score": result["score"],
                    "Signal": result["signal"]
                })

        except Exception:
            pass

    if watchlist_results:
        watchlist_df = pd.DataFrame(
            watchlist_results
        )

        st.dataframe(
            watchlist_df,
            use_container_width=True
        )

    else:
        st.warning(
            "No watchlist results were available."
        )


st.divider()

st.subheader("📝 Signal Log")

if st.session_state.signal_log:
    log_df = pd.DataFrame(
        st.session_state.signal_log
    )

    st.dataframe(
        log_df,
        use_container_width=True
    )

    csv_data = log_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="Download Signal Log CSV",
        data=csv_data,
        file_name="paper_trading_signal_log.csv",
        mime="text/csv"
    )

    if st.button("Clear Signal Log"):
        st.session_state.signal_log = []
        st.rerun()

else:
    st.info(
        "No signals logged yet."
    )


st.caption(
    "Paper-testing and educational use only. "
    "This app does not place trades, "
    "does not guarantee future results, "
    "and is not financial advice."
)
