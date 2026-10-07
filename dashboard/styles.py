"""
Modern Fintech UI Styling & Business-Friendly Components for AegisFlow.
Uses strict semantic color coding:
- Green (#10B981)  = Safe (0-40)
- Yellow (#F59E0B) = Medium Risk (41-70)
- Red (#EF4444)    = High Risk (71-100)
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd
import streamlit as st

COLOR_SAFE = "#10B981"      # Green
COLOR_MEDIUM = "#F59E0B"    # Yellow
COLOR_HIGH = "#EF4444"      # Red


def get_risk_level_and_color(score: float) -> Tuple[str, str]:
    """
    Map a 0-100 risk score to business-friendly Risk Level and semantic hex color:
    - 0-40:  Safe (Green)
    - 41-70: Medium Risk (Yellow)
    - 71-100: High Risk (Red)
    """
    val = float(score)
    if val <= 40.0:
        return "Safe", COLOR_SAFE
    if val <= 70.0:
        return "Medium Risk", COLOR_MEDIUM
    return "High Risk", COLOR_HIGH


def risk_color(score: float) -> str:
    """Return hex color (Green / Yellow / Red) for a 0-100 risk score."""
    _, color = get_risk_level_and_color(score)
    return color


def format_risk_badge_html(score: float) -> str:
    """Return a clean pill badge showing Risk Level and Score."""
    level, color = get_risk_level_and_color(score)
    bg_map = {
        COLOR_SAFE: "rgba(16, 185, 129, 0.14)",
        COLOR_MEDIUM: "rgba(245, 158, 11, 0.15)",
        COLOR_HIGH: "rgba(239, 68, 68, 0.16)",
    }
    bg = bg_map.get(color, "rgba(148, 163, 184, 0.15)")
    return (
        f'<span class="aegis-badge" style="background:{bg}; color:{color}; '
        f'border:1px solid {color}55;">● {level} ({score:.0f})</span>'
    )


def format_action_badge_html(action: str, risk_score: float | None = None) -> str:
    """Return a clean business-friendly badge for a Recommended Action."""
    if action == "Approve":
        color = COLOR_SAFE
        bg = "rgba(16, 185, 129, 0.14)"
    elif action == "OTP Verification":
        color = COLOR_MEDIUM
        bg = "rgba(245, 158, 11, 0.15)"
    else:
        color = COLOR_HIGH
        bg = "rgba(239, 68, 68, 0.16)"

    return (
        f'<span class="aegis-badge" style="background:{bg}; color:{color}; '
        f'border:1px solid {color}55;">{action}</span>'
    )


def apply_custom_styles() -> None:
    """Inject clean, minimal, modern fintech dark-mode styling."""
    st.markdown(
        """
        <style>
        /* Layout & Typography */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            max-width: 1380px;
        }

        /* Hero Brand Header */
        .aegis-header {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 1.35rem 1.75rem;
            margin-bottom: 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .aegis-title {
            font-size: 1.65rem;
            font-weight: 800;
            color: #F8FAFC;
            letter-spacing: -0.02em;
            margin: 0;
        }
        .aegis-tagline {
            font-size: 0.95rem;
            color: #94A3B8;
            margin-top: 0.2rem;
        }
        .aegis-legend {
            display: flex;
            gap: 1rem;
            align-items: center;
            background: rgba(15, 23, 42, 0.65);
            padding: 0.5rem 1rem;
            border-radius: 999px;
            border: 1px solid rgba(255, 255, 255, 0.07);
            font-size: 0.82rem;
            color: #E2E8F0;
        }

        /* Large Readable Executive Metric Cards */
        .kpi-card {
            background: #111827;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 1.25rem 1.35rem;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            margin-bottom: 0.75rem;
            transition: transform 0.15s ease;
        }
        .kpi-label {
            color: #94A3B8;
            font-size: 0.82rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            margin-bottom: 0.4rem;
        }
        .kpi-value {
            color: #F8FAFC;
            font-size: 2rem;
            font-weight: 700;
            line-height: 1.15;
        }
        .kpi-sub {
            color: #64748B;
            font-size: 0.8rem;
            margin-top: 0.35rem;
        }

        /* Clean Fintech Feature / Ring Cards */
        .fintech-card {
            background: #111827;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 1.35rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
        }

        /* Pill Badges */
        .aegis-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.01em;
        }

        /* Section Title */
        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #F8FAFC;
            margin-bottom: 0.2rem;
        }
        .section-subtitle {
            font-size: 0.88rem;
            color: #94A3B8;
            margin-bottom: 1.1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, subtitle: str = "", accent_color: str = "#10B981") -> None:
    """Render a large, readable fintech KPI card."""
    st.markdown(
        f"""
        <div class="kpi-card" style="border-top: 3px solid {accent_color};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_executive_overview(state: Dict[str, Any]) -> None:
    """
    Render the top-level AegisFlow header and the 5 required Dashboard Overview KPIs:
    - Total Transactions
    - High Risk Transactions
    - High Risk Accounts
    - Fraud Rings Detected
    - Average Risk Score
    """
    tx_df: pd.DataFrame = state["transactions_df"]
    acc_df: pd.DataFrame = state["accounts_df"]
    rings = state["fraud_rings"]

    total_tx = len(tx_df)
    high_risk_tx = int((tx_df["risk_score"] > 70.0).sum()) if not tx_df.empty else 0
    high_risk_acc = int((acc_df["account_risk_score"] > 70.0).sum()) if not acc_df.empty else 0
    rings_detected = len(rings)
    avg_risk = float(tx_df["risk_score"].mean()) if not tx_df.empty else 0.0
    _, avg_color = get_risk_level_and_color(avg_risk)

    st.markdown(
        f"""
        <div class="aegis-header">
            <div>
                <div class="aegis-title">🛡️ AegisFlow</div>
                <div class="aegis-tagline">Graph-Powered Financial Fraud Intelligence Platform</div>
            </div>
            <div class="aegis-legend">
                <span><strong>Risk Scale:</strong></span>
                <span style="color:{COLOR_SAFE}; font-weight:600;">● Safe (0–40)</span>
                <span style="color:{COLOR_MEDIUM}; font-weight:600;">● Medium Risk (41–70)</span>
                <span style="color:{COLOR_HIGH}; font-weight:600;">● High Risk (71–100)</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_kpi_card(
            "Total Transactions",
            f"{total_tx:,}",
            "Monitored in real time",
            accent_color=COLOR_SAFE,
        )
    with c2:
        render_kpi_card(
            "High Risk Transactions",
            f"{high_risk_tx:,}",
            "Score > 70 (Hold or Block)",
            accent_color=COLOR_HIGH,
        )
    with c3:
        render_kpi_card(
            "High Risk Accounts",
            f"{high_risk_acc:,}",
            "Flagged for review",
            accent_color=COLOR_HIGH,
        )
    with c4:
        render_kpi_card(
            "Fraud Rings Detected",
            f"{rings_detected:,}",
            "Coordinated account clusters",
            accent_color=COLOR_HIGH if rings_detected > 0 else COLOR_SAFE,
        )
    with c5:
        render_kpi_card(
            "Average Risk Score",
            f"{avg_risk:.1f}",
            "0–100 platform risk index",
            accent_color=avg_color,
        )
