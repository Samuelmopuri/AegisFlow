"""FastAPI Router for the Real-Time Financial Fraud Intelligence Platform."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.schemas import (
    AccountRecord,
    FraudRingRecord,
    PatternRecord,
    RealtimeScoreResponse,
    SimulationRequest,
    TransactionInput,
    TransactionRecord,
)
from database.seed import generate_initial_dataset, generate_simulated_transaction
from engine.pipeline import FraudIntelligencePipeline

router = APIRouter(prefix="/api", tags=["Fraud Intelligence API"])


def _get_pipeline() -> FraudIntelligencePipeline:
    pipeline = FraudIntelligencePipeline()
    # Auto-seed if database is empty
    if not pipeline.db.get_transactions(limit=1):
        pipeline.run_full_pipeline(generate_initial_dataset())
    return pipeline


@router.get("/health")
def health_check() -> Dict[str, Any]:
    pipeline = _get_pipeline()
    return {
        "status": "healthy",
        "database_mode": pipeline.db.mode,
        "service": "Real-Time Financial Fraud Intelligence Platform",
    }


@router.get("/transactions", response_model=List[TransactionRecord])
def list_transactions(
    min_risk: float = Query(0.0, ge=0.0, le=100.0),
    action: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
) -> List[Dict[str, Any]]:
    pipeline = _get_pipeline()
    txs = pipeline.db.get_transactions(limit=limit)
    filtered = [t for t in txs if float(t.get("risk_score", 0.0)) >= min_risk]
    if action:
        filtered = [t for t in filtered if str(t.get("action")) == action]
    if account_id:
        filtered = [t for t in filtered if str(t.get("account_id")) == account_id]
    return filtered


@router.post("/transactions/score", response_model=RealtimeScoreResponse)
def score_transaction(payload: TransactionInput) -> Dict[str, Any]:
    pipeline = _get_pipeline()
    return pipeline.ingest_realtime_transaction(payload.model_dump(exclude_none=True))


@router.post("/transactions/simulate", response_model=RealtimeScoreResponse)
def simulate_transaction(req: SimulationRequest) -> Dict[str, Any]:
    pipeline = _get_pipeline()
    sim_tx = generate_simulated_transaction(req.scenario)
    return pipeline.ingest_realtime_transaction(sim_tx)


@router.get("/accounts", response_model=List[AccountRecord])
def list_accounts(min_risk: float = Query(0.0, ge=0.0, le=100.0)) -> List[Dict[str, Any]]:
    pipeline = _get_pipeline()
    accounts = pipeline.db.get_accounts()
    return [a for a in accounts if float(a.get("account_risk_score", 0.0)) >= min_risk]


@router.get("/accounts/{account_id}")
def get_account_detail(account_id: str) -> Dict[str, Any]:
    pipeline = _get_pipeline()
    state = pipeline.get_current_state()
    acc = next((a for a in state["accounts"] if str(a["account_id"]) == account_id), None)
    if not acc:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    txs = [t for t in state["transactions"] if str(t["account_id"]) == account_id]
    rings = [r for r in state["fraud_rings"] if account_id in r.get("accounts_involved", [])]
    return {
        "account": acc,
        "transactions": txs,
        "fraud_rings": rings,
    }


@router.get("/fraud-rings", response_model=List[FraudRingRecord])
def list_fraud_rings() -> List[Dict[str, Any]]:
    pipeline = _get_pipeline()
    return pipeline.db.get_fraud_rings()


@router.get("/patterns", response_model=List[PatternRecord])
def list_patterns() -> List[Dict[str, Any]]:
    pipeline = _get_pipeline()
    state = pipeline.get_current_state()
    return state["patterns"]


@router.get("/graph")
def get_network_graph() -> Dict[str, Any]:
    pipeline = _get_pipeline()
    state = pipeline.get_current_state()
    G = state["graph"]

    nodes = [
        {"id": str(node_id), **{k: v for k, v in attrs.items()}}
        for node_id, attrs in G.nodes(data=True)
    ]
    edges = [
        {"source": str(u), "target": str(v), **{k: v for k, v in attrs.items()}}
        for u, v, attrs in G.edges(data=True)
    ]
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


@router.get("/analytics")
def get_analytics_summary() -> Dict[str, Any]:
    pipeline = _get_pipeline()
    state = pipeline.get_current_state()
    txs = state["transactions"]
    accounts = state["accounts"]
    rings = state["fraud_rings"]

    total_tx = len(txs)
    total_volume = sum(float(t.get("amount", 0.0)) for t in txs)
    avg_tx_risk = sum(float(t.get("risk_score", 0.0)) for t in txs) / max(1, total_tx)

    action_counts: Dict[str, int] = {
        "Approve": 0,
        "OTP Verification": 0,
        "Temporary Hold": 0,
        "Block and Investigate": 0,
    }
    for t in txs:
        act = str(t.get("action", "Approve"))
        action_counts[act] = action_counts.get(act, 0) + 1

    return {
        "total_transactions": total_tx,
        "total_volume_usd": round(total_volume, 2),
        "average_transaction_risk": round(avg_tx_risk, 2),
        "total_accounts": len(accounts),
        "high_risk_accounts": sum(1 for a in accounts if float(a.get("account_risk_score", 0.0)) > 70.0),
        "detected_fraud_rings": len(rings),
        "detected_patterns": len(state["patterns"]),
        "action_breakdown": action_counts,
        "database_mode": state["db_mode"],
    }


@router.post("/seed")
def reseed_database() -> Dict[str, Any]:
    pipeline = FraudIntelligencePipeline()
    pipeline.db.clear_all()
    result = pipeline.run_full_pipeline(generate_initial_dataset())
    return {
        "status": "reseeded",
        "transactions_seeded": len(result["transactions"]),
        "accounts_scored": len(result["accounts"]),
        "fraud_rings_detected": len(result["fraud_rings"]),
        "patterns_discovered": len(result["patterns"]),
    }
