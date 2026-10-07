"""Pydantic schemas for the Fraud Intelligence Platform REST API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TransactionInput(BaseModel):
    transaction_id: Optional[str] = Field(
        default=None, description="Optional unique transaction ID (auto-generated if omitted)"
    )
    account_id: str = Field(..., description="Account identifier, e.g. ACC-2001")
    device_id: str = Field(..., description="Device identifier, e.g. DEV-MULE-X99")
    merchant_id: str = Field(..., description="Merchant identifier, e.g. MER-CRYPTO-MIXER")
    location: str = Field(..., description="Geographic location, e.g. Lagos, NG")
    amount: float = Field(..., ge=0.0, description="Transaction amount in USD")
    timestamp: Optional[str] = Field(
        default=None, description="ISO-8601 UTC timestamp (defaults to current UTC time)"
    )


class TransactionRecord(BaseModel):
    transaction_id: str
    account_id: str
    device_id: str
    merchant_id: str
    location: str
    amount: float
    timestamp: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    explanation: str
    action: str


class AccountRecord(BaseModel):
    account_id: str
    account_risk_score: float = Field(..., ge=0.0, le=100.0)
    explanation: str


class FraudRingRecord(BaseModel):
    ring_id: str
    ring_risk_score: float = Field(..., ge=0.0, le=100.0)
    pattern_detected: str
    accounts_involved: List[str]


class PatternRecord(BaseModel):
    pattern_id: str
    pattern_type: str
    entity_id: str
    accounts_involved: List[str]
    transaction_count: int
    total_amount: float
    severity_score: float
    description: str


class SimulationRequest(BaseModel):
    scenario: str = Field(
        default="random",
        description="One of: random, normal, otp_stepup, shared_device_attack, smurfing_ring",
    )


class RealtimeScoreResponse(BaseModel):
    transaction: TransactionRecord
    account: Optional[AccountRecord] = None
    fraud_rings_count: int
    patterns_count: int
