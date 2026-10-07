"""
Section: Live Transactions (formerly Transaction Monitoring).
Displays business-focused transaction risk intelligence with:
- Transaction ID
- Amount
- Risk Score
- Explanation
- Recommended Action
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from dashboard.styles import (
    COLOR_HIGH,
    COLOR_MEDIUM,
    COLOR_SAFE,
    format_action_badge_html,
    format_risk_badge_html,
    get_risk_level_and_color,
)


def render_transaction_monitoring(state: Dict[str, Any], pipeline: Any = None) -> None:
    """Render the clean, modern Live Transactions view."""
    st.markdown('<div class="section-title">💳 Live Transactions</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        "Real-time risk scoring, plain-English explanations, and automated payment decisions for every transaction."
        "</div>",
        unsafe_allow_html=True,
    )

    if pipeline is not None:
        with st.expander("➕ Add New Transaction to Supabase", expanded=False):
            with st.form("add_transaction_form", clear_on_submit=False):
                c_a, c_b, c_c, c_d, c_e = st.columns(5)
                with c_a:
                    in_account = st.text_input("Account ID", value="ACC-2001")
                with c_b:
                    in_amount = st.number_input("Amount ($)", min_value=1.0, max_value=500000.0, value=4500.0, step=50.0)
                with c_c:
                    in_merchant = st.text_input("Merchant ID", value="MER-APPLE-STORE")
                with c_d:
                    in_device = st.text_input("Device ID", value="DEV-MULE-X99")
                with c_e:
                    in_location = st.selectbox(
                        "Location",
                        [
                            "New York, US",
                            "London, UK",
                            "San Francisco, US",
                            "Lagos, NG",
                            "Cayman Islands",
                            "Macau, CN",
                            "Panama City, PA",
                        ],
                    )
                submit_tx = st.form_submit_button("Submit & Score Transaction", use_container_width=True)
                if submit_tx:
                    res = pipeline.ingest_realtime_transaction(
                        {
                            "account_id": in_account.strip(),
                            "amount": float(in_amount),
                            "merchant_id": in_merchant.strip(),
                            "device_id": in_device.strip(),
                            "location": in_location,
                        }
                    )
                    tx_out = res["transaction"]
                    st.success(
                        f"Saved {tx_out['transaction_id']} to Supabase → "
                        f"Risk Score: {tx_out['risk_score']:.0f}/100 ({tx_out['action']}) | {tx_out['explanation']}"
                    )
                    st.rerun()

    tx_df: pd.DataFrame = state["transactions_df"]
    if tx_df.empty:
        st.info("No transactions available.")
        return

    # Add Risk Level label (Safe / Medium Risk / High Risk)
    work_df = tx_df.copy()
    work_df["risk_level"] = work_df["risk_score"].apply(lambda s: get_risk_level_and_color(float(s))[0])

    # -------------------------------------------------------------------------
    # 1. Business Insights Strip (Safe / Medium Risk / High Risk Breakdown)
    # -------------------------------------------------------------------------
    safe_count = int((work_df["risk_level"] == "Safe").sum())
    med_count = int((work_df["risk_level"] == "Medium Risk").sum())
    high_count = int((work_df["risk_level"] == "High Risk").sum())

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""
            <div class="fintech-card" style="border-left: 4px solid {COLOR_SAFE};">
                <div style="color:{COLOR_SAFE}; font-weight:700; font-size:0.85rem;">● SAFE TRANSACTIONS (0–40)</div>
                <div style="color:#F8FAFC; font-size:1.65rem; font-weight:700; margin-top:0.25rem;">{safe_count:,} Approved</div>
                <div style="color:#94A3B8; font-size:0.82rem; margin-top:0.2rem;">Cleared automatically with zero customer friction</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="fintech-card" style="border-left: 4px solid {COLOR_MEDIUM};">
                <div style="color:{COLOR_MEDIUM}; font-weight:700; font-size:0.85rem;">● MEDIUM RISK (41–70)</div>
                <div style="color:#F8FAFC; font-size:1.65rem; font-weight:700; margin-top:0.25rem;">{med_count:,} Step-Up OTP</div>
                <div style="color:#94A3B8; font-size:0.82rem; margin-top:0.2rem;">Verified via automated one-time passcode</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="fintech-card" style="border-left: 4px solid {COLOR_HIGH};">
                <div style="color:{COLOR_HIGH}; font-weight:700; font-size:0.85rem;">● HIGH RISK (71–100)</div>
                <div style="color:#F8FAFC; font-size:1.65rem; font-weight:700; margin-top:0.25rem;">{high_count:,} Held or Blocked</div>
                <div style="color:#94A3B8; font-size:0.82rem; margin-top:0.2rem;">Stopped before funds leave the platform</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # 2. Recent High-Risk Transaction Spotlights (Readable Cards)
    # -------------------------------------------------------------------------
    st.markdown("#### 🚨 Recent Flagged Transactions")
    top_flagged = work_df.sort_values("risk_score", ascending=False).head(3)
    s_cols = st.columns(3)
    for col, (_, row) in zip(s_cols, top_flagged.iterrows()):
        score = float(row["risk_score"])
        risk_badge = format_risk_badge_html(score)
        action_badge = format_action_badge_html(str(row["action"]))
        with col:
            st.markdown(
                f"""
                <div class="fintech-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:#F8FAFC; font-size:1rem;">{row['transaction_id']}</strong>
                        {risk_badge}
                    </div>
                    <div style="font-size:1.45rem; font-weight:700; color:#F8FAFC; margin:0.55rem 0;">
                        ${float(row['amount']):,.2f}
                    </div>
                    <div style="color:#CBD5E1; font-size:0.84rem; min-height:2.6rem;">
                        <strong>Why Flagged:</strong> {row['explanation']}
                    </div>
                    <div style="margin-top:0.75rem; padding-top:0.6rem; border-top:1px solid rgba(255,255,255,0.07); display:flex; justify-content:space-between; align-items:center;">
                        <span style="color:#94A3B8; font-size:0.8rem;">Recommended Action</span>
                        {action_badge}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------------------
    # 3. Clean Transaction Table (Exact Required Columns)
    # -------------------------------------------------------------------------
    f1, f2 = st.columns([1.2, 1.8])
    with f1:
        risk_filter = st.selectbox(
            "Filter by Risk Level",
            options=["All Transactions", "High Risk (71–100)", "Medium Risk (41–70)", "Safe (0–40)"],
        )
    with f2:
        search_txt = st.text_input("Search Transaction ID or Explanation", placeholder="e.g. TX-1060, Unusually high amount")

    filtered = work_df.copy()
    if risk_filter == "High Risk (71–100)":
        filtered = filtered[filtered["risk_level"] == "High Risk"]
    elif risk_filter == "Medium Risk (41–70)":
        filtered = filtered[filtered["risk_level"] == "Medium Risk"]
    elif risk_filter == "Safe (0–40)":
        filtered = filtered[filtered["risk_level"] == "Safe"]

    if search_txt.strip():
        q = search_txt.strip().lower()
        filtered = filtered[
            filtered["transaction_id"].astype(str).str.lower().str.contains(q)
            | filtered["explanation"].astype(str).str.lower().str.contains(q)
            | filtered["action"].astype(str).str.lower().str.contains(q)
        ]

    display_df = filtered[
        ["transaction_id", "amount", "risk_score", "explanation", "action"]
    ].rename(
        columns={
            "transaction_id": "Transaction ID",
            "amount": "Amount",
            "risk_score": "Risk Score",
            "explanation": "Explanation",
            "action": "Recommended Action",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Transaction ID": st.column_config.TextColumn("Transaction ID", width="small"),
            "Amount": st.column_config.NumberColumn("Amount", format="$%.2f", width="small"),
            "Risk Score": st.column_config.ProgressColumn(
                "Risk Score",
                min_value=0,
                max_value=100,
                format="%.0f / 100",
                width="small",
            ),
            "Explanation": st.column_config.TextColumn("Explanation", width="large"),
            "Recommended Action": st.column_config.TextColumn("Recommended Action", width="medium"),
        },
        height=420,
    )
