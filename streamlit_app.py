st.divider()

st.subheader(
    "⏱️ 60-Second Paper Observation"
)

st.write(
    "This schedules a future 60-second observation. "
    "The app waits for the scheduled time, records "
    "the starting price, waits 60 seconds, then "
    "shows whether the price moved UP, DOWN, or FLAT."
)

observation_ticker = st.text_input(
    "Ticker for 60-second observation:",
    "MSFT",
    key="observation_ticker"
).upper().strip()


if st.button(
    "Start Future 60-Second Observation"
):
    try:
        analysis = analyze_ticker(
            observation_ticker
        )

        now = local_now()

        target_start = (
            now.replace(
                second=0,
                microsecond=0
            )
            + timedelta(minutes=2)
        )

        target_end = (
            target_start
            + timedelta(minutes=1)
        )

        st.write(
            "Scheduled observation: "
            f"{format_time(target_start)}"
            " → "
            f"{format_time(target_end)}"
        )

        seconds_to_wait = (
            target_start - local_now()
        ).total_seconds()

        if seconds_to_wait > 0:
            with st.spinner(
                "Waiting for the scheduled "
                "observation time..."
            ):
                time.sleep(seconds_to_wait)

        start_time = local_now()

        start_price = get_latest_price(
            observation_ticker
        )

        if start_price is None:
            st.error(
                "Could not get a starting price."
            )

        else:
            st.write(
                "Observation started at: "
                f"{format_time(start_time)}"
            )

            st.write(
                f"Starting price: "
                f"${start_price:.4f}"
            )

            with st.spinner(
                "Observing for 60 seconds..."
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
