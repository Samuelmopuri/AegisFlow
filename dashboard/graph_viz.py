"""
Interactive Network Graph Visualization Builder for AegisFlow.
Shows clear relationships between:
- Accounts (Colored Green = Safe, Yellow = Medium Risk, Red = High Risk)
- Devices
- Merchants
- Locations
"""

from __future__ import annotations

import json
from typing import Optional, Set

import networkx as nx
from pyvis.network import Network

from dashboard.styles import get_risk_level_and_color


def build_pyvis_html(
    G: nx.Graph,
    focus_accounts: Optional[Set[str]] = None,
    include_types: Optional[Set[str]] = None,
    min_risk: float = 0.0,
    enable_physics: bool = True,
    height_px: int = 580,
) -> str:
    """
    Convert the heterogeneous NetworkX graph into a clean, business-friendly
    PyVis HTML visualization.
    """
    allowed_types = include_types or {"account", "device", "merchant", "location"}

    selected_nodes: Set[str] = set()
    if focus_accounts:
        for acc_id in focus_accounts:
            acc_node = f"account:{acc_id}"
            if G.has_node(acc_node):
                selected_nodes.add(acc_node)
                for nbr in G.neighbors(acc_node):
                    nbr_type = str(G.nodes[nbr].get("entity_type", ""))
                    if nbr_type in allowed_types:
                        selected_nodes.add(nbr)
    else:
        for node_id, attrs in G.nodes(data=True):
            etype = str(attrs.get("entity_type", "account"))
            score = float(attrs.get("risk_score", 0.0))
            if etype in allowed_types and score >= min_risk:
                selected_nodes.add(node_id)

    sub_g = G.subgraph(selected_nodes).copy()

    net = Network(
        height=f"{height_px}px",
        width="100%",
        bgcolor="#0B1120",
        font_color="#F8FAFC",
        directed=False,
        notebook=False,
    )

    for node_id, attrs in sub_g.nodes(data=True):
        etype = str(attrs.get("entity_type", "account"))
        label = str(attrs.get("label", node_id))
        score = float(attrs.get("risk_score", 0.0))
        ring_id = str(attrs.get("ring_id", ""))
        explanation = str(attrs.get("explanation", ""))
        deg = int(sub_g.degree(node_id))

        risk_level, semantic_color = get_risk_level_and_color(score)

        if etype == "account":
            color = semantic_color
            shape = "dot"
            size = 20 + min(14, int(score * 0.12))
            border_width = 3 if ring_id else 2
            title = (
                f"Account: {label}\n"
                f"Risk Level: {risk_level} ({score:.0f}/100)\n"
                f"Fraud Network: {ring_id or 'None'}\n"
                f"Summary: {explanation}"
            )
        elif etype == "device":
            color = "#EF4444" if deg >= 2 else "#38BDF8"
            shape = "diamond"
            size = 16 + min(14, deg * 3)
            border_width = 3 if deg >= 2 else 1
            title = (
                f"Device: {label}\n"
                f"Linked Accounts: {deg}\n"
                f"Status: {'Shared across multiple accounts' if deg >= 2 else 'Single-account device'}"
            )
        elif etype == "merchant":
            color = "#A855F7"
            shape = "triangle"
            size = 15 + min(12, deg * 2)
            border_width = 2
            title = f"Merchant: {label}\nConnected Accounts: {deg}"
        else:  # location
            color = "#64748B"
            shape = "square"
            size = 14 + min(10, deg * 2)
            border_width = 2
            title = f"Location: {label}\nConnected Accounts: {deg}"

        net.add_node(
            str(node_id),
            label=label,
            title=title,
            color={
                "background": color,
                "border": "#FFFFFF" if ring_id or (etype == "device" and deg >= 2) else color,
                "highlight": {"background": color, "border": "#F8FAFC"},
            },
            shape=shape,
            size=size,
            borderWidth=border_width,
        )

    for u, v, edata in sub_g.edges(data=True):
        weight = float(edata.get("weight", 1.0))
        total_amt = float(edata.get("total_amount", 0.0))
        max_risk = float(edata.get("max_risk", 0.0))
        _, edge_sem_color = get_risk_level_and_color(max_risk)

        edge_color = (
            "rgba(239, 68, 68, 0.65)"
            if max_risk > 70.0
            else "rgba(245, 158, 11, 0.50)"
            if max_risk > 40.0
            else "rgba(148, 163, 184, 0.28)"
        )
        edge_width = min(5.0, 1.2 + weight * 0.6)
        edge_title = f"Transactions: {int(weight)} | Total Amount: ${total_amt:,.2f}"
        net.add_edge(
            str(u),
            str(v),
            value=edge_width,
            color=edge_color,
            title=edge_title,
        )

    options = {
        "nodes": {
            "font": {"size": 13, "face": "Inter, system-ui, sans-serif", "color": "#F8FAFC"},
        },
        "edges": {
            "smooth": {"type": "continuous"},
        },
        "physics": {
            "enabled": enable_physics,
            "barnesHut": {
                "gravitationalConstant": -4200,
                "centralGravity": 0.30,
                "springLength": 135,
                "springConstant": 0.04,
                "damping": 0.09,
            },
            "stabilization": {"iterations": 120},
        },
        "interaction": {
            "hover": True,
            "tooltipDelay": 80,
            "navigationButtons": True,
        },
    }
    net.set_options(json.dumps(options))
    return net.generate_html()
