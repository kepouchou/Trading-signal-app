import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Trading Signal App", page_icon="📈")

st.title("📈 My Paper Trading Signal App")
st.write("Market signal analysis for paper trading and learning only.")

ticker = st.text_input("Enter a stock ticker:", "AAPL").upper().strip()

if st.button("Check Signal"):
    try:
        data = yf.Ticker(ticker).history(period="6mo")

        if data.empty or len(data) < 30:
            st.error("Not enough market data found for this ticker.")
        else:
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
            data["MACD_SIGNAL"] = data["MACD"].ewm(span=9, adjust=False).mean()

            # Bollinger middle band
            data["BB_MIDDLE"] = close.rolling(20).mean()

            latest = data.dropna().iloc[-1]

            score = 0

            if latest["SMA5"] > latest["SMA10"]:
                score += 1

            if latest["RSI"] > 50:
                score += 1

            if latest["MACD"] > latest["MACD_SIGNAL"]:
                score += 1

            if latest["Close"] > latest["BB_MIDDLE"]:
                score += 1

            st.subheader(f"{ticker} Signal")

            st.write(f"Latest price: ${latest['Close']:.2f}")
            st.write(f"RSI: {latest['RSI']:.2f}")
            st.write(f"MACD: {latest['MACD']:.4f}")
            st.write(f"MACD signal line: {latest['MACD_SIGNAL']:.4f}")
            st.write(f"Signal score: {score} / 4")

            if score >= 3:
                st.success("✅ PAPER ENTRY CONDITIONS ALIGNED")
                st.subheader("✅ PAPER BUY SIGNAL")
            else:
                st.warning("⏳ WAIT / NO SIGNAL")

            chart_data = data[["Close", "SMA5", "SMA10", "BB_MIDDLE"]].dropna()
            st.line_chart(chart_data)

            st.caption(
                "Paper-testing and educational use only. "
                "This is not financial advice and does not guarantee future results."
            )

    except Exception as e:
        st.error(f"Something went wrong: {e}")
