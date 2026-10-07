"""
Transaction Risk Scoring Engine.
Combines behavioral risk heuristics with Scikit-learn IsolationForest anomaly detection
to produce a calibrated 0-100 risk score and transparent, human-readable explanations
for every transaction.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from engine.action_engine import recommend_action

HIGH_RISK_LOCATIONS = {
    "Cayman Islands",
    "Lagos, NG",
    "Bucharest, RO",
    "Minsk, BY",
    "Macau, CN",
    "Panama City, PA",
    "Offshore-Proxy-VPN",
    "Darknet-Exit-Node",
}

HIGH_RISK_MERCHANT_KEYWORDS = ("CRYPTO", "CASINO", "WIRE", "BULLION", "SHELL", "OFFSHORE", "MIXER")


class TransactionRiskScorer:
    """
    Hybrid ML + Behavioral Rule Transaction Risk Scorer.
    Generates:
      - risk_score: float (0 - 100)
      - explanation: str (human-readable reasons)
      - action: str (Approve | OTP Verification | Temporary Hold | Block and Investigate)
    """

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state

    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing or NULL values explicitly before featurization."""
        out = df.copy()
        out["amount"] = pd.to_numeric(out.get("amount", 0.0), errors="coerce").fillna(0.0).clip(lower=0.0)
        out["account_id"] = out.get("account_id", "UNKNOWN_ACC").fillna("UNKNOWN_ACC").astype(str)
        out["device_id"] = out.get("device_id", "UNKNOWN_DEV").fillna("UNKNOWN_DEV").astype(str)
        out["merchant_id"] = out.get("merchant_id", "UNKNOWN_MER").fillna("UNKNOWN_MER").astype(str)
        out["location"] = out.get("location", "Unknown").fillna("Unknown").astype(str)
        out["timestamp_dt"] = pd.to_datetime(out.get("timestamp"), errors="coerce", utc=True)
        if out["timestamp_dt"].isna().any():
            out["timestamp_dt"] = out["timestamp_dt"].fillna(pd.Timestamp.now(tz="UTC"))
        return out

    def score_transactions_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score a batch of transactions (historical + recent) and return a DataFrame
        populated with `risk_score`, `explanation`, and `action`.
        """
        if df.empty:
            return df.copy()

        work = self._clean_dataframe(df)
        work = work.sort_values("timestamp_dt", ascending=True).reset_index(drop=True)

        # ---------------------------------------------------------------------
        # 1. Contextual & Behavioral Feature Extraction
        # ---------------------------------------------------------------------
        # Global statistics
        global_median_amt = float(work["amount"].median()) if len(work) > 0 else 150.0
        global_std_amt = float(work["amount"].std()) if len(work) > 1 else 250.0
        if global_std_amt <= 0:
            global_std_amt = 100.0

        # Device sharing across distinct accounts
        device_account_counts = work.groupby("device_id")["account_id"].nunique().to_dict()
        # Merchant sharing across distinct accounts
        merchant_account_counts = work.groupby("merchant_id")["account_id"].nunique().to_dict()

        # Per-account historical tracking (chronological order to prevent future leakage)
        acct_seen_devices: Dict[str, set] = {}
        acct_seen_locations: Dict[str, set] = {}
        acct_amounts: Dict[str, List[float]] = {}
        acct_timestamps: Dict[str, List[pd.Timestamp]] = {}

        feature_rows: List[List[float]] = []
        heuristic_scores: List[float] = []
        explanations_list: List[List[str]] = []

        for _, row in work.iterrows():
            acc_id = str(row["account_id"])
            dev_id = str(row["device_id"])
            mer_id = str(row["merchant_id"])
            loc = str(row["location"])
            amt = float(row["amount"])
            ts: pd.Timestamp = row["timestamp_dt"]

            reasons: List[Tuple[float, str]] = []
            rule_points = 0.0

            # Initialize account history containers
            seen_devs = acct_seen_devices.setdefault(acc_id, set())
            seen_locs = acct_seen_locations.setdefault(acc_id, set())
            prev_amts = acct_amounts.setdefault(acc_id, [])
            prev_ts = acct_timestamps.setdefault(acc_id, [])

            # --- Factor A: Unusually High Amount / Structuring ---
            acct_baseline = float(np.mean(prev_amts)) if len(prev_amts) >= 2 else global_median_amt
            amt_ratio = amt / max(acct_baseline, 25.0)

            if amt >= 5000.0 or (amt >= 1200.0 and amt_ratio >= 3.5):
                pts = min(38.0, 18.0 + (amt / 600.0) + (amt_ratio * 2.2))
                rule_points += pts
                reasons.append((pts, f"Unusually high amount (${amt:,.2f} vs baseline ${acct_baseline:,.0f})"))
            elif amt >= 1800.0 or amt_ratio >= 2.5:
                pts = min(22.0, 10.0 + amt_ratio * 2.0)
                rule_points += pts
                reasons.append((pts, f"Unusually high amount (${amt:,.2f})"))

            # Structuring / Smurfing just below $10,000 or $5,000 reporting thresholds
            if 9000.0 <= amt <= 9999.99 or 4800.0 <= amt <= 4999.99:
                pts = 18.0
                rule_points += pts
                reasons.append((pts, f"Structuring pattern near reporting threshold (${amt:,.2f})"))

            # --- Factor B: New Device Used & Shared Device Across Accounts ---
            shared_dev_accounts = int(device_account_counts.get(dev_id, 1))
            is_new_device = len(seen_devs) > 0 and (dev_id not in seen_devs)

            if is_new_device:
                pts = 18.0
                rule_points += pts
                reasons.append((pts, f"New device used ({dev_id})"))

            if shared_dev_accounts >= 3:
                pts = min(30.0, 14.0 + (shared_dev_accounts - 2) * 5.5)
                rule_points += pts
                reasons.append(
                    (pts, f"Device shared across {shared_dev_accounts} accounts ({dev_id})")
                )
            elif shared_dev_accounts == 2:
                pts = 11.0
                rule_points += pts
                reasons.append((pts, f"Device linked to another account ({dev_id})"))

            # --- Factor C: Unusual Location ---
            is_new_location = len(seen_locs) > 0 and (loc not in seen_locs)
            is_high_risk_loc = loc in HIGH_RISK_LOCATIONS or any(
                k.lower() in loc.lower() for k in ("offshore", "proxy", "vpn", "cayman", "lagos", "minsk", "macau")
            )

            if is_high_risk_loc and is_new_location:
                pts = 26.0
                rule_points += pts
                reasons.append((pts, f"Unusual location ({loc} - high-risk jurisdiction)"))
            elif is_high_risk_loc:
                pts = 20.0
                rule_points += pts
                reasons.append((pts, f"Unusual location ({loc})"))
            elif is_new_location:
                pts = 14.0
                rule_points += pts
                reasons.append((pts, f"Unusual location ({loc} outside normal profile)"))

            # --- Factor D: Unusual Transaction Timing (Late-night / Odd Hours) ---
            hour = int(ts.hour)
            is_odd_hour = hour in (0, 1, 2, 3, 4, 5)
            if is_odd_hour:
                pts = 15.0 if amt >= 600.0 else 10.0
                rule_points += pts
                reasons.append((pts, f"Unusual transaction timing ({ts.strftime('%H:%M')} UTC off-hours)"))

            # --- Factor E: Short Time Window / High Velocity Burst ---
            minutes_since_last = 9999.0
            burst_count_15m = 0
            if prev_ts:
                minutes_since_last = max(0.0, (ts - prev_ts[-1]).total_seconds() / 60.0)
                burst_count_15m = sum(1 for t0 in prev_ts if 0 <= (ts - t0).total_seconds() <= 900)

            if burst_count_15m >= 2 or minutes_since_last <= 5.0:
                pts = min(24.0, 14.0 + burst_count_15m * 4.5)
                rule_points += pts
                reasons.append(
                    (pts, f"Rapid transaction velocity ({burst_count_15m + 1} txns within 15m window)")
                )

            # --- Factor F: High-Risk or Heavily Shared Collusive Merchant ---
            shared_mer_accounts = int(merchant_account_counts.get(mer_id, 1))
            is_risky_merchant = any(k in mer_id.upper() for k in HIGH_RISK_MERCHANT_KEYWORDS)
            if is_risky_merchant:
                pts = 15.0
                rule_points += pts
                reasons.append((pts, f"High-risk merchant category ({mer_id})"))
            elif shared_mer_accounts >= 4 and amt >= 800.0:
                pts = 10.0
                rule_points += pts
                reasons.append((pts, f"Merchant concentration burst ({mer_id})"))

            # Update per-account history after scoring current transaction
            seen_devs.add(dev_id)
            seen_locs.add(loc)
            prev_amts.append(amt)
            prev_ts.append(ts)

            # Numeric feature vector for Scikit-learn IsolationForest
            feature_rows.append(
                [
                    np.log1p(amt),
                    min(amt_ratio, 25.0),
                    float(shared_dev_accounts),
                    float(1 if is_new_device else 0),
                    float(1 if (is_new_location or is_high_risk_loc) else 0),
                    float(1 if is_odd_hour else 0),
                    float(burst_count_15m),
                    float(1 if is_risky_merchant else 0),
                ]
            )
            heuristic_scores.append(rule_points)

            # Sort reasons by contribution weight descending
            reasons.sort(key=lambda item: item[0], reverse=True)
            explanations_list.append([r[1] for r in reasons])

        # ---------------------------------------------------------------------
        # 2. Scikit-learn IsolationForest Anomaly Scoring (Split Fit / Eval)
        # ---------------------------------------------------------------------
        X = np.array(feature_rows, dtype=float)
        ml_scores = np.zeros(len(work), dtype=float)

        if len(work) >= 8:
            # Strict Featurization Ordering: fit scaler & model on chronological training split (first 70%)
            split_idx = max(5, int(len(work) * 0.7))
            X_train = X[:split_idx]

            scaler = StandardScaler()
            scaler.fit(X_train)
            X_train_scaled = scaler.transform(X_train)
            X_all_scaled = scaler.transform(X)

            iso = IsolationForest(
                n_estimators=120,
                contamination=0.22,
                random_state=self.random_state,
            )
            iso.fit(X_train_scaled)

            # decision_function: lower is more anomalous. Convert to 0-100 anomaly score
            raw_decision = -iso.decision_function(X_all_scaled)
            min_d, max_d = float(np.min(raw_decision)), float(np.max(raw_decision))
            if max_d > min_d:
                ml_scores = ((raw_decision - min_d) / (max_d - min_d)) * 100.0
            else:
                ml_scores = np.clip(np.array(heuristic_scores), 0.0, 100.0)
        else:
            ml_scores = np.clip(np.array(heuristic_scores), 0.0, 100.0)

        # ---------------------------------------------------------------------
        # 3. Blend Heuristic + ML Score into Calibrated 0-100 Risk Score
        # ---------------------------------------------------------------------
        final_scores: List[float] = []
        final_explanations: List[str] = []
        final_actions: List[str] = []

        for idx in range(len(work)):
            h_score = heuristic_scores[idx]
            m_score = float(ml_scores[idx])

            if h_score == 0.0:
                # Baseline low-risk normal transaction
                combined = min(28.0, round(m_score * 0.28, 2))
            else:
                combined = round(min(100.0, 0.76 * h_score + 0.24 * m_score), 2)

            reasons_for_tx = explanations_list[idx]
            if not reasons_for_tx:
                if combined <= 40.0:
                    explanation_str = "Normal transaction pattern within baseline profile"
                else:
                    explanation_str = "Statistical multi-feature anomaly detected by ML IsolationForest"
            else:
                explanation_str = "; ".join(reasons_for_tx[:4])

            action_str = recommend_action(combined)
            final_scores.append(combined)
            final_explanations.append(explanation_str)
            final_actions.append(action_str)

        work["risk_score"] = final_scores
        work["explanation"] = final_explanations
        work["action"] = final_actions

        # Drop temporary column and restore descending timestamp order
        work = work.drop(columns=["timestamp_dt"]).sort_values("timestamp", ascending=False).reset_index(drop=True)
        return work

    def score_single_transaction(
        self,
        transaction: Dict[str, Any],
        historical_transactions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Score a single real-time transaction in context of historical transactions."""
        history = list(historical_transactions or [])
        tx_copy = dict(transaction)
        combined_rows = [r for r in history if str(r.get("transaction_id")) != str(tx_copy.get("transaction_id"))]
        combined_rows.append(tx_copy)

        df = pd.DataFrame(combined_rows)
        scored_df = self.score_transactions_df(df)
        matched = scored_df[scored_df["transaction_id"].astype(str) == str(tx_copy["transaction_id"])]
        if not matched.empty:
            return matched.iloc[0].to_dict()
        return scored_df.iloc[0].to_dict()
