"""
Account Risk Scoring Engine.
Aggregates transaction-level risk scores, behavioral diversity (devices, locations,
velocity), and fraud ring associations into an account-level risk score (0-100)
with human-readable explanations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import numpy as np
import pandas as pd


class AccountRiskScorer:
    """Computes aggregated account-level risk scores and explanations."""

    def score_accounts(
        self,
        transactions_df: pd.DataFrame,
        fraud_rings: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate transaction risk scores per account and incorporate fraud ring signals.

        Returns list of dicts matching `accounts` schema:
        - account_id
        - account_risk_score (0-100)
        - explanation
        """
        if transactions_df.empty:
            return []

        df = transactions_df.copy()
        df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce").fillna(0.0)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

        # Map account_id -> list of rings it belongs to
        acct_rings: Dict[str, List[Dict[str, Any]]] = {}
        for ring in fraud_rings or []:
            ring_id = str(ring.get("ring_id", ""))
            for acc in ring.get("accounts_involved", []):
                acct_rings.setdefault(str(acc), []).append(ring)

        # Count how many accounts share each device
        device_acct_counts = df.groupby("device_id")["account_id"].nunique().to_dict()

        accounts_output: List[Dict[str, Any]] = []

        for account_id, group in df.groupby("account_id"):
            acc_str = str(account_id)
            scores = group["risk_score"].to_numpy(dtype=float)
            amounts = group["amount"].to_numpy(dtype=float)

            mean_score = float(np.mean(scores))
            max_score = float(np.max(scores))
            high_risk_count = int(np.sum(scores > 70.0))
            critical_count = int(np.sum(scores > 90.0))
            tx_count = len(scores)
            total_volume = float(np.sum(amounts))

            unique_devices = int(group["device_id"].nunique())
            unique_locations = int(group["location"].nunique())

            # Check if any device used by this account is shared with other accounts
            shared_devices: Set[str] = {
                str(d) for d in group["device_id"].unique() if int(device_acct_counts.get(d, 1)) >= 2
            }

            # Base aggregation: blend weighted peak risk + mean risk
            agg_score = 0.55 * max_score + 0.45 * mean_score

            reasons: List[str] = []

            if critical_count > 0:
                agg_score += min(14.0, critical_count * 6.0)
                reasons.append(f"{critical_count} critical-risk transaction(s) (score > 90)")
            elif high_risk_count > 0:
                agg_score += min(10.0, high_risk_count * 4.0)
                reasons.append(f"{high_risk_count} high-risk transaction(s) (score > 70)")

            if shared_devices:
                agg_score += min(12.0, len(shared_devices) * 7.0)
                dev_sample = ", ".join(sorted(shared_devices)[:2])
                reasons.append(f"Shares device infrastructure ({dev_sample}) with other accounts")

            if unique_devices >= 3:
                agg_score += 6.0
                reasons.append(f"Multiple devices used ({unique_devices} distinct devices)")

            if unique_locations >= 3:
                agg_score += 6.0
                reasons.append(f"Rapid geographic dispersion across {unique_locations} locations")

            # Fraud ring membership boost
            rings_for_acc = acct_rings.get(acc_str, [])
            if rings_for_acc:
                top_ring = max(rings_for_acc, key=lambda r: float(r.get("ring_risk_score", 0.0)))
                ring_boost = min(15.0, float(top_ring.get("ring_risk_score", 0.0)) * 0.14)
                agg_score = max(agg_score, float(top_ring.get("ring_risk_score", 0.0)) * 0.85) + ring_boost * 0.35
                reasons.append(
                    f"Member of Fraud Ring {top_ring['ring_id']} ({top_ring.get('pattern_detected', 'Coordinated ring')})"
                )

            final_account_score = round(float(np.clip(agg_score, 0.0, 100.0)), 2)

            # Pull top transaction-level explanations if account explanation needs detail
            if not reasons:
                if final_account_score <= 40.0:
                    explanation = (
                        f"Consistent baseline behavior across {tx_count} transaction(s) "
                        f"(${total_volume:,.2f} total volume)"
                    )
                else:
                    top_tx_reason = str(group.sort_values("risk_score", ascending=False).iloc[0]["explanation"])
                    explanation = f"Elevated transaction risk (peak {max_score:.0f}/100): {top_tx_reason}"
            else:
                explanation = "; ".join(reasons) + f" | Peak Tx Risk: {max_score:.1f}/100 across {tx_count} txns"

            accounts_output.append(
                {
                    "account_id": acc_str,
                    "account_risk_score": final_account_score,
                    "explanation": explanation,
                }
            )

        accounts_output.sort(key=lambda x: x["account_risk_score"], reverse=True)
        return accounts_output
