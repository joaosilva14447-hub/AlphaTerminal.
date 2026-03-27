st.markdown(
    """
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] {
        background-color: #161616;
        padding: 16px;
        border-radius: 6px;
        border: 1px solid #2A2A2A;
    }
    .stDataFrame { background-color: #161616; border-radius: 6px; }
    .signal-board {
        margin-top: 12px;
        padding: 22px;
        border-radius: 18px;
        border: 1px solid rgba(76, 125, 255, 0.18);
        background:
            radial-gradient(circle at top right, rgba(76, 125, 255, 0.16), transparent 28%),
            linear-gradient(180deg, rgba(19, 24, 33, 0.98), rgba(10, 13, 18, 0.98));
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.28);
    }
    .signal-board-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        margin-bottom: 18px;
    }
    .signal-board-title {
        color: #EAF2FF;
        font-size: 1.08rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .signal-board-subtitle {
        color: #8D9AAF;
        font-size: 0.86rem;
    }
    .signal-board-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 18px;
    }
    .signal-card {
        padding: 16px 18px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        background: linear-gradient(180deg, rgba(24, 29, 38, 0.96), rgba(14, 17, 24, 0.96));
    }
    .signal-card-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 10px;
    }
    .signal-rank {
        color: #6E7B91;
        font-size: 0.78rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .signal-asset {
        color: #F7FAFF;
        font-size: 1.28rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .signal-score-pill {
        min-width: 70px;
        padding: 8px 10px;
        border-radius: 999px;
        text-align: center;
        font-weight: 800;
        font-size: 0.98rem;
        color: #F7FAFF;
    }
    .signal-card-setup {
        margin-bottom: 12px;
        color: #D8E2F2;
        font-size: 0.95rem;
        font-weight: 600;
    }
    .signal-card-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
    }
    .signal-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        border: 1px solid transparent;
    }
    .badge-bull {
        color: #7CFFD1;
        background: rgba(0, 255, 170, 0.10);
        border-color: rgba(0, 255, 170, 0.20);
    }
    .badge-bear {
        color: #FFB18B;
        background: rgba(255, 92, 92, 0.10);
        border-color: rgba(255, 92, 92, 0.22);
    }
    .badge-range {
        color: #C7D0DB;
        background: rgba(141, 154, 175, 0.12);
        border-color: rgba(141, 154, 175, 0.22);
    }
    .badge-compression {
        color: #A9BCFF;
        background: rgba(76, 125, 255, 0.12);
        border-color: rgba(76, 125, 255, 0.26);
    }
    .badge-neutral {
        color: #D5DEEB;
        background: rgba(199, 208, 219, 0.10);
        border-color: rgba(199, 208, 219, 0.16);
    }
    .signal-card-stats {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
    }
    .signal-stat-label {
        color: #7F8A9E;
        font-size: 0.70rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }
    .signal-stat-value {
        color: #F3F7FD;
        font-size: 0.98rem;
        font-weight: 700;
    }
    .signal-table {
        overflow: hidden;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        background: rgba(8, 10, 14, 0.65);
    }
    .signal-table table {
        width: 100%;
        border-collapse: collapse;
    }
    .signal-table thead th {
        padding: 12px 14px;
        text-align: left;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: #7F8A9E;
        background: rgba(255, 255, 255, 0.03);
    }
    .signal-table tbody tr {
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    .signal-table tbody tr:nth-child(odd) {
        background: rgba(255, 255, 255, 0.015);
    }
    .signal-table tbody tr:hover {
        background: rgba(76, 125, 255, 0.08);
    }
    .signal-table td {
        padding: 14px;
        color: #EAF2FF;
        font-size: 0.95rem;
        vertical-align: middle;
    }
    .rank-cell {
        color: #6E7B91;
        font-weight: 700;
        width: 48px;
    }
    .asset-cell {
        font-weight: 800;
        font-size: 1.02rem;
        letter-spacing: 0.02em;
    }
    .score-cell {
        min-width: 190px;
    }
    .score-shell {
        position: relative;
        height: 11px;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.08);
        margin-bottom: 8px;
    }
    .score-fill {
        height: 100%;
        border-radius: 999px;
    }
    .score-text {
        font-size: 0.90rem;
        font-weight: 700;
        color: #F7FAFF;
    }
    .metric-pos { color: #7CFFD1; font-weight: 700; }
    .metric-neg { color: #FFB18B; font-weight: 700; }
    .metric-flat { color: #D5DEEB; font-weight: 700; }
    @media (max-width: 1100px) {
        .signal-board-grid { grid-template-columns: 1fr; }
        .signal-card-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .signal-table { overflow-x: auto; }
    }
</style>
""",
    unsafe_allow_html=True,
)
