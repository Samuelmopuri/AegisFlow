"""
Section: Network Visualization.
Interactive graph showing relationships between:
- Accounts
- Devices
- Merchants
- Locations
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import networkx as nx
import streamlit as st
import streamlit.components.v1 as components

from dashboard.graph_viz import build_pyvis_html
from dashboard.styles import COLOR_HIGH, COLOR_MEDIUM, COLOR_SAFE


def render_network_graph(state: Dict[str, Any]) -> None:
    """Render the clean Network Visualization view."""
    st.markdown('<div class="section-title">🌐 Network Visualization</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        "Interactive relationship map connecting Accounts, Devices, Merchants, and Locations."
        "</div>",
        unsafe_allow_html=True,
    )

    G: nx.Graph = state["graph"]
    rings: List[Dict[str, Any]] = state["fraud_rings"]

    if G.number_of_nodes() == 0:
        st.info("No network relationships available.")
        return

    # Simple, clean filter bar
    c1, c2 = st.columns([1.4, 2.0])
    with c1:
        ring_options = ["All Connected Entities"] + [
            f"{r['ring_id']} ({len(r.get('accounts_involved', []))} Accounts — Risk {float(r['ring_risk_score']):.0f})"
            for r in rings
        ]
        selected_view = st.selectbox("Select Network View", options=ring_options)

    with c2:
        layer_map = {
            "Accounts": "account",
            "Devices": "device",
            "Merchants": "merchant",
            "Locations": "location",
        }
        selected_labels = st.multiselect(
            "Visible Entity Types",
            options=list(layer_map.keys()),
            default=list(layer_map.keys()),
        )
        include_types = {layer_map[lbl] for lbl in selected_labels} if selected_labels else {"account"}

    focus_accounts: Optional[Set[str]] = None
    if selected_view != "All Connected Entities":
        ring_id = selected_view.split(" ")[0]
        matched = next((r for r in rings if r["ring_id"] == ring_id), None)
        if matched:
            focus_accounts = set(matched.get("accounts_involved", []))

    # Clean visual legend
    st.markdown(
        f"""
        <div class="fintech-card" style="padding:0.75rem 1.2rem; margin-bottom:0.8rem; font-size:0.85rem;">
            <strong style="color:#F8FAFC;">Legend:</strong>
            <span style="color:{COLOR_SAFE}; margin-left:1.1rem; font-weight:600;">● Safe Account (0–40)</span>
            <span style="color:{COLOR_MEDIUM}; margin-left:1.1rem; font-weight:600;">● Medium Risk Account (41–70)</span>
            <span style="color:{COLOR_HIGH}; margin-left:1.1rem; font-weight:600;">● High Risk Account (71–100)</span>
            <span style="color:#38BDF8; margin-left:1.1rem;">◆ Device</span>
            <span style="color:#A855F7; margin-left:1.1rem;">▲ Merchant</span>
            <span style="color:#94A3B8; margin-left:1.1rem;">■ Location</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    html_content = build_pyvis_html(
        G,
        focus_accounts=focus_accounts,
        include_types=include_types,
        min_risk=0.0,
        enable_physics=True,
        height_px=580,
    )
    components.html(html_content, height=600, scrolling=False)
