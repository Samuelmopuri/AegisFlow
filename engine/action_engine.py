"""
Action Recommendation Engine.
Maps risk scores (0-100) to deterministic operational actions:
- 0-40  -> Approve
- 41-70 -> OTP Verification
- 71-90 -> Temporary Hold
- 91-100 -> Block and Investigate
"""

from __future__ import annotations

from typing import Dict


def recommend_action(risk_score: float) -> str:
    """
    Return the action recommendation string for a given risk score (0-100).

    Thresholds:
    - 0-40: Approve
    - 41-70: OTP Verification
    - 71-90: Temporary Hold
    - 91-100: Block and Investigate
    """
    score = max(0.0, min(100.0, float(risk_score)))
    if score <= 40.0:
        return "Approve"
    if score <= 70.0:
        return "OTP Verification"
    if score <= 90.0:
        return "Temporary Hold"
    return "Block and Investigate"


def get_action_metadata(action: str) -> Dict[str, str]:
    """Return UI styling metadata and operational guidance for an action."""
    mapping = {
        "Approve": {
            "color": "#10B981",
            "bg_color": "rgba(16, 185, 129, 0.15)",
            "severity": "LOW",
            "icon": "✓",
            "playbook": "Auto-clear transaction through standard settlement rail.",
        },
        "OTP Verification": {
            "color": "#F59E0B",
            "bg_color": "rgba(245, 158, 11, 0.15)",
            "severity": "MEDIUM",
            "icon": "⚡",
            "playbook": "Trigger step-up 2FA / biometric challenge before settlement.",
        },
        "Temporary Hold": {
            "color": "#F97316",
            "bg_color": "rgba(249, 115, 22, 0.15)",
            "severity": "HIGH",
            "icon": "⏸",
            "playbook": "Place 24h settlement hold and request cardholder confirmation.",
        },
        "Block and Investigate": {
            "color": "#EF4444",
            "bg_color": "rgba(239, 68, 68, 0.18)",
            "severity": "CRITICAL",
            "icon": "⛔",
            "playbook": "Immediately block transaction, freeze linked device token, and escalate to SOC Fraud Ring unit.",
        },
    }
    return mapping.get(
        action,
        {
            "color": "#94A3B8",
            "bg_color": "rgba(148, 163, 184, 0.15)",
            "severity": "UNKNOWN",
            "icon": "•",
            "playbook": "Review manually.",
        },
    )
