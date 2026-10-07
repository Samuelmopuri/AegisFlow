"""
Synthetic Financial Fraud & Transaction Stream Generator.
Generates realistic baseline transactions alongside coordinated multi-account
fraud rings, structuring bursts, device sharing rings, and high-risk anomalies.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

NORMAL_LOCATIONS = [
    "New York, US",
    "San Francisco, US",
    "Chicago, US",
    "Austin, US",
    "London, UK",
    "Toronto, CA",
    "Seattle, US",
    "Boston, US",
]

NORMAL_MERCHANTS = [
    "MER-AMAZON-US",
    "MER-APPLE-STORE",
    "MER-STARBUCKS",
    "MER-UBER-TRIP",
    "MER-WHOLEFOODS",
    "MER-DELTA-AIR",
    "MER-NETFLIX-SUB",
    "MER-TARGET-RET",
    "MER-COSTCO-WHL",
]


def generate_initial_dataset(seed: int = 42) -> List[Dict[str, Any]]:
    """
    Generate a comprehensive dataset (~90 transactions across 18 accounts)
    covering all risk tiers (Approve, OTP Verification, Temporary Hold, Block and Investigate)
    and 3 distinct multi-account Fraud Rings.
    """
    rng = random.Random(seed)
    base_time = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(hours=36)
    txs: List[Dict[str, Any]] = []
    tx_counter = 1001

    def next_tx_id() -> str:
        nonlocal tx_counter
        tid = f"TX-{tx_counter}"
        tx_counter += 1
        return tid

    # -------------------------------------------------------------------------
    # 1. Normal Baseline Accounts (ACC-1001 to ACC-1008) -> Low Risk (0-40)
    # -------------------------------------------------------------------------
    normal_accounts = [
        ("ACC-1001", "DEV-IOS-101", "New York, US"),
        ("ACC-1002", "DEV-AND-102", "San Francisco, US"),
        ("ACC-1003", "DEV-WEB-103", "Chicago, US"),
        ("ACC-1004", "DEV-IOS-104", "Austin, US"),
        ("ACC-1005", "DEV-MAC-105", "London, UK"),
        ("ACC-1006", "DEV-IOS-106", "Toronto, CA"),
        ("ACC-1007", "DEV-WIN-107", "Seattle, US"),
        ("ACC-1008", "DEV-AND-108", "Boston, US"),
    ]

    for acc_id, home_dev, home_loc in normal_accounts:
        for step in range(6):
            ts = base_time + timedelta(hours=step * 4 + rng.randint(0, 2), minutes=rng.randint(5, 50))
            # Force daytime hours (09:00 - 20:00 UTC) for clean baseline
            ts = ts.replace(hour=rng.randint(9, 19))
            txs.append(
                {
                    "transaction_id": next_tx_id(),
                    "account_id": acc_id,
                    "device_id": home_dev,
                    "merchant_id": rng.choice(NORMAL_MERCHANTS),
                    "location": home_loc,
                    "amount": round(rng.uniform(18.50, 240.00), 2),
                    "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

    # -------------------------------------------------------------------------
    # 2. Medium & High Risk Individual Accounts (ACC-1009, ACC-1010)
    #    Triggers OTP Verification (41-70) & Temporary Hold (71-90)
    # -------------------------------------------------------------------------
    # ACC-1009: Normal history followed by new device + unusual location + elevated amount
    for i in range(3):
        ts = (base_time + timedelta(hours=i * 3)).replace(hour=14, minute=10 + i * 12)
        txs.append(
            {
                "transaction_id": next_tx_id(),
                "account_id": "ACC-1009",
                "device_id": "DEV-IOS-109",
                "merchant_id": "MER-AMAZON-US",
                "location": "New York, US",
                "amount": round(85.0 + i * 20.0, 2),
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    # Medium risk transaction for ACC-1009 (OTP Verification)
    ts_med = (base_time + timedelta(hours=22)).replace(hour=15, minute=25)
    txs.append(
        {
            "transaction_id": next_tx_id(),
            "account_id": "ACC-1009",
            "device_id": "DEV-NEW-909",
            "merchant_id": "MER-APPLE-STORE",
            "location": "Miami, US",
            "amount": 1950.00,
            "timestamp": ts_med.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    # High risk transaction for ACC-1009 (Temporary Hold)
    ts_high = (base_time + timedelta(hours=18)).replace(hour=4, minute=45)
    txs.append(
        {
            "transaction_id": next_tx_id(),
            "account_id": "ACC-1009",
            "device_id": "DEV-UNKNOWN-88",
            "merchant_id": "MER-WIRE-GLOBAL",
            "location": "Panama City, PA",
            "amount": 4250.00,
            "timestamp": ts_high.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )

    # ACC-1010: Normal history then odd-hour high amount
    for i in range(3):
        ts = (base_time + timedelta(hours=i * 4)).replace(hour=13, minute=15 + i * 10)
        txs.append(
            {
                "transaction_id": next_tx_id(),
                "account_id": "ACC-1010",
                "device_id": "DEV-MAC-110",
                "merchant_id": "MER-COSTCO-WHL",
                "location": "Seattle, US",
                "amount": round(110.0 + i * 15.0, 2),
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    ts_otp = (base_time + timedelta(hours=20)).replace(hour=3, minute=40)
    txs.append(
        {
            "transaction_id": next_tx_id(),
            "account_id": "ACC-1010",
            "device_id": "DEV-MAC-110",
            "merchant_id": "MER-DELTA-AIR",
            "location": "Miami, US",
            "amount": 2150.00,
            "timestamp": ts_otp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )

    # -------------------------------------------------------------------------
    # 3. FRAUD RING 1: Shared Device Mule Ring + Short Time Window Burst
    #    Accounts: ACC-2001, ACC-2002, ACC-2003, ACC-2004
    #    Shared Device: DEV-MULE-X99 | Merchant: MER-CRYPTO-MIXER | Location: Lagos, NG
    # -------------------------------------------------------------------------
    ring1_accounts = ["ACC-2001", "ACC-2002", "ACC-2003", "ACC-2004"]
    # Give each account 1 initial normal transaction so the shared device + location registers as new/anomalous
    for idx, acc_id in enumerate(ring1_accounts):
        ts_init = (base_time + timedelta(hours=2)).replace(hour=12, minute=10 + idx * 5)
        txs.append(
            {
                "transaction_id": next_tx_id(),
                "account_id": acc_id,
                "device_id": f"DEV-HOME-{idx + 201}",
                "merchant_id": "MER-STARBUCKS",
                "location": "New York, US",
                "amount": 45.00 + idx * 10.0,
                "timestamp": ts_init.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    # Coordinated burst within an 8-minute window at 02:10 - 02:18 UTC
    burst1_start = (base_time + timedelta(hours=26)).replace(hour=2, minute=10)
    for idx, acc_id in enumerate(ring1_accounts):
        for wave in range(2):
            ts_attack = burst1_start + timedelta(minutes=idx * 1 + wave * 3)
            txs.append(
                {
                    "transaction_id": next_tx_id(),
                    "account_id": acc_id,
                    "device_id": "DEV-MULE-X99",
                    "merchant_id": "MER-CRYPTO-MIXER",
                    "location": "Lagos, NG",
                    "amount": round(6800.00 + idx * 120.0 + wave * 90.0, 2),
                    "timestamp": ts_attack.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

    # -------------------------------------------------------------------------
    # 4. FRAUD RING 2: Structuring / Smurfing Ring (Similar Amounts + Shared Merchant)
    #    Accounts: ACC-3001, ACC-3002, ACC-3003
    #    Shared Device: DEV-PROXY-77 | Merchant: MER-OFFSHORE-BULLION | Location: Cayman Islands
    #    Similar amounts clustered tightly around ~$9,490 (just under $10k reporting limit)
    # -------------------------------------------------------------------------
    ring2_accounts = ["ACC-3001", "ACC-3002", "ACC-3003"]
    for idx, acc_id in enumerate(ring2_accounts):
        ts_init = (base_time + timedelta(hours=4)).replace(hour=11, minute=20 + idx * 6)
        txs.append(
            {
                "transaction_id": next_tx_id(),
                "account_id": acc_id,
                "device_id": f"DEV-CORP-{idx + 301}",
                "merchant_id": "MER-UBER-TRIP",
                "location": "London, UK",
                "amount": 120.00 + idx * 15.0,
                "timestamp": ts_init.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

    burst2_start = (base_time + timedelta(hours=28)).replace(hour=3, minute=5)
    structured_amounts = [9485.00, 9492.50, 9488.00, 9495.00, 9490.00, 9487.50]
    for idx, acc_id in enumerate(ring2_accounts):
        for wave in range(2):
            ts_smurf = burst2_start + timedelta(minutes=idx * 2 + wave * 2)
            amt = structured_amounts[(idx * 2 + wave) % len(structured_amounts)]
            txs.append(
                {
                    "transaction_id": next_tx_id(),
                    "account_id": acc_id,
                    "device_id": "DEV-PROXY-77",
                    "merchant_id": "MER-OFFSHORE-BULLION",
                    "location": "Cayman Islands",
                    "amount": amt,
                    "timestamp": ts_smurf.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

    # -------------------------------------------------------------------------
    # 5. FRAUD RING 3: Merchant Bust-Out & Multi-Account Device Relay
    #    Accounts: ACC-4001, ACC-4002, ACC-4003
    #    Shared Device: DEV-RELAY-404 | Merchant: MER-CASINO-ROYAL | Location: Macau, CN
    # -------------------------------------------------------------------------
    ring3_accounts = ["ACC-4001", "ACC-4002", "ACC-4003"]
    burst3_start = (base_time + timedelta(hours=31)).replace(hour=1, minute=15)
    for idx, acc_id in enumerate(ring3_accounts):
        for wave in range(2):
            ts_ring3 = burst3_start + timedelta(minutes=idx * 2 + wave * 3)
            txs.append(
                {
                    "transaction_id": next_tx_id(),
                    "account_id": acc_id,
                    "device_id": "DEV-RELAY-404",
                    "merchant_id": "MER-CASINO-ROYAL",
                    "location": "Macau, CN",
                    "amount": round(4910.00 + idx * 8.0 + wave * 5.0, 2),
                    "timestamp": ts_ring3.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )

    return txs


def generate_simulated_transaction(scenario: str = "random") -> Dict[str, Any]:
    """
    Generate a single synthetic real-time transaction for live streaming simulation
    on the dashboard or API.
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tx_id = f"TX-LIVE-{uuid.uuid4().hex[:6].upper()}"

    if scenario == "normal":
        return {
            "transaction_id": tx_id,
            "account_id": random.choice(["ACC-1001", "ACC-1002", "ACC-1003", "ACC-1004"]),
            "device_id": "DEV-IOS-101",
            "merchant_id": random.choice(NORMAL_MERCHANTS),
            "location": "New York, US",
            "amount": round(random.uniform(24.0, 165.0), 2),
            "timestamp": now_iso,
        }
    if scenario == "otp_stepup":
        return {
            "transaction_id": tx_id,
            "account_id": "ACC-1005",
            "device_id": f"DEV-NEW-{random.randint(500, 599)}",
            "merchant_id": "MER-APPLE-STORE",
            "location": "Miami, US",
            "amount": round(random.uniform(1450.0, 2200.0), 2),
            "timestamp": now_iso,
        }
    if scenario == "shared_device_attack":
        return {
            "transaction_id": tx_id,
            "account_id": random.choice(["ACC-2001", "ACC-2002", "ACC-2003", "ACC-2004"]),
            "device_id": "DEV-MULE-X99",
            "merchant_id": "MER-CRYPTO-MIXER",
            "location": "Lagos, NG",
            "amount": round(random.uniform(7200.0, 9600.0), 2),
            "timestamp": datetime.now(timezone.utc).replace(hour=2, minute=random.randint(10, 19)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    if scenario == "smurfing_ring":
        return {
            "transaction_id": tx_id,
            "account_id": random.choice(["ACC-3001", "ACC-3002", "ACC-3003"]),
            "device_id": "DEV-PROXY-77",
            "merchant_id": "MER-OFFSHORE-BULLION",
            "location": "Cayman Islands",
            "amount": round(random.uniform(9485.0, 9495.0), 2),
            "timestamp": datetime.now(timezone.utc).replace(hour=3, minute=random.randint(5, 14)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # Default: weighted random across scenarios
    choice = random.choices(
        ["normal", "otp_stepup", "shared_device_attack", "smurfing_ring"],
        weights=[0.35, 0.25, 0.20, 0.20],
        k=1,
    )[0]
    return generate_simulated_transaction(choice)
