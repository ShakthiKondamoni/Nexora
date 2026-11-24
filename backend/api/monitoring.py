"""HTTP contracts retained from the supplied application; implementation lives in services."""
from typing import List
from fastapi import APIRouter, Form, File, UploadFile
from backend.services import monitoring_service as service

router = APIRouter(prefix='')

@router.get('/api/metrics')
def metrics():
    return service.metrics()

@router.get('/api/processes')
def procs():
    return service.procs()

