"""Health and authenticated diagnostics endpoints."""
from fastapi import APIRouter
from backend.services.diagnostics_service import collect
router=APIRouter()
@router.get("/api/health")
def health():return {"status":"Ready","service":"Nexora"}
@router.get("/api/diagnostics")
def diagnostics():return collect()
