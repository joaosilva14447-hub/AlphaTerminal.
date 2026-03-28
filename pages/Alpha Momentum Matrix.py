        col=1,
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0F0F0F",
        plot_bgcolor="#0F0F0F",
        height=620,
        margin=dict(l=40, r=30, t=40, b=30),
        title=dict(text="Backtest Equity Curve", font=dict(size=18, color="#EAF2FF")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(title="Equity", showgrid=False, row=1, col=1)
    fig.update_yaxes(title="Drawdown %", showgrid=False, row=2, col=1)
    return fig


def render_signal_board(df: pd.DataFrame) -> None:
    records = df.to_dict(orient="records")
    top_cards_html: list[str] = []
    for rank, row_data in enumerate(records[: min(3, len(records))], start=1):
        fill, glow = _score_visuals(float(row_data["Setup Score"]))
        top_cards_html.append(
            (
                f'<div class="signal-card" style="box-shadow: inset 0 0 0 1px {glow};">'
                f'<div class="signal-card-top"><div><div class="signal-rank">Top {rank}</div>'
                f'<div class="signal-asset">{html.escape(str(row_data["Asset"]))}</div></div>'
                f'<div class="signal-score-pill" style="background:{fill};">{row_data["Setup Score"]:.1f}</div></div>'
                f'<div class="signal-card-setup">{html.escape(str(row_data["Setup"]))}</div>'
                f'<div class="signal-card-meta">'
                f'<span class="signal-badge badge-neutral">{html.escape(str(row_data["Asset Class"]))}</span>'
                f'<span class="signal-badge {_badge_class(str(row_data["Alert"]), "Alert")}">{html.escape(str(row_data["Alert"]))}</span>'
                f'<span class="signal-badge {_badge_class(str(row_data["Regime"]), "Regime")}">{html.escape(str(row_data["Regime"]))}</span>'
                f'<span class="signal-badge {_badge_class(str(row_data["Bias"]), "Bias")}">{html.escape(str(row_data["Bias"]))}</span>'
                f'<span class="signal-badge {_badge_class(str(row_data["Squeeze"]), "Squeeze")}">Squeeze {html.escape(str(row_data["Squeeze"]))}</span>'
                f'<span class="signal-badge {_badge_class(str(row_data["Data Health"]), "Data")}">{html.escape(str(row_data["Data Health"]))}</span>'
                f"</div>"
                f'<div class="signal-card-stats">'
                f'<div><div class="signal-stat-label">Momentum Z</div><div class="signal-stat-value">{row_data["Momentum Z"]:+.2f}</div></div>'
                f'<div><div class="signal-stat-label">Acceleration</div><div class="signal-stat-value">{row_data["Acceleration Z"]:+.2f}</div></div>'
                f'<div><div class="signal-stat-label">Trend Z</div><div class="signal-stat-value">{row_data["Trend Z"]:+.2f}</div></div>'
                f'<div><div class="signal-stat-label">RVOL</div><div class="signal-stat-value">{row_data["RVOL"]:.2f}x</div></div>'
                f"</div></div>"
            )
        )

    rows_html: list[str] = []
    for rank, row_data in enumerate(records, start=1):
        score = float(row_data["Setup Score"])
        fill, _ = _score_visuals(score)
        momentum_class = _metric_class(float(row_data["Momentum Z"]), 0.35, -0.35)
        accel_class = _metric_class(float(row_data["Acceleration Z"]), 0.10, -0.10)
        trend_class = _metric_class(float(row_data["Trend Z"]), 0.20, -0.20)
        rvol_class = _metric_class(float(row_data["RVOL"]), 1.05, 0.95)
        rows_html.append(
            (
                "<tr>"
                f'<td class="rank-cell">{rank:02d}</td>'
                f'<td class="asset-cell">{html.escape(str(row_data["Asset"]))}</td>'
                f'<td>{html.escape(str(row_data["Asset Class"]))}</td>'
                f'<td><span class="signal-badge {_badge_class(str(row_data["Setup"]), "Setup")}">{html.escape(str(row_data["Setup"]))}</span></td>'
                f'<td><span class="signal-badge {_badge_class(str(row_data["Alert"]), "Alert")}">{html.escape(str(row_data["Alert"]))}</span></td>'
                f'<td><span class="signal-badge {_badge_class(str(row_data["Bias"]), "Bias")}">{html.escape(str(row_data["Bias"]))}</span></td>'
                f'<td><span class="signal-badge {_badge_class(str(row_data["Regime"]), "Regime")}">{html.escape(str(row_data["Regime"]))}</span></td>'
                f'<td class="score-cell"><div class="score-shell"><div class="score-fill" style="width:{score:.1f}%; background:{fill};"></div></div><div class="score-text">{score:.1f}/100</div></td>'
                f'<td class="{momentum_class}">{row_data["Momentum Z"]:+.2f}</td>'
                f'<td class="{accel_class}">{row_data["Acceleration Z"]:+.2f}</td>'
                f'<td class="{trend_class}">{row_data["Trend Z"]:+.2f}</td>'
                f'<td class="{rvol_class}">{row_data["RVOL"]:.2f}x</td>'
                f"<td>{int(row_data['Squeeze Bars'])}</td>"
                f'<td>{html.escape(str(row_data["Data Health"]))}</td>'
                "</tr>"
            )
        )

    board_html = (
        '<div class="signal-board">'
        '<div class="signal-board-header"><div>'
        '<div class="signal-board-title">Signal Board</div>'
        '<div class="signal-board-subtitle">Causally normalized setups ranked by directional imbalance and structural trend quality</div>'
        "</div></div>"
        f'<div class="signal-board-grid">{"".join(top_cards_html)}</div>'
        '<div class="signal-table"><table><thead><tr>'
        "<th>#</th><th>Asset</th><th>Class</th><th>Setup</th><th>Alert</th><th>Bias</th><th>Regime</th><th>Score</th>"
        "<th>Momentum</th><th>Accel</th><th>Trend</th><th>RVOL</th><th>SQZ</th><th>Data</th>"
        f'</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div></div>'
    )
    st.markdown(board_html, unsafe_allow_html=True)


with st.sidebar:
    with st.form("alpha_momentum_controls"):
        st.header("Radar Controls")
        watchlist_text = st.text_area("Watchlist", DEFAULT_WATCHLIST, height=120)
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=2)
        selected_asset_classes = st.multiselect("Asset Classes", ASSET_CLASS_OPTIONS, default=ASSET_CLASS_OPTIONS)
        long_threshold = st.slider("Long Threshold", min_value=52, max_value=75, value=57, step=1)
        short_threshold = st.slider("Short Threshold", min_value=25, max_value=48, value=43, step=1)
        top_n = st.slider("Rows displayed", min_value=4, max_value=20, value=10, step=1)
        submitted = st.form_submit_button("Analyze Market")

run_analysis = submitted or "alpha_momentum_results" not in st.session_state

if run_analysis:
    tickers = _clean_watchlist(watchlist_text)
    results_rows: list[dict[str, object]] = []
    histories: dict[str, pd.DataFrame] = {}
    backtests: list[dict[str, object]] = []
    trades_log: list[pd.DataFrame] = []
    failures: list[str] = []
    config = TIMEFRAME_CONFIG[timeframe]

    if not tickers:
        st.warning("Add at least one ticker to the watchlist.")
        st.stop()

    with st.spinner("Processing squeeze, momentum, trend, and volume structure..."):
        for symbol in tickers:
            raw, fetch_error = fetch_price_history(symbol, timeframe)
            if fetch_error:
                failures.append(f"{symbol}: {fetch_error}")
                continue
            if raw.empty or len(raw) < config["min_history"]:
                failures.append(f"{symbol}: not enough clean history after normalization")
                continue

            try:
                enriched = calculate_signals(raw, timeframe, float(long_threshold), float(short_threshold))
            except Exception as exc:
                failures.append(f"{symbol}: signal engine failed ({exc})")
                continue

            if enriched.empty:
                failures.append(f"{symbol}: indicators could not be computed")
                continue

            last = enriched.iloc[-1]
            backtest = _backtest_summary(enriched, timeframe)
            trade_log = _backtest_trade_log(enriched, timeframe)
            volume_quality = float(last["VolumeQuality"]) if pd.notna(last["VolumeQuality"]) else 0.0
            data_health = _data_health_label(volume_quality, len(raw), config["min_history"])
            histories[symbol] = enriched.tail(config["display_bars"])
            results_rows.append(
                {
                    "Asset": symbol,
                    "Asset Class": _classify_asset(symbol),
                    "Price": float(last["Close"]),
                    "Regime": str(last["Regime"]),
                    "Bias": str(last["Bias"]),
                    "Setup": str(last["Setup"]),
                    "Alert": str(last["Alert"]),
                    "Setup Score": float(last["SetupScore"]),
                    "Confidence": float(last["Confidence"]),
                    "Squeeze": "ON" if bool(last["SqueezeOn"]) else "OFF",
                    "Squeeze Bars": int(last["SqueezeDuration"]),
                    "Momentum Z": float(last["MomentumZ"]),
                    "Acceleration Z": float(last["AccelerationZ"]),
                    "Trend Z": float(last["TrendZ"]),
                    "RVOL": float(last["RVOL"]),
                    "NATR %": float(last["NATR"]),
                    "BT Signals": int(backtest["signals"]),
                    "BT Hit Rate": float(backtest["hit_rate"]) if pd.notna(backtest["hit_rate"]) else np.nan,
                    "BT Avg %": float(backtest["avg_return"] * 100.0) if pd.notna(backtest["avg_return"]) else np.nan,
                    "Data Health": data_health,
                }
            )
            if not trade_log.empty:
                trade_log = trade_log.copy()
                trade_log["Asset"] = symbol
                trade_log["Asset Class"] = _classify_asset(symbol)
                trades_log.append(trade_log)
            backtests.append(
                {
                    "Asset": symbol,
                    "Asset Class": _classify_asset(symbol),
                    "Signals": int(backtest["signals"]),
                    "Hit Rate": float(backtest["hit_rate"]) if pd.notna(backtest["hit_rate"]) else np.nan,
                    "Avg Return %": float(backtest["avg_return"] * 100.0) if pd.notna(backtest["avg_return"]) else np.nan,
                }
            )

    results_df = pd.DataFrame(results_rows)
    if not results_df.empty:
        results_df["Directional Edge"] = (results_df["Setup Score"] - 50.0).abs()
        results_df["Ranking Score"] = results_df["Directional Edge"] * (0.75 + 0.25 * results_df["Confidence"])
        results_df = results_df.sort_values(["Ranking Score", "Setup Score"], ascending=[False, False]).reset_index(drop=True)
        results_df["Class Rank"] = results_df.groupby("Asset Class").cumcount() + 1
    st.session_state["alpha_momentum_results"] = results_df
    st.session_state["alpha_momentum_histories"] = histories
    st.session_state["alpha_momentum_backtests"] = pd.DataFrame(backtests)
    st.session_state["alpha_momentum_trades"] = pd.concat(trades_log, ignore_index=True) if trades_log else pd.DataFrame()
    st.session_state["alpha_momentum_failures"] = failures
    st.session_state["alpha_momentum_timeframe"] = timeframe
    st.session_state["alpha_momentum_asset_classes"] = selected_asset_classes
    st.session_state["alpha_momentum_long_threshold"] = float(long_threshold)
    st.session_state["alpha_momentum_short_threshold"] = float(short_threshold)

results_df = st.session_state.get("alpha_momentum_results", pd.DataFrame())
histories = st.session_state.get("alpha_momentum_histories", {})
backtest_df = st.session_state.get("alpha_momentum_backtests", pd.DataFrame())
trades_df = st.session_state.get("alpha_momentum_trades", pd.DataFrame())
failures = st.session_state.get("alpha_momentum_failures", [])
active_timeframe = st.session_state.get("alpha_momentum_timeframe", timeframe)
active_asset_classes = st.session_state.get("alpha_momentum_asset_classes", selected_asset_classes)
active_long_threshold = float(st.session_state.get("alpha_momentum_long_threshold", long_threshold))
active_short_threshold = float(st.session_state.get("alpha_momentum_short_threshold", short_threshold))
results_df = _ensure_results_schema(results_df)
results_df["Directional Edge"] = (results_df["Setup Score"] - 50.0).abs()
results_df["Ranking Score"] = results_df["Directional Edge"] * (0.75 + 0.25 * results_df["Confidence"])
results_df = results_df.sort_values(["Ranking Score", "Setup Score"], ascending=[False, False]).reset_index(drop=True)
results_df["Class Rank"] = results_df.groupby("Asset Class").cumcount() + 1
st.session_state["alpha_momentum_results"] = results_df

if active_asset_classes:
    filtered_results_df = results_df[results_df["Asset Class"].isin(active_asset_classes)].copy()
else:
    filtered_results_df = pd.DataFrame()

if isinstance(backtest_df, pd.DataFrame) and not backtest_df.empty and active_asset_classes:
    backtest_df = backtest_df[backtest_df["Asset Class"].isin(active_asset_classes)].copy()
if isinstance(trades_df, pd.DataFrame) and not trades_df.empty and active_asset_classes:
    trades_df = trades_df[trades_df["Asset Class"].isin(active_asset_classes)].copy()

if results_df.empty:
    st.warning("No assets returned enough clean data to compute the matrix.")
    if failures:
        with st.expander("Diagnostics", expanded=False):
            for failure in failures:
                st.write(f"- {failure}")
    st.stop()

if filtered_results_df.empty:
    st.warning("No assets match the selected asset-class filter.")
    st.stop()

long_count = int((filtered_results_df["Setup Score"] >= active_long_threshold).sum())
short_count = int((filtered_results_df["Setup Score"] <= active_short_threshold).sum())
compression_count = int((filtered_results_df["Setup"] == "Compression").sum())
long_entry_count = int((filtered_results_df["Alert"] == "Long Entry").sum())
short_entry_count = int((filtered_results_df["Alert"] == "Short Entry").sum())
exit_count = int(filtered_results_df["Alert"].isin(["Long Exit", "Short Exit"]).sum())
leader = filtered_results_df.iloc[0]
breadth = ((filtered_results_df["Setup Score"] > active_long_threshold).sum() - (filtered_results_df["Setup Score"] < active_short_threshold).sum()) / max(len(filtered_results_df), 1)
breadth_label = "Bullish" if breadth > 0.15 else "Bearish" if breadth < -0.15 else "Balanced"
class_leaders = (
    filtered_results_df.sort_values(["Ranking Score", "Setup Score"], ascending=[False, False])
    .drop_duplicates(subset=["Asset Class"])
    .reset_index(drop=True)
)

c1, c2, c3, c4 = st.columns([1, 1, 1, 1.4])
c1.metric("Assets Shown", f"{len(filtered_results_df)}/{len(results_df)}")
c2.metric("Long Bias", f"{long_count}")
c3.metric("Short Bias", f"{short_count}")
c4.metric("Top Alert", f"{leader['Asset']} ({leader['Alert']})")

d1, d2, d3, d4 = st.columns([1, 1, 1.2, 1])
d1.metric("Compressions", f"{compression_count}")
d2.metric("Timeframe", active_timeframe)
d3.metric("Breadth", breadth_label, f"{breadth:+.0%}")
d4.metric("Median Confidence", f"{filtered_results_df['Confidence'].median():.2f}")

e1, e2, e3, e4 = st.columns(4)
e1.metric("Long Entries", f"{long_entry_count}")
e2.metric("Short Entries", f"{short_entry_count}")
e3.metric("Exit Alerts", f"{exit_count}")
e4.metric("Thresholds", f"{active_long_threshold:.0f}/{active_short_threshold:.0f}")

if not class_leaders.empty:
    st.subheader("Class Leaders")
    for start in range(0, len(class_leaders), 4):
        chunk = class_leaders.iloc[start : start + 4]
        cols = st.columns(len(chunk))
        for col, (_, row) in zip(cols, chunk.iterrows()):
            col.metric(str(row["Asset Class"]), str(row["Asset"]), f'{row["Alert"]} | {row["Setup Score"]:.1f}')

display_df = (
    filtered_results_df.drop(columns=["Directional Edge", "Ranking Score"], errors="ignore")
    .head(top_n)
    .copy()
)
render_signal_board(display_df)

csv_bytes = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download current radar as CSV",
    data=csv_bytes,
    file_name=f"alpha_momentum_matrix_{active_timeframe}.csv",
    mime="text/csv",
)

st.plotly_chart(build_scatter_chart(display_df), use_container_width=True, config={"displayModeBar": False})

valid_backtests = pd.DataFrame()
if isinstance(backtest_df, pd.DataFrame) and not backtest_df.empty:
    valid_backtests = backtest_df.copy()
    for column, default_value in {"Asset Class": "Unknown", "Signals": 0, "Hit Rate": np.nan, "Avg Return %": np.nan}.items():
        if column not in valid_backtests.columns:
            valid_backtests[column] = default_value
    for column in ["Signals", "Hit Rate", "Avg Return %"]:
        if column in valid_backtests.columns:
            valid_backtests[column] = pd.to_numeric(valid_backtests[column], errors="coerce")
    valid_backtests = valid_backtests[valid_backtests["Signals"].fillna(0) > 0]

if not valid_backtests.empty:
    total_signals = int(valid_backtests["Signals"].sum())
    weighted_hit_rate = float((valid_backtests["Hit Rate"] * valid_backtests["Signals"]).sum() / total_signals)
    weighted_avg_return = float((valid_backtests["Avg Return %"] * valid_backtests["Signals"]).sum() / total_signals)
    best_backtest_row = valid_backtests.sort_values("Avg Return %", ascending=False).iloc[0]

    st.subheader("Backtest Snapshot")
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Signals", f"{total_signals}")
    b2.metric("Hit Rate", f"{weighted_hit_rate:.1%}")
    b3.metric("Avg Signal Return", f"{weighted_avg_return:+.2f}%")
    b4.metric("Best Asset", str(best_backtest_row["Asset"]), f'{best_backtest_row["Avg Return %"]:+.2f}%')

    class_backtest_rows: list[dict[str, object]] = []
    for asset_class, group in valid_backtests.groupby("Asset Class", dropna=False):
        group_signals = int(group["Signals"].sum())
        class_backtest_rows.append(
            {
                "Asset Class": asset_class,
                "Signals": group_signals,
                "Hit Rate": (group["Hit Rate"] * group["Signals"]).sum() / max(group_signals, 1),
                "Avg Return %": (group["Avg Return %"] * group["Signals"]).sum() / max(group_signals, 1),
            }
        )
    class_backtest = pd.DataFrame(class_backtest_rows)
    st.dataframe(class_backtest, use_container_width=True, hide_index=True)
    if isinstance(trades_df, pd.DataFrame) and not trades_df.empty:
        st.plotly_chart(build_equity_curve_chart(trades_df), use_container_width=True, config={"displayModeBar": False})
else:
    st.info("Backtest snapshot will appear after the current scan generates entry signals.")

selected_symbol = st.selectbox("Inspect asset", display_df["Asset"].tolist(), index=0)
selected_history = histories.get(selected_symbol)
if selected_history is not None and not selected_history.empty:
    st.plotly_chart(build_overview_chart(selected_symbol, selected_history), use_container_width=True, config={"displayModeBar": False})

if failures:
    with st.expander("Diagnostics", expanded=False):
        for failure in failures:
            st.write(f"- {failure}")

with st.expander("Methodology", expanded=False):
    st.markdown(
        """
- `4h` is built by explicit `1h -> 4h` OHLCV resampling, so the timeframe is temporally honest instead of a relabeled `1h`.
- `Momentum Z`, `Acceleration Z`, `Trend Z`, and `RVOL Z` use a causal rolling baseline that only looks at prior bars.
- `Squeeze` uses Bollinger Bands inside Keltner Channels, and the post-release boost only survives for a short decay window after a real compression.
- `Regime` now requires price above or below `EMA200`, confirmation from `EMA50`, and a slower `EMA200` slope so it does not flip on one noisy bar.
- `Alerts` convert the score into explicit `Long Entry`, `Short Entry`, `Exit`, and `Watch` states using score transitions plus regime confirmation.
- `Asset Class` labels let the dashboard rank crypto, futures, indices, and equities without losing class context.
- `Thresholds` are configurable from the sidebar, so long/short interpretation can be tightened or relaxed without changing the code.
- `Asset-class filters` let you inspect only the slices of the market you want while keeping the full scan in memory.
- `Backtest Snapshot` measures forward returns after entry alerts so you can judge whether the current signal logic has recent follow-through.
- `Equity Curve` compounds historical alert returns trade by trade, so you can see whether the edge is stable or just episodic.
- `Setup Score` is bounded from `0` to `100` with `tanh`, which keeps tails informative without letting a single component dominate.
- `Auto-adjusted` OHLC reduces split and dividend contamination for equities when mixing stocks, futures, and crypto in one watchlist.
- `Confidence` is a secondary quality readout, not a trading signal. It rewards cleaner trend alignment and stronger directional separation.
        """.strip()
    )

st.caption(
    "Data source: Yahoo Finance public market data. Cross-asset dashboards remain heuristic by nature, "
    "so the score is best used for ranking within a watchlist rather than as a universal forecast probability."
)
