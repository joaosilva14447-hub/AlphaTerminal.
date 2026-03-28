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
                f'<td><span class="signal-badge {_badge_class(str(row_data["Setup"]), "Setup")}">{html.escape(str(row_data["Setup"]))}</span></td>'
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
        "<th>#</th><th>Asset</th><th>Setup</th><th>Bias</th><th>Regime</th><th>Score</th>"
        "<th>Momentum</th><th>Accel</th><th>Trend</th><th>RVOL</th><th>SQZ</th><th>Data</th>"
        f'</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div></div>'
    )
    st.markdown(board_html, unsafe_allow_html=True)
