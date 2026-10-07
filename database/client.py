"""
Dual-mode Database Client for the Real-Time Financial Fraud Intelligence Platform.
Supports Supabase (PostgreSQL) in production and seamlessly falls back to a local
SQLite database with the identical schema (`transactions`, `accounts`, `fraud_rings`)
when Supabase credentials are not configured.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "fraud_intelligence.db"


class FraudDatabaseClient:
    """Unified repository interface over Supabase PostgreSQL and local SQLite fallback."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        sqlite_path: Optional[Path] = None,
    ) -> None:
        load_dotenv(override=True)
        self.supabase_url = (
            supabase_url.strip()
            if supabase_url is not None
            else os.getenv("SUPABASE_URL", "").strip()
        )
        self.supabase_key = (
            supabase_key.strip()
            if supabase_key is not None
            else os.getenv("SUPABASE_KEY", "").strip()
        )
        self.sqlite_path = sqlite_path or DEFAULT_SQLITE_PATH
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        self._supabase_client = None
        self.mode = "sqlite"

        if self._is_valid_supabase_config(self.supabase_url, self.supabase_key):
            try:
                from supabase import create_client  # type: ignore

                self._supabase_client = create_client(self.supabase_url, self.supabase_key)
                self.mode = "supabase"
                logger.info("Connected to Supabase backend at %s", self.supabase_url)
            except Exception as exc:
                logger.warning("Failed to initialize Supabase client (%s). Falling back to SQLite.", exc)
                self._supabase_client = None
                self.mode = "sqlite"

        self._init_sqlite_schema()

    @staticmethod
    def _is_valid_supabase_config(url: str, key: str) -> bool:
        if not url or not key:
            return False
        if "your-project-id" in url or "your-supabase" in key:
            return False
        return url.startswith("http://") or url.startswith("https://")

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite_schema(self) -> None:
        with self._get_sqlite_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    account_risk_score REAL NOT NULL DEFAULT 0,
                    explanation TEXT NOT NULL DEFAULT 'Normal account activity'
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    merchant_id TEXT NOT NULL,
                    location TEXT NOT NULL,
                    amount REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    risk_score REAL NOT NULL DEFAULT 0,
                    explanation TEXT NOT NULL,
                    action TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS fraud_rings (
                    ring_id TEXT PRIMARY KEY,
                    ring_risk_score REAL NOT NULL DEFAULT 0,
                    pattern_detected TEXT NOT NULL,
                    accounts_involved TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
                CREATE INDEX IF NOT EXISTS idx_tx_device ON transactions(device_id);
                CREATE INDEX IF NOT EXISTS idx_tx_merchant ON transactions(merchant_id);
                CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_tx_risk ON transactions(risk_score DESC);
                """
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # Transactions CRUD
    # -------------------------------------------------------------------------
    def upsert_transactions(self, transactions: List[Dict[str, Any]]) -> None:
        if not transactions:
            return

        cleaned: List[Dict[str, Any]] = []
        for tx in transactions:
            cleaned.append(
                {
                    "transaction_id": str(tx["transaction_id"]),
                    "account_id": str(tx["account_id"]),
                    "device_id": str(tx["device_id"]),
                    "merchant_id": str(tx["merchant_id"]),
                    "location": str(tx["location"]),
                    "amount": round(float(tx["amount"]), 2),
                    "timestamp": str(tx["timestamp"]),
                    "risk_score": round(float(tx["risk_score"]), 2),
                    "explanation": str(tx["explanation"]),
                    "action": str(tx["action"]),
                }
            )

        if self.mode == "supabase" and self._supabase_client is not None:
            try:
                self._supabase_client.table("transactions").upsert(cleaned).execute()
                return
            except Exception as exc:
                logger.warning("Supabase transaction upsert failed (%s). Writing to SQLite fallback.", exc)

        with self._get_sqlite_conn() as conn:
            conn.executemany(
                """
                INSERT INTO transactions (
                    transaction_id, account_id, device_id, merchant_id,
                    location, amount, timestamp, risk_score, explanation, action
                ) VALUES (
                    :transaction_id, :account_id, :device_id, :merchant_id,
                    :location, :amount, :timestamp, :risk_score, :explanation, :action
                )
                ON CONFLICT(transaction_id) DO UPDATE SET
                    account_id = excluded.account_id,
                    device_id = excluded.device_id,
                    merchant_id = excluded.merchant_id,
                    location = excluded.location,
                    amount = excluded.amount,
                    timestamp = excluded.timestamp,
                    risk_score = excluded.risk_score,
                    explanation = excluded.explanation,
                    action = excluded.action
                """,
                cleaned,
            )
            conn.commit()

    def get_transactions(self, limit: int = 1000) -> List[Dict[str, Any]]:
        if self.mode == "supabase" and self._supabase_client is not None:
            try:
                resp = (
                    self._supabase_client.table("transactions")
                    .select("*")
                    .order("timestamp", desc=True)
                    .limit(limit)
                    .execute()
                )
                if resp.data is not None:
                    return list(resp.data)
            except Exception as exc:
                logger.warning("Supabase get_transactions failed (%s). Reading from SQLite.", exc)

        with self._get_sqlite_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # -------------------------------------------------------------------------
    # Accounts CRUD
    # -------------------------------------------------------------------------
    def upsert_accounts(self, accounts: List[Dict[str, Any]]) -> None:
        if not accounts:
            return

        cleaned: List[Dict[str, Any]] = []
        for acc in accounts:
            cleaned.append(
                {
                    "account_id": str(acc["account_id"]),
                    "account_risk_score": round(float(acc["account_risk_score"]), 2),
                    "explanation": str(acc["explanation"]),
                }
            )

        if self.mode == "supabase" and self._supabase_client is not None:
            try:
                self._supabase_client.table("accounts").upsert(cleaned).execute()
                return
            except Exception as exc:
                logger.warning("Supabase accounts upsert failed (%s). Writing to SQLite fallback.", exc)

        with self._get_sqlite_conn() as conn:
            conn.executemany(
                """
                INSERT INTO accounts (account_id, account_risk_score, explanation)
                VALUES (:account_id, :account_risk_score, :explanation)
                ON CONFLICT(account_id) DO UPDATE SET
                    account_risk_score = excluded.account_risk_score,
                    explanation = excluded.explanation
                """,
                cleaned,
            )
            conn.commit()

    def get_accounts(self) -> List[Dict[str, Any]]:
        if self.mode == "supabase" and self._supabase_client is not None:
            try:
                resp = (
                    self._supabase_client.table("accounts")
                    .select("*")
                    .order("account_risk_score", desc=True)
                    .execute()
                )
                if resp.data is not None:
                    return list(resp.data)
            except Exception as exc:
                logger.warning("Supabase get_accounts failed (%s). Reading from SQLite.", exc)

        with self._get_sqlite_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM accounts ORDER BY account_risk_score DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    # -------------------------------------------------------------------------
    # Fraud Rings CRUD
    # -------------------------------------------------------------------------
    def replace_fraud_rings(self, rings: List[Dict[str, Any]]) -> None:
        cleaned_supabase: List[Dict[str, Any]] = []
        cleaned_sqlite: List[Dict[str, Any]] = []

        for ring in rings:
            accounts_list = ring["accounts_involved"]
            if isinstance(accounts_list, str):
                try:
                    accounts_list = json.loads(accounts_list)
                except Exception:
                    accounts_list = [a.strip() for a in accounts_list.split(",") if a.strip()]

            cleaned_supabase.append(
                {
                    "ring_id": str(ring["ring_id"]),
                    "ring_risk_score": round(float(ring["ring_risk_score"]), 2),
                    "pattern_detected": str(ring["pattern_detected"]),
                    "accounts_involved": accounts_list,
                }
            )
            cleaned_sqlite.append(
                {
                    "ring_id": str(ring["ring_id"]),
                    "ring_risk_score": round(float(ring["ring_risk_score"]), 2),
                    "pattern_detected": str(ring["pattern_detected"]),
                    "accounts_involved": json.dumps(accounts_list),
                }
            )

        if self.mode == "supabase" and self._supabase_client is not None:
            try:
                self._supabase_client.table("fraud_rings").delete().neq("ring_id", "").execute()
                if cleaned_supabase:
                    self._supabase_client.table("fraud_rings").upsert(cleaned_supabase).execute()
                return
            except Exception as exc:
                logger.warning("Supabase fraud_rings update failed (%s). Writing to SQLite fallback.", exc)

        with self._get_sqlite_conn() as conn:
            conn.execute("DELETE FROM fraud_rings")
            if cleaned_sqlite:
                conn.executemany(
                    """
                    INSERT INTO fraud_rings (ring_id, ring_risk_score, pattern_detected, accounts_involved)
                    VALUES (:ring_id, :ring_risk_score, :pattern_detected, :accounts_involved)
                    """,
                    cleaned_sqlite,
                )
            conn.commit()

    def get_fraud_rings(self) -> List[Dict[str, Any]]:
        if self.mode == "supabase" and self._supabase_client is not None:
            try:
                resp = (
                    self._supabase_client.table("fraud_rings")
                    .select("*")
                    .order("ring_risk_score", desc=True)
                    .execute()
                )
                if resp.data is not None:
                    result = []
                    for r in resp.data:
                        row = dict(r)
                        if isinstance(row.get("accounts_involved"), str):
                            try:
                                row["accounts_involved"] = json.loads(row["accounts_involved"])
                            except Exception:
                                row["accounts_involved"] = [
                                    a.strip() for a in row["accounts_involved"].split(",") if a.strip()
                                ]
                        result.append(row)
                    return result
            except Exception as exc:
                logger.warning("Supabase get_fraud_rings failed (%s). Reading from SQLite.", exc)

        with self._get_sqlite_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM fraud_rings ORDER BY ring_risk_score DESC"
            ).fetchall()
            result = []
            for r in rows:
                row = dict(r)
                raw_accounts = row.get("accounts_involved", "[]")
                if isinstance(raw_accounts, str):
                    try:
                        row["accounts_involved"] = json.loads(raw_accounts)
                    except Exception:
                        row["accounts_involved"] = [
                            a.strip() for a in raw_accounts.split(",") if a.strip()
                        ]
                result.append(row)
            return result

    def clear_all(self) -> None:
        """Reset all tables (useful for re-seeding demo scenarios)."""
        if self.mode == "supabase" and self._supabase_client is not None:
            try:
                self._supabase_client.table("transactions").delete().neq("transaction_id", "").execute()
                self._supabase_client.table("fraud_rings").delete().neq("ring_id", "").execute()
                self._supabase_client.table("accounts").delete().neq("account_id", "").execute()
            except Exception as exc:
                logger.warning("Supabase clear_all failed (%s).", exc)

        with self._get_sqlite_conn() as conn:
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM fraud_rings")
            conn.execute("DELETE FROM accounts")
            conn.commit()


_db_instance: Optional[FraudDatabaseClient] = None


def get_db_client() -> FraudDatabaseClient:
    """Singleton getter for the FraudDatabaseClient (auto-reloads if .env credentials change)."""
    global _db_instance
    load_dotenv(override=True)
    current_url = os.getenv("SUPABASE_URL", "").strip()
    current_key = os.getenv("SUPABASE_KEY", "").strip()
    if (
        _db_instance is None
        or _db_instance.supabase_url != current_url
        or _db_instance.supabase_key != current_key
    ):
        _db_instance = FraudDatabaseClient(supabase_url=current_url, supabase_key=current_key)
    return _db_instance
