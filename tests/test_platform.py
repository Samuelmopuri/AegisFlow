"""
Comprehensive Automated Test Suite for the Real-Time Financial Fraud Intelligence Platform.
Verifies:
1. Transaction Risk Scoring (0-100 + human-readable explanations)
2. Action Recommendations (0-40, 41-70, 71-90, 91-100)
3. Account Risk Scoring & Aggregation
4. Fraud Ring Detection with NetworkX (Accounts, Devices, Merchants, Locations)
5. Pattern Discovery (Shared devices, shared merchants, similar amounts, short time windows)
6. Database Schema & Persistence (`transactions`, `accounts`, `fraud_rings`)
7. PyVis Network Graph HTML rendering
8. FastAPI REST API endpoints
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app
from dashboard.graph_viz import build_pyvis_html
from database.client import FraudDatabaseClient
from database.seed import generate_initial_dataset
from engine.action_engine import recommend_action
from engine.pipeline import FraudIntelligencePipeline


def test_action_recommendation_thresholds() -> None:
    assert recommend_action(0) == "Approve"
    assert recommend_action(25.5) == "Approve"
    assert recommend_action(40) == "Approve"
    assert recommend_action(41) == "OTP Verification"
    assert recommend_action(70) == "OTP Verification"
    assert recommend_action(71) == "Temporary Hold"
    assert recommend_action(90) == "Temporary Hold"
    assert recommend_action(91) == "Block and Investigate"
    assert recommend_action(100) == "Block and Investigate"


def test_full_pipeline_and_database_schemas(tmp_path: Path) -> None:
    db_file = tmp_path / "test_fraud.db"
    db_client = FraudDatabaseClient(supabase_url="", supabase_key="", sqlite_path=db_file)
    pipeline = FraudIntelligencePipeline(db_client=db_client)

    raw_txs = generate_initial_dataset(seed=42)
    result = pipeline.run_full_pipeline(raw_txs)

    # 1. Verify transactions schema & scoring
    txs = db_client.get_transactions()
    assert len(txs) == len(raw_txs)
    required_tx_cols = {
        "transaction_id",
        "account_id",
        "device_id",
        "merchant_id",
        "location",
        "amount",
        "timestamp",
        "risk_score",
        "explanation",
        "action",
    }
    for tx in txs:
        assert required_tx_cols.issubset(tx.keys())
        score = float(tx["risk_score"])
        assert 0.0 <= score <= 100.0
        assert len(str(tx["explanation"])) > 0
        assert tx["action"] == recommend_action(score)

    # Check that explanations include required examples across dataset
    all_explanations = " | ".join(str(t["explanation"]) for t in txs)
    assert "Unusually high amount" in all_explanations
    assert "New device used" in all_explanations
    assert "Unusual location" in all_explanations
    assert "Unusual transaction timing" in all_explanations

    # 2. Verify accounts schema & aggregation
    accounts = db_client.get_accounts()
    assert len(accounts) >= 15
    required_acc_cols = {"account_id", "account_risk_score", "explanation"}
    for acc in accounts:
        assert required_acc_cols.issubset(acc.keys())
        assert 0.0 <= float(acc["account_risk_score"]) <= 100.0
        assert len(str(acc["explanation"])) > 0

    # 3. Verify fraud_rings schema & NetworkX detection
    rings = db_client.get_fraud_rings()
    assert len(rings) >= 3
    required_ring_cols = {"ring_id", "ring_risk_score", "pattern_detected", "accounts_involved"}
    for ring in rings:
        assert required_ring_cols.issubset(ring.keys())
        assert 0.0 <= float(ring["ring_risk_score"]) <= 100.0
        assert isinstance(ring["accounts_involved"], list)
        assert len(ring["accounts_involved"]) >= 2

    # 4. Verify Pattern Discovery covers all 4 pattern types
    pattern_types = {p["pattern_type"] for p in result["patterns"]}
    assert "Multiple accounts using same device" in pattern_types
    assert "Multiple accounts using same merchant" in pattern_types
    assert "Similar transaction amounts" in pattern_types
    assert "Transactions occurring within short time windows" in pattern_types

    # 5. Verify NetworkX Heterogeneous Graph & PyVis HTML output
    state = pipeline.get_current_state()
    G = state["graph"]
    entity_types = {d.get("entity_type") for _, d in G.nodes(data=True)}
    assert {"account", "device", "merchant", "location"}.issubset(entity_types)

    html = build_pyvis_html(G)
    assert "<html" in html.lower()
    assert "vis-network" in html


def test_fastapi_routes() -> None:
    client = TestClient(app)

    r_seed = client.post("/api/seed")
    assert r_seed.status_code == 200
    assert r_seed.json()["fraud_rings_detected"] >= 3

    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "healthy"

    r_txs = client.get("/api/transactions")
    assert r_txs.status_code == 200
    assert len(r_txs.json()) > 0

    r_accs = client.get("/api/accounts")
    assert r_accs.status_code == 200
    assert len(r_accs.json()) > 0

    r_rings = client.get("/api/fraud-rings")
    assert r_rings.status_code == 200
    assert len(r_rings.json()) >= 3

    r_pats = client.get("/api/patterns")
    assert r_pats.status_code == 200
    assert len(r_pats.json()) > 0

    r_graph = client.get("/api/graph")
    assert r_graph.status_code == 200
    assert r_graph.json()["node_count"] > 0

    # Test real-time transaction scoring endpoint
    score_resp = client.post(
        "/api/transactions/score",
        json={
            "account_id": "ACC-2001",
            "device_id": "DEV-MULE-X99",
            "merchant_id": "MER-CRYPTO-MIXER",
            "location": "Lagos, NG",
            "amount": 9250.0,
            "timestamp": "2026-10-07T02:15:00Z",
        },
    )
    assert score_resp.status_code == 200
    scored_tx = score_resp.json()["transaction"]
    assert scored_tx["risk_score"] >= 71.0
    assert scored_tx["action"] in ("Temporary Hold", "Block and Investigate")
