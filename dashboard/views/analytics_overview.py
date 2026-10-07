"""
Section: Intelligence Insights (formerly Analytics Overview).
Displays four executive charts:
1. Risk distribution chart
2. Fraud vs Legitimate transactions
3. Top risky accounts
4. Top risky merchants
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.styles import COLOR_HIGH, COLOR_MEDIUM, COLOR_SAFE, get_risk_level_and_color


def render_analytics_overview(state: Dict[str, Any]) -> None:
    """Render the clean Intelligence Insights section."""
    st.markdown('<div class="section-title">📊 Intelligence Insights</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        "Visual breakdown of transaction risk distribution, fraud vs. legitimate volume, and top risk exposures."
        "</div>",
        unsafe_allow_html=True,
    )

    tx_df: pd.DataFrame = state["transactions_df"]
    acc_df: pd.DataFrame = state["accounts_df"]

    if tx_df.empty:
        st.info("No data available for analytics.")
        return

    work_tx = tx_df.copy()
    work_tx["Risk Level"] = work_tx["risk_score"].apply(lambda s: get_risk_level_and_color(float(s))[0])
    work_tx["Category"] = work_tx["risk_score"].apply(
        lambda s: "Legitimate (Safe)"
        if float(s) <= 40.0
        else ("Suspicious (Medium Risk)" if float(s) <= 70.0 else "Fraudulent / High Risk")
    )

    color_map = {
        "Safe": COLOR_SAFE,
        "Medium Risk": COLOR_MEDIUM,
        "High Risk": COLOR_HIGH,
    }

    # -------------------------------------------------------------------------
    # Row 1: Risk Distribution Chart & Fraud vs Legitimate Transactions
    # -------------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 1. Risk Distribution Chart")
        fig_dist = px.histogram(
            work_tx,
            x="risk_score",
            color="Risk Level",
            nbins=20,
            color_discrete_map=color_map,
            category_orders={"Risk Level": ["Safe", "Medium Risk", "High Risk"]},
            labels={"risk_score": "Risk Score (0–100)", "count": "Transactions"},
        )
        fig_dist.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F8FAFC"),
            margin=dict(t=15, b=20, l=10, r=10),
            height=340,
            xaxis=dict(range=[0, 102], gridcolor="rgba(148,163,184,0.12)"),
            yaxis=dict(title="Number of Transactions", gridcolor="rgba(148,163,184,0.12)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    with col2:
        st.markdown("#### 2. Fraud vs Legitimate Transactions")
        cat_counts = (
            work_tx["Category"]
            .value_counts()
            .reindex(
                ["Legitimate (Safe)", "Suspicious (Medium Risk)", "Fraudulent / High Risk"],
                fill_value=0,
            )
            .reset_index()
        )
        cat_counts.columns = ["Category", "Transactions"]

        fig_pie = px.pie(
            cat_counts,
            names="Category",
            values="Transactions",
            hole=0.58,
            color="Category",
            color_discrete_map={
                "Legitimate (Safe)": COLOR_SAFE,
                "Suspicious (Medium Risk)": COLOR_MEDIUM,
                "Fraudulent / High Risk": COLOR_HIGH,
            },
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F8FAFC"),
            margin=dict(t=15, b=20, l=10, r=10),
            height=340,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # -------------------------------------------------------------------------
    # Row 2: Top Risky Accounts & Top Risky Merchants
    # -------------------------------------------------------------------------
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("#### 3. Top Risky Accounts")
        if not acc_df.empty:
            top_acc = acc_df.copy()
            top_acc["Risk Level"] = top_acc["account_risk_score"].apply(
                lambda s: get_risk_level_and_color(float(s))[0]
            )
            top_acc = top_acc.sort_values("account_risk_score", ascending=True).tail(8)

            fig_acc = px.bar(
                top_acc,
                x="account_risk_score",
                y="account_id",
                orientation="h",
                color="Risk Level",
                color_discrete_map=color_map,
                labels={"account_risk_score": "Account Risk Score (0–100)", "account_id": "Account ID"},
            )
            fig_acc.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(t=15, b=20, l=10, r=10),
                height=350,
                xaxis=dict(range=[0, 105], gridcolor="rgba(148,163,184,0.12)"),
                showlegend=False,
            )
            st.plotly_chart(fig_acc, use_container_width=True)

    with col4:
        st.markdown("#### 4. Top Risky Merchants")
        mer_stats = (
            work_tx.groupby("merchant_id", as_index=False)
            .agg(avg_risk=("risk_score", "mean"), tx_count=("transaction_id", "count"))
            .sort_values("avg_risk", ascending=True)
            .tail(8)
        )
        mer_stats["Risk Level"] = mer_stats["avg_risk"].apply(
            lambda s: get_risk_level_and_color(float(s))[0]
        )

        fig_mer = px.bar(
            mer_stats,
            x="avg_risk",
            y="merchant_id",
            orientation="h",
            color="Risk Level",
            color_discrete_map=color_map,
            labels={"avg_risk": "Average Risk Score (0–100)", "merchant_id": "Merchant"},
        )
        fig_mer.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F8FAFC"),
            margin=dict(t=15, b=20, l=10, r=10),
            height=350,
            xaxis=dict(range=[0, 105], gridcolor="rgba(148,163,184,0.12)"),
            showlegend=False,
        )
        st.plotly_chart(fig_mer, use_container_width=True)
