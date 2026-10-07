"""
FastAPI Application Entrypoint for the Real-Time Financial Fraud Intelligence Platform.
Run with:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

app = FastAPI(
    title="AegisFlow — Graph-Powered Financial Fraud Intelligence Platform",
    description=(
        "Production REST API for real-time transaction risk scoring, account risk aggregation, "
        "pattern discovery, and NetworkX fraud ring detection backed by Supabase PostgreSQL."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "platform": "AegisFlow — Graph-Powered Financial Fraud Intelligence Platform",
        "docs": "/docs",
        "health": "/api/health",
    }
