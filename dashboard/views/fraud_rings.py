"""
Section: Coordinated Fraud Networks (formerly Fraud Rings).
Displays detected fraud rings with:
- Ring ID
- Risk Score
- Accounts Involved
- Shared Devices
- Shared Merchants
- Pattern Detected
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from dashboard.styles import COLOR_HIGH, format_risk_badge_html


def _extract_shared_entities(tx_df: pd.DataFrame, accounts: List[str], col_name: str) -> List[str]:
    """Find devices or merchants shared by 2+ accounts in the ring (or top entities used by the ring)."""
    if tx_df.empty or not accounts:
        return []
    sub = tx_df[tx_df["account_id"].astype(str).isin(accounts)]
    if sub.empty:
        return []
    counts = sub.groupby(col_name)["account_id"].nunique()
    shared = sorted(counts[counts >= 2].index.astype(str).tolist())
    if shared:
        return shared
    return sorted(sub[col_name].astype(str).unique().tolist()[:2])


def render_fraud_rings(state: Dict[str, Any]) -> None:
    """Render the Coordinated Fraud Networks view."""
    st.markdown('<div class="section-title">🕸️ Coordinated Fraud Networks</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        "Groups of connected accounts automatically detected sharing devices, merchants, or synchronized payment behavior."
        "</div>",
        unsafe_allow_html=True,
    )

    rings: List[Dict[str, Any]] = state["fraud_rings"]
    tx_df: pd.DataFrame = state["transactions_df"]

    if not rings:
        st.success("No coordinated fraud networks detected.")
        return

    # Enrich each ring with Shared Devices and Shared Merchants
    enriched_rows: List[Dict[str, Any]] = []
    for ring in rings:
        accs = [str(a) for a in ring.get("accounts_involved", [])]
        shared_devices = _extract_shared_entities(tx_df, accs, "device_id")
        shared_merchants = _extract_shared_entities(tx_df, accs, "merchant_id")

        enriched_rows.append(
            {
                "Ring ID": str(ring["ring_id"]),
                "Risk Score": float(ring["ring_risk_score"]),
                "Accounts Involved": ", ".join(accs),
                "Shared Devices": ", ".join(shared_devices) if shared_devices else "None",
                "Shared Merchants": ", ".join(shared_merchants) if shared_merchants else "None",
                "Pattern Detected": str(ring["pattern_detected"]),
            }
        )

    # -------------------------------------------------------------------------
    # 1. Large Readable Fraud Ring Cards
    # -------------------------------------------------------------------------
    for item in enriched_rows:
        badge = format_risk_badge_html(item["Risk Score"])
        st.markdown(
            f"""
            <div class="fintech-card" style="border-left: 4px solid {COLOR_HIGH};">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                    <div style="font-size:1.15rem; font-weight:700; color:#F8FAFC;">
                        {item['Ring ID']}
                    </div>
                    <div>{badge}</div>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:1rem; margin-top:0.85rem;">
                    <div>
                        <div style="color:#94A3B8; font-size:0.78rem; text-transform:uppercase;">Accounts Involved</div>
                        <div style="color:#F8FAFC; font-weight:600; margin-top:0.2rem;">{item['Accounts Involved']}</div>
                    </div>
                    <div>
                        <div style="color:#94A3B8; font-size:0.78rem; text-transform:uppercase;">Shared Devices</div>
                        <div style="color:#38BDF8; font-weight:600; margin-top:0.2rem;">{item['Shared Devices']}</div>
                    </div>
                    <div>
                        <div style="color:#94A3B8; font-size:0.78rem; text-transform:uppercase;">Shared Merchants</div>
                        <div style="color:#A855F7; font-weight:600; margin-top:0.2rem;">{item['Shared Merchants']}</div>
                    </div>
                </div>
                <div style="margin-top:0.85rem; padding-top:0.65rem; border-top:1px solid rgba(255,255,255,0.07); color:#E2E8F0; font-size:0.88rem;">
                    <strong>Pattern Detected:</strong> {item['Pattern Detected']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # 2. Clean Summary Table (Exact Required Columns)
    # -------------------------------------------------------------------------
    st.markdown("#### Fraud Ring Summary Table")
    rings_df = pd.DataFrame(enriched_rows)
    st.dataframe(
        rings_df[
            [
                "Ring ID",
                "Risk Score",
                "Accounts Involved",
                "Shared Devices",
                "Shared Merchants",
                "Pattern Detected",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ring ID": st.column_config.TextColumn("Ring ID", width="small"),
            "Risk Score": st.column_config.ProgressColumn(
                "Risk Score",
                min_value=0,
                max_value=100,
                format="%.0f / 100",
                width="small",
            ),
            "Accounts Involved": st.column_config.TextColumn("Accounts Involved", width="medium"),
            "Shared Devices": st.column_config.TextColumn("Shared Devices", width="small"),
            "Shared Merchants": st.column_config.TextColumn("Shared Merchants", width="medium"),
            "Pattern Detected": st.column_config.TextColumn("Pattern Detected", width="large"),
        },
    )
