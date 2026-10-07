"""
Section: Account Risk Analysis (formerly Account Monitoring).
Displays clean account-level fraud assessment with:
- Account ID
- Risk Score
- Risk Level (Safe / Medium Risk / High Risk)
- Number of Suspicious Transactions
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from dashboard.styles import format_risk_badge_html, get_risk_level_and_color


def render_account_monitoring(state: Dict[str, Any]) -> None:
    """Render the clean Account Risk Analysis section."""
    st.markdown('<div class="section-title">👤 Account Risk Analysis</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        "Aggregated account risk profiles based on historical transaction behavior and network links."
        "</div>",
        unsafe_allow_html=True,
    )

    acc_df: pd.DataFrame = state["accounts_df"]
    tx_df: pd.DataFrame = state["transactions_df"]

    if acc_df.empty:
        st.info("No accounts available.")
        return

    # Compute Number of Suspicious Transactions (risk_score > 40) per account
    suspicious_counts: Dict[str, int] = {}
    if not tx_df.empty:
        susp_df = tx_df[tx_df["risk_score"] > 40.0]
        suspicious_counts = susp_df.groupby("account_id").size().to_dict()

    work = acc_df.copy()
    work["Risk Level"] = work["account_risk_score"].apply(
        lambda s: get_risk_level_and_color(float(s))[0]
    )
    work["Number of Suspicious Transactions"] = work["account_id"].apply(
        lambda aid: int(suspicious_counts.get(str(aid), 0))
    )

    # -------------------------------------------------------------------------
    # 1. Highlight Cards for Top High-Risk Accounts
    # -------------------------------------------------------------------------
    st.markdown("#### Priority Accounts Requiring Review")
    top_accounts = work.sort_values("account_risk_score", ascending=False).head(3)
    cols = st.columns(3)
    for col, (_, row) in zip(cols, top_accounts.iterrows()):
        score = float(row["account_risk_score"])
        badge_html = format_risk_badge_html(score)
        susp_cnt = int(row["Number of Suspicious Transactions"])
        with col:
            st.markdown(
                f"""
                <div class="fintech-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:#F8FAFC; font-size:1.05rem;">{row['account_id']}</strong>
                        {badge_html}
                    </div>
                    <div style="margin-top:0.65rem; color:#F8FAFC; font-size:1.35rem; font-weight:700;">
                        {susp_cnt} Suspicious Transactions
                    </div>
                    <div style="margin-top:0.4rem; color:#94A3B8; font-size:0.84rem; min-height:2.4rem;">
                        {row['explanation']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------------------
    # 2. Clean Account Risk Table (Exact Required Columns)
    # -------------------------------------------------------------------------
    level_filter = st.selectbox(
        "Filter Accounts by Risk Level",
        options=["All Accounts", "High Risk", "Medium Risk", "Safe"],
    )

    filtered = work.copy()
    if level_filter != "All Accounts":
        filtered = filtered[filtered["Risk Level"] == level_filter]

    display_df = filtered[
        [
            "account_id",
            "account_risk_score",
            "Risk Level",
            "Number of Suspicious Transactions",
            "explanation",
        ]
    ].rename(
        columns={
            "account_id": "Account ID",
            "account_risk_score": "Risk Score",
            "explanation": "Risk Summary",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Account ID": st.column_config.TextColumn("Account ID", width="small"),
            "Risk Score": st.column_config.ProgressColumn(
                "Risk Score",
                min_value=0,
                max_value=100,
                format="%.0f / 100",
                width="small",
            ),
            "Risk Level": st.column_config.TextColumn("Risk Level", width="small"),
            "Number of Suspicious Transactions": st.column_config.NumberColumn(
                "Number of Suspicious Transactions",
                format="%d",
                width="medium",
            ),
            "Risk Summary": st.column_config.TextColumn("Risk Summary", width="large"),
        },
        height=420,
    )
