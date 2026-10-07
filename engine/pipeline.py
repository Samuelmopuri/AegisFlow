"""
Real-Time Fraud Intelligence Pipeline Orchestrator.
Coordinates Transaction Risk Scoring, Pattern Discovery, NetworkX Fraud Ring
Detection, Account Risk Aggregation, and Database Persistence.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import networkx as nx
import pandas as pd

from database.client import FraudDatabaseClient, get_db_client
from engine.account_scorer import AccountRiskScorer
from engine.fraud_ring_detector import FraudRingDetector
from engine.pattern_detector import PatternDiscoveryEngine
from engine.transaction_scorer import TransactionRiskScorer


class FraudIntelligencePipeline:
    """End-to-end orchestrator for real-time and batch financial fraud intelligence."""

    def __init__(self, db_client: Optional[FraudDatabaseClient] = None) -> None:
        self.db = db_client or get_db_client()
        self.tx_scorer = TransactionRiskScorer()
        self.account_scorer = AccountRiskScorer()
        self.pattern_detector = PatternDiscoveryEngine()
        self.ring_detector = FraudRingDetector()

    def run_full_pipeline(self, raw_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Score all transactions, detect fraud rings & patterns, aggregate account risks,
        and persist all three tables (`accounts`, `transactions`, `fraud_rings`) to DB.
        """
        if not raw_transactions:
            return {
                "transactions": [],
                "accounts": [],
                "fraud_rings": [],
                "patterns": [],
            }

        tx_df = pd.DataFrame(raw_transactions)
        scored_tx_df = self.tx_scorer.score_transactions_df(tx_df)

        # Detect fraud rings using NetworkX
        fraud_rings = self.ring_detector.detect_fraud_rings(scored_tx_df)

        # Compute account-level risk scores incorporating fraud ring membership
        accounts = self.account_scorer.score_accounts(scored_tx_df, fraud_rings=fraud_rings)

        # Discover granular patterns
        patterns = self.pattern_detector.discover_patterns(scored_tx_df)

        scored_tx_records = scored_tx_df.to_dict(orient="records")

        # Persist in foreign-key safe order: accounts -> transactions -> fraud_rings
        self.db.upsert_accounts(accounts)
        self.db.upsert_transactions(scored_tx_records)
        self.db.replace_fraud_rings(fraud_rings)

        return {
            "transactions": scored_tx_records,
            "accounts": accounts,
            "fraud_rings": fraud_rings,
            "patterns": patterns,
        }

    def ingest_realtime_transaction(self, incoming_tx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a newly arrived transaction in real time against existing history,
        update account risk scores and fraud rings, and persist to the database.
        """
        tx_payload = dict(incoming_tx)
        if not tx_payload.get("transaction_id"):
            tx_payload["transaction_id"] = f"TX-{uuid.uuid4().hex[:8].upper()}"
        if not tx_payload.get("timestamp"):
            tx_payload["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        existing_txs = self.db.get_transactions(limit=1500)
        all_txs = [
            t for t in existing_txs if str(t.get("transaction_id")) != str(tx_payload["transaction_id"])
        ]
        all_txs.append(tx_payload)

        result = self.run_full_pipeline(all_txs)

        # Locate the newly scored transaction
        scored_tx = next(
            (
                t
                for t in result["transactions"]
                if str(t["transaction_id"]) == str(tx_payload["transaction_id"])
            ),
            result["transactions"][0],
        )
        account_record = next(
            (
                a
                for a in result["accounts"]
                if str(a["account_id"]) == str(scored_tx["account_id"])
            ),
            None,
        )

        return {
            "transaction": scored_tx,
            "account": account_record,
            "fraud_rings_count": len(result["fraud_rings"]),
            "patterns_count": len(result["patterns"]),
        }

    def get_current_state(self) -> Dict[str, Any]:
        """
        Load current transactions, accounts, fraud rings, discovered patterns,
        and heterogeneous NetworkX graph from the database.
        """
        txs = self.db.get_transactions(limit=1500)
        accounts = self.db.get_accounts()
        rings = self.db.get_fraud_rings()

        tx_df = pd.DataFrame(txs) if txs else pd.DataFrame()
        patterns = self.pattern_detector.discover_patterns(tx_df) if not tx_df.empty else []
        graph: nx.Graph = (
            self.ring_detector.build_heterogeneous_graph(tx_df, accounts_list=accounts, fraud_rings=rings)
            if not tx_df.empty
            else nx.Graph()
        )

        return {
            "transactions": txs,
            "transactions_df": tx_df,
            "accounts": accounts,
            "accounts_df": pd.DataFrame(accounts) if accounts else pd.DataFrame(),
            "fraud_rings": rings,
            "fraud_rings_df": pd.DataFrame(rings) if rings else pd.DataFrame(),
            "patterns": patterns,
            "graph": graph,
            "db_mode": self.db.mode,
        }
