"""
Fraud Ring Detection & Heterogeneous Graph Intelligence Engine.
Uses NetworkX to build a multi-entity graph connecting:
- Accounts
- Devices
- Merchants
- Locations
Detects suspicious clusters of connected accounts sharing devices, merchants,
locations, or coordinated transaction patterns, and calculates `ring_risk_score`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd

from engine.pattern_detector import PatternDiscoveryEngine


class FraudRingDetector:
    """
    NetworkX-based Fraud Ring Detector.
    Builds both:
    1. Full heterogeneous entity graph (Accounts, Devices, Merchants, Locations)
    2. Account-to-Account fraud correlation graph for ring clustering & risk scoring
    """

    def __init__(self) -> None:
        self.pattern_engine = PatternDiscoveryEngine()

    def build_heterogeneous_graph(
        self,
        transactions_df: pd.DataFrame,
        accounts_list: Optional[List[Dict[str, Any]]] = None,
        fraud_rings: Optional[List[Dict[str, Any]]] = None,
    ) -> nx.Graph:
        """
        Build a heterogeneous NetworkX graph with nodes for:
        - Accounts (`account:<id>`)
        - Devices (`device:<id>`)
        - Merchants (`merchant:<id>`)
        - Locations (`location:<id>`)
        """
        G = nx.Graph()
        if transactions_df.empty:
            return G

        acct_risk_map: Dict[str, float] = {}
        acct_expl_map: Dict[str, str] = {}
        for acc in accounts_list or []:
            aid = str(acc["account_id"])
            acct_risk_map[aid] = float(acc.get("account_risk_score", 0.0))
            acct_expl_map[aid] = str(acc.get("explanation", ""))

        acct_ring_map: Dict[str, str] = {}
        for ring in fraud_rings or []:
            rid = str(ring["ring_id"])
            for aid in ring.get("accounts_involved", []):
                acct_ring_map[str(aid)] = rid

        df = transactions_df.copy()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["risk_score"] = pd.to_numeric(df.get("risk_score", 0.0), errors="coerce").fillna(0.0)

        for _, row in df.iterrows():
            acc_id = str(row["account_id"])
            dev_id = str(row["device_id"])
            mer_id = str(row["merchant_id"])
            loc_id = str(row["location"])
            amt = float(row["amount"])
            tx_risk = float(row["risk_score"])

            acc_node = f"account:{acc_id}"
            dev_node = f"device:{dev_id}"
            mer_node = f"merchant:{mer_id}"
            loc_node = f"location:{loc_id}"

            # 1. Account node
            acc_score = acct_risk_map.get(acc_id, tx_risk)
            G.add_node(
                acc_node,
                entity_type="account",
                label=acc_id,
                risk_score=round(acc_score, 2),
                ring_id=acct_ring_map.get(acc_id, ""),
                explanation=acct_expl_map.get(acc_id, str(row.get("explanation", ""))),
            )

            # 2. Device node
            if not G.has_node(dev_node):
                G.add_node(dev_node, entity_type="device", label=dev_id, risk_score=tx_risk)
            else:
                G.nodes[dev_node]["risk_score"] = max(float(G.nodes[dev_node]["risk_score"]), tx_risk)

            # 3. Merchant node
            if not G.has_node(mer_node):
                G.add_node(mer_node, entity_type="merchant", label=mer_id, risk_score=tx_risk)
            else:
                G.nodes[mer_node]["risk_score"] = max(float(G.nodes[mer_node]["risk_score"]), tx_risk)

            # 4. Location node
            if not G.has_node(loc_node):
                G.add_node(loc_node, entity_type="location", label=loc_id, risk_score=tx_risk)
            else:
                G.nodes[loc_node]["risk_score"] = max(float(G.nodes[loc_node]["risk_score"]), tx_risk)

            # Add / update edges
            self._add_or_update_edge(G, acc_node, dev_node, "USES_DEVICE", amt, tx_risk)
            self._add_or_update_edge(G, acc_node, mer_node, "TRANSACTS_AT", amt, tx_risk)
            self._add_or_update_edge(G, acc_node, loc_node, "LOCATED_IN", amt, tx_risk)

        return G

    @staticmethod
    def _add_or_update_edge(
        G: nx.Graph, u: str, v: str, relation: str, amount: float, risk_score: float
    ) -> None:
        if G.has_edge(u, v):
            G[u][v]["weight"] = float(G[u][v].get("weight", 1.0)) + 1.0
            G[u][v]["total_amount"] = float(G[u][v].get("total_amount", 0.0)) + amount
            G[u][v]["max_risk"] = max(float(G[u][v].get("max_risk", 0.0)), risk_score)
        else:
            G.add_edge(
                u,
                v,
                relation=relation,
                weight=1.0,
                total_amount=amount,
                max_risk=risk_score,
            )

    def detect_fraud_rings(self, transactions_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect suspicious clusters of connected accounts sharing devices, merchants,
        locations, or coordinated transaction patterns.

        Returns list of dicts matching `fraud_rings` schema:
        - ring_id
        - ring_risk_score (0-100)
        - pattern_detected
        - accounts_involved (list of account_ids)
        """
        if transactions_df.empty:
            return []

        df = transactions_df.copy()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["risk_score"] = pd.to_numeric(df.get("risk_score", 0.0), errors="coerce").fillna(0.0)

        # Build an account-to-account suspicious link graph
        acct_graph = nx.Graph()
        all_accounts = df["account_id"].astype(str).unique().tolist()
        for acc in all_accounts:
            sub = df[df["account_id"].astype(str) == acc]
            acct_graph.add_node(
                acc,
                mean_risk=float(sub["risk_score"].mean()),
                max_risk=float(sub["risk_score"].max()),
                total_amount=float(sub["amount"].sum()),
            )

        # 1. Link accounts sharing the same device (Strongest fraud ring signal)
        for dev_id, group in df.groupby("device_id"):
            accs = sorted(group["account_id"].astype(str).unique().tolist())
            if len(accs) >= 2:
                for i in range(len(accs)):
                    for j in range(i + 1, len(accs)):
                        self._link_accounts(
                            acct_graph,
                            accs[i],
                            accs[j],
                            weight=3.0,
                            reason=f"Shared device ({dev_id})",
                        )

        # 2. Link accounts sharing high-risk merchants
        for mer_id, group in df.groupby("merchant_id"):
            risky_sub = group[group["risk_score"] >= 50.0]
            accs = sorted(risky_sub["account_id"].astype(str).unique().tolist())
            if len(accs) >= 2:
                for i in range(len(accs)):
                    for j in range(i + 1, len(accs)):
                        self._link_accounts(
                            acct_graph,
                            accs[i],
                            accs[j],
                            weight=1.8,
                            reason=f"Shared high-risk merchant ({mer_id})",
                        )

        # 3. Link accounts sharing high-risk / anomalous locations with elevated risk
        for loc_id, group in df.groupby("location"):
            risky_sub = group[group["risk_score"] >= 65.0]
            accs = sorted(risky_sub["account_id"].astype(str).unique().tolist())
            if 2 <= len(accs) <= 6:
                for i in range(len(accs)):
                    for j in range(i + 1, len(accs)):
                        self._link_accounts(
                            acct_graph,
                            accs[i],
                            accs[j],
                            weight=1.2,
                            reason=f"Correlated high-risk location ({loc_id})",
                        )

        # 4. Incorporate Pattern Discovery links (similar amounts & short time window bursts)
        discovered_patterns = self.pattern_engine.discover_patterns(df)
        for pat in discovered_patterns:
            p_type = str(pat.get("pattern_type", ""))
            accs = [str(a) for a in pat.get("accounts_involved", [])]
            if len(accs) >= 2 and p_type in (
                "Similar transaction amounts",
                "Transactions occurring within short time windows",
            ):
                label = (
                    f"Similar transaction amounts ({pat.get('entity_id')})"
                    if p_type == "Similar transaction amounts"
                    else f"Short time window burst ({pat.get('entity_id')})"
                )
                for i in range(len(accs)):
                    for j in range(i + 1, len(accs)):
                        self._link_accounts(acct_graph, accs[i], accs[j], weight=2.0, reason=label)

        # Extract suspicious clusters (connected components with at least 2 accounts)
        active_edges_graph = nx.Graph(
            (u, v, d) for u, v, d in acct_graph.edges(data=True) if float(d.get("weight", 0.0)) >= 1.5
        )

        raw_clusters: List[Set[str]] = []
        for comp in nx.connected_components(active_edges_graph):
            if len(comp) >= 5:
                # Use greedy modularity community detection to split multi-ring components into tight rings
                sub_g = active_edges_graph.subgraph(comp)
                communities = nx.algorithms.community.greedy_modularity_communities(sub_g, weight="weight")
                for comm in communities:
                    if len(comm) >= 2:
                        raw_clusters.append(set(comm))
            elif len(comp) >= 2:
                raw_clusters.append(set(comp))

        rings: List[Dict[str, Any]] = []
        for idx, cluster in enumerate(raw_clusters, start=1):
            accounts_sorted = sorted(cluster)
            sub_g = active_edges_graph.subgraph(accounts_sorted)

            # Collect distinct reasons across edges in the cluster
            reason_counts: Dict[str, float] = {}
            total_edge_weight = 0.0
            for _, _, edata in sub_g.edges(data=True):
                w = float(edata.get("weight", 1.0))
                total_edge_weight += w
                for r in edata.get("reasons", set()):
                    reason_counts[r] = reason_counts.get(r, 0.0) + w

            sorted_reasons = [
                r for r, _ in sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)
            ]

            # Calculate ring risk score (0-100) from member transaction risks + graph density/weights
            ring_tx_df = df[df["account_id"].astype(str).isin(accounts_sorted)]
            mean_tx_risk = float(ring_tx_df["risk_score"].mean()) if not ring_tx_df.empty else 50.0
            max_tx_risk = float(ring_tx_df["risk_score"].max()) if not ring_tx_df.empty else 65.0
            density = float(nx.density(sub_g)) if len(accounts_sorted) > 1 else 1.0

            ring_score = (
                0.45 * max_tx_risk
                + 0.35 * mean_tx_risk
                + min(12.0, len(accounts_sorted) * 2.8)
                + min(10.0, total_edge_weight * 1.4)
                + (density * 5.0)
            )
            ring_score = round(float(np.clip(ring_score, 45.0, 100.0)), 2)

            pattern_summary = "; ".join(sorted_reasons[:3]) if sorted_reasons else "Coordinated multi-account cluster"

            rings.append(
                {
                    "ring_id": f"RING-{idx:03d}",
                    "ring_risk_score": ring_score,
                    "pattern_detected": pattern_summary,
                    "accounts_involved": accounts_sorted,
                }
            )

        # Sort rings by risk score descending and re-number sequentially
        rings.sort(key=lambda r: float(r["ring_risk_score"]), reverse=True)
        for idx, ring in enumerate(rings, start=1):
            ring["ring_id"] = f"RING-{idx:03d}"

        return rings

    @staticmethod
    def _link_accounts(
        G: nx.Graph, acc_a: str, acc_b: str, weight: float, reason: str
    ) -> None:
        if acc_a == acc_b:
            return
        if G.has_edge(acc_a, acc_b):
            G[acc_a][acc_b]["weight"] = float(G[acc_a][acc_b].get("weight", 0.0)) + weight
            reasons: Set[str] = set(G[acc_a][acc_b].get("reasons", set()))
            reasons.add(reason)
            G[acc_a][acc_b]["reasons"] = reasons
        else:
            G.add_edge(acc_a, acc_b, weight=weight, reasons={reason})
