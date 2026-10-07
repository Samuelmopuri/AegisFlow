"""
Pattern Discovery Engine.
Detects coordinated financial fraud patterns across the transaction stream:
1. Multiple accounts using same device (Device Sharing / Mule Hardware)
2. Multiple accounts using same merchant (Merchant Collusion / Bust-Out)
3. Similar transaction amounts (Structuring / Smurfing)
4. Transactions occurring within short time windows (High-Velocity Synchronized Burst)
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


class PatternDiscoveryEngine:
    """Discovers multi-account and behavioral fraud patterns from transaction data."""

    def discover_patterns(self, transactions_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Run all pattern discovery detectors and return a list of detected patterns
        sorted by severity / risk score descending.
        """
        if transactions_df.empty:
            return []

        df = transactions_df.copy()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["risk_score"] = pd.to_numeric(df.get("risk_score", 0.0), errors="coerce").fillna(0.0)
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

        patterns: List[Dict[str, Any]] = []
        patterns.extend(self._detect_shared_devices(df))
        patterns.extend(self._detect_shared_merchants(df))
        patterns.extend(self._detect_similar_amounts(df))
        patterns.extend(self._detect_short_time_windows(df))

        patterns.sort(key=lambda p: float(p.get("severity_score", 0.0)), reverse=True)
        return patterns

    def _detect_shared_devices(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect multiple accounts using the same device."""
        results: List[Dict[str, Any]] = []
        grouped = df.groupby("device_id")

        for dev_id, group in grouped:
            accounts = sorted(group["account_id"].astype(str).unique().tolist())
            if len(accounts) >= 2:
                avg_risk = float(group["risk_score"].mean())
                total_amt = float(group["amount"].sum())
                severity = min(100.0, round(48.0 + len(accounts) * 11.0 + avg_risk * 0.25, 2))
                results.append(
                    {
                        "pattern_id": f"PAT-DEV-{dev_id}",
                        "pattern_type": "Multiple accounts using same device",
                        "entity_id": str(dev_id),
                        "accounts_involved": accounts,
                        "transaction_count": int(len(group)),
                        "total_amount": round(total_amt, 2),
                        "severity_score": severity,
                        "description": (
                            f"Multiple accounts using same device ({dev_id}): "
                            f"{len(accounts)} distinct accounts executed {len(group)} transactions "
                            f"totaling ${total_amt:,.2f}."
                        ),
                    }
                )
        return results

    def _detect_shared_merchants(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect multiple accounts concentrating high-risk or suspicious volume on the same merchant."""
        results: List[Dict[str, Any]] = []
        grouped = df.groupby("merchant_id")

        for mer_id, group in grouped:
            accounts = sorted(group["account_id"].astype(str).unique().tolist())
            high_risk_group = group[group["risk_score"] >= 50.0]
            high_risk_accounts = sorted(high_risk_group["account_id"].astype(str).unique().tolist())

            if len(high_risk_accounts) >= 2 or (len(accounts) >= 4 and float(group["amount"].mean()) >= 750.0):
                target_accounts = high_risk_accounts if len(high_risk_accounts) >= 2 else accounts
                avg_risk = float(group["risk_score"].mean())
                total_amt = float(group["amount"].sum())
                severity = min(98.0, round(42.0 + len(target_accounts) * 9.0 + avg_risk * 0.30, 2))
                results.append(
                    {
                        "pattern_id": f"PAT-MER-{mer_id}",
                        "pattern_type": "Multiple accounts using same merchant",
                        "entity_id": str(mer_id),
                        "accounts_involved": target_accounts,
                        "transaction_count": int(len(group)),
                        "total_amount": round(total_amt, 2),
                        "severity_score": severity,
                        "description": (
                            f"Multiple accounts using same merchant ({mer_id}): "
                            f"{len(target_accounts)} accounts converged on {mer_id} "
                            f"for ${total_amt:,.2f} across {len(group)} transactions."
                        ),
                    }
                )
        return results

    def _detect_similar_amounts(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect similar transaction amounts (Structuring / Smurfing across accounts)."""
        results: List[Dict[str, Any]] = []
        # Focus on non-trivial amounts >= $300
        candidates = df[df["amount"] >= 300.0].copy()
        if len(candidates) < 2:
            return results

        # Bucket amounts into $50 bands to find tight clustering of near-identical amounts
        candidates["amt_bucket"] = (candidates["amount"] / 50.0).round() * 50.0

        for bucket, group in candidates.groupby("amt_bucket"):
            accounts = sorted(group["account_id"].astype(str).unique().tolist())
            if len(accounts) >= 2 and len(group) >= 3:
                amt_std = float(group["amount"].std()) if len(group) > 1 else 0.0
                mean_amt = float(group["amount"].mean())
                # Only flag if amounts are tightly clustered (std < 35)
                if amt_std <= 35.0:
                    total_amt = float(group["amount"].sum())
                    avg_risk = float(group["risk_score"].mean())
                    severity = min(99.0, round(50.0 + len(accounts) * 8.5 + avg_risk * 0.25, 2))
                    results.append(
                        {
                            "pattern_id": f"PAT-AMT-{int(bucket)}",
                            "pattern_type": "Similar transaction amounts",
                            "entity_id": f"~${mean_amt:,.2f}",
                            "accounts_involved": accounts,
                            "transaction_count": int(len(group)),
                            "total_amount": round(total_amt, 2),
                            "severity_score": severity,
                            "description": (
                                f"Similar transaction amounts (~${mean_amt:,.2f} ± ${amt_std:,.2f}): "
                                f"{len(accounts)} accounts executed {len(group)} structured transactions "
                                f"totaling ${total_amt:,.2f}."
                            ),
                        }
                    )
        return results

    def _detect_short_time_windows(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect bursts of transactions occurring within short time windows (<= 12 minutes)."""
        results: List[Dict[str, Any]] = []
        valid = df.dropna(subset=["timestamp_dt"]).sort_values("timestamp_dt", ascending=True).reset_index(drop=True)
        if len(valid) < 3:
            return results

        timestamps = valid["timestamp_dt"].tolist()
        n = len(valid)
        used_indices: set = set()
        burst_idx = 1

        for i in range(n):
            if i in used_indices:
                continue
            t_start = timestamps[i]
            window_rows = [i]
            for j in range(i + 1, n):
                delta_min = (timestamps[j] - t_start).total_seconds() / 60.0
                if delta_min <= 12.0:
                    window_rows.append(j)
                else:
                    break

            sub = valid.iloc[window_rows]
            accounts = sorted(sub["account_id"].astype(str).unique().tolist())
            high_risk_sub = sub[sub["risk_score"] >= 45.0]

            if len(window_rows) >= 3 and len(accounts) >= 2 and len(high_risk_sub) >= 2:
                used_indices.update(window_rows)
                total_amt = float(sub["amount"].sum())
                avg_risk = float(sub["risk_score"].mean())
                duration_min = max(
                    0.5,
                    (timestamps[window_rows[-1]] - t_start).total_seconds() / 60.0,
                )
                severity = min(99.0, round(52.0 + len(window_rows) * 6.0 + avg_risk * 0.28, 2))
                results.append(
                    {
                        "pattern_id": f"PAT-BURST-{burst_idx:02d}",
                        "pattern_type": "Transactions occurring within short time windows",
                        "entity_id": f"{t_start.strftime('%H:%M')} UTC ({duration_min:.1f}m window)",
                        "accounts_involved": accounts,
                        "transaction_count": int(len(window_rows)),
                        "total_amount": round(total_amt, 2),
                        "severity_score": severity,
                        "description": (
                            f"Transactions occurring within short time windows: "
                            f"{len(window_rows)} transactions across {len(accounts)} accounts "
                            f"within {duration_min:.1f} minutes at {t_start.strftime('%Y-%m-%d %H:%M')} UTC "
                            f"(${total_amt:,.2f})."
                        ),
                    }
                )
                burst_idx += 1

        return results
