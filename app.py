"""
AegisFlow — Graph-Powered Financial Fraud Intelligence Platform.
Main Streamlit Entrypoint.
Run with:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from dashboard.styles import apply_custom_styles, render_executive_overview
from dashboard.views.account_monitoring import render_account_monitoring
from dashboard.views.analytics_overview import render_analytics_overview
from dashboard.views.fraud_rings import render_fraud_rings
from dashboard.views.network_graph import render_network_graph
from dashboard.views.transaction_monitoring import render_transaction_monitoring
from database.seed import generate_initial_dataset
from engine.pipeline import FraudIntelligencePipeline

st.set_page_config(
    page_title="AegisFlow | Graph-Powered Financial Fraud Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    apply_custom_styles()

    pipeline = FraudIntelligencePipeline()

    # Auto-seed initial dataset if database has no transactions
    if not pipeline.db.get_transactions(limit=1):
        with st.spinner("Loading AegisFlow Fraud Intelligence..."):
            pipeline.run_full_pipeline(generate_initial_dataset())

    state = pipeline.get_current_state()

    # -------------------------------------------------------------------------
    # Clean, Minimal Fintech Sidebar
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("## 🛡️ AegisFlow")
        st.caption("Graph-Powered Financial Fraud Intelligence Platform")
        st.markdown("---")

        section = st.radio(
            "Platform Sections",
            options=[
                "Live Transactions",
                "Account Risk Analysis",
                "Coordinated Fraud Networks",
                "Network Visualization",
                "Intelligence Insights",
            ],
            index=0,
        )

        st.markdown("---")
        st.markdown("### 🟢 System Status")
        if state["db_mode"] == "supabase":
            st.success("Online — Supabase Connected")
        else:
            st.info("Online — Local Engine Active")

        st.caption(
            f"**{len(state['transactions'])}** Transactions  •  "
            f"**{len(state['accounts'])}** Accounts  •  "
            f"**{len(state['fraud_rings'])}** Fraud Rings"
        )

        st.markdown("---")
        st.markdown(
            """
            <div style="font-size:0.82rem; color:#94A3B8; line-height:1.6;">
                <strong style="color:#F8FAFC;">Risk Color Key</strong><br/>
                <span style="color:#10B981;">● Green (0–40):</span> Safe → Approve<br/>
                <span style="color:#F59E0B;">● Yellow (41–70):</span> Medium Risk → OTP<br/>
                <span style="color:#EF4444;">● Red (71–100):</span> High Risk → Hold / Block
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # Top-Level Dashboard Overview (Always Visible for 10-Second Judge Comprehension)
    # -------------------------------------------------------------------------
    render_executive_overview(state)
    st.markdown("---")

    # -------------------------------------------------------------------------
    # Section Router
    # -------------------------------------------------------------------------
    if section == "Live Transactions":
        render_transaction_monitoring(state, pipeline)
    elif section == "Account Risk Analysis":
        render_account_monitoring(state)
    elif section == "Coordinated Fraud Networks":
        render_fraud_rings(state)
    elif section == "Network Visualization":
        render_network_graph(state)
    elif section == "Intelligence Insights":
        render_analytics_overview(state)


if __name__ == "__main__":
    main()
