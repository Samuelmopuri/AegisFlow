# 🛡️ SentinelGraph — Real-Time Financial Fraud Intelligence Platform

A full-stack, real-time financial fraud detection, explainable risk scoring, pattern discovery, and graph intelligence platform built with **Python, Streamlit, Supabase (PostgreSQL), FastAPI, Pandas, Scikit-learn, NetworkX, Plotly, and PyVis**.

---

## ✨ Core Capabilities

1. **Real-Time Transaction Risk Scoring (`0–100`) & Explainable AI**
   - Hybrid **Scikit-learn `IsolationForest`** statistical anomaly model + behavioral risk rules.
   - Generates itemized human-readable explanations for every transaction:
     - *Unusually high amount*
     - *New device used*
     - *Unusual location*
     - *Unusual transaction timing*
     - *Rapid transaction velocity / Structuring near reporting thresholds*
2. **Account Risk Scoring & Aggregation**
   - Aggregates transaction risk, device proliferation, geographic dispersion, and fraud ring membership into an account-level score (`0–100`) with clear explanations.
3. **Heterogeneous Graph Fraud Ring Detection (`NetworkX`)**
   - Builds a multipartite graph linking **Accounts**, **Devices**, **Merchants**, and **Locations**.
   - Detects connected mule clusters and communities sharing infrastructure or synchronized behavior, producing `ring_risk_score`, `pattern_detected`, and `accounts_involved`.
4. **Automated Pattern Discovery**
   - Detects:
     - Multiple accounts using same device
     - Multiple accounts using same merchant
     - Similar transaction amounts (Structuring / Smurfing)
     - Transactions occurring within short time windows (High-velocity bursts)
5. **Deterministic Action Recommendation Engine**
   - `0–40` → **Approve**
   - `41–70` → **OTP Verification**
   - `71–90` → **Temporary Hold**
   - `91–100` → **Block and Investigate**
6. **Interactive Multi-Page Streamlit Dashboard + PyVis Network Graph**
   - **Transaction Monitoring** (with live attack simulator & custom transaction evaluator)
   - **Account Monitoring** (with 360° account forensic profile drill-down)
   - **Fraud Rings** (with ring forensics and 4-tab pattern discovery explorer)
   - **Network Graph Visualization** (interactive PyVis canvas + hub centrality table)
   - **Analytics Overview** (executive KPIs & Plotly visualizations)

---

## 📁 Project Structure

```text
c:\REVS\
├── .env.example                  # Supabase & API environment variable template
├── README.md                     # Documentation & quickstart guide
├── requirements.txt              # Pinned Python dependencies
├── app.py                        # Main Streamlit dashboard entrypoint
├── database/
│   ├── schema.sql                # Production Supabase (PostgreSQL) DDL, indexes, RLS, Realtime
│   ├── client.py                 # Dual-mode DB client (Supabase PostgreSQL + automatic SQLite fallback)
│   └── seed.py                   # Synthetic baseline & multi-account fraud ring generator
├── engine/
│   ├── action_engine.py          # Risk-to-Action threshold policy (0-40, 41-70, 71-90, 91-100)
│   ├── transaction_scorer.py     # Hybrid Scikit-learn IsolationForest + Behavioral Scorer
│   ├── account_scorer.py         # Account-level Risk Aggregation & Explainability
│   ├── pattern_detector.py       # Pattern Discovery (shared device/merchant, similar amounts, bursts)
│   ├── fraud_ring_detector.py    # NetworkX Graph Builder & Fraud Ring Cluster Detector
│   └── pipeline.py               # End-to-end Real-Time Intelligence Pipeline orchestrator
├── api/
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── routes.py                 # FastAPI endpoints (/api/transactions, /api/accounts, /api/fraud-rings, etc.)
│   └── main.py                   # FastAPI server entrypoint
├── dashboard/
│   ├── styles.py                 # Custom dark fintech CSS & badge utilities
│   ├── graph_viz.py              # PyVis interactive HTML network builder
│   └── views/
│       ├── transaction_monitoring.py
│       ├── account_monitoring.py
│       ├── fraud_rings.py
│       ├── network_graph.py
│       └── analytics_overview.py
└── tests/
    └── test_platform.py          # Automated pytest verification suite
```

---

## 🚀 Quickstart

### 1. Configure Supabase (Optional)
1. Run the SQL script in [`database/schema.sql`](database/schema.sql) inside your Supabase SQL Editor to create the `accounts`, `transactions`, and `fraud_rings` tables.
2. Copy `.env.example` to `.env` and fill in `SUPABASE_URL` and `SUPABASE_KEY`.
   *(Note: If `.env` is not configured, the platform automatically uses a local SQLite database with the identical schema so you can demo offline or immediately.)*

### 2. Launch the Streamlit Dashboard
```powershell
.\.venv\Scripts\streamlit run app.py
```

### 3. Launch the FastAPI REST Backend (Optional)
```powershell
.\.venv\Scripts\uvicorn api.main:app --reload --port 8000
```
Interactive Swagger docs are served at `http://localhost:8000/docs`.
