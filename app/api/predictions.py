"""API routes for prediction/forecast endpoints (Wave D.1).

JWT-protected, client-scoped. Every endpoint returns heuristic estimates
documented as MVP — not ML accuracy.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from auth import get_current_client
from app.services.prediction_service import (
    predict_cancellation_risk,
    predict_cashflow,
    predict_inventory,
    predict_revenue,
)
from database import SessionLocal

logger = logging.getLogger("api.predictions")
router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/revenue")
def get_revenue(client: dict = Depends(get_current_client)):
    db = next(_get_db())
    try:
        return predict_revenue(db, client.id)
    finally:
        db.close()


@router.get("/cancellation-risk")
def get_cancellation_risk(client: dict = Depends(get_current_client)):
    db = next(_get_db())
    try:
        return predict_cancellation_risk(db, client.id)
    finally:
        db.close()


@router.get("/inventory")
def get_inventory_prediction(client: dict = Depends(get_current_client)):
    db = next(_get_db())
    try:
        return predict_inventory(db, client.id)
    finally:
        db.close()


@router.get("/cashflow")
def get_cashflow(client: dict = Depends(get_current_client)):
    db = next(_get_db())
    try:
        return predict_cashflow(db, client.id)
    finally:
        db.close()
