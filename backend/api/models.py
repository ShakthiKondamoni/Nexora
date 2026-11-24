"""HTTP contracts retained from the supplied application; implementation lives in services."""
from typing import List
from fastapi import APIRouter, Form, File, UploadFile
from backend.services import ollama_service as service

router = APIRouter(prefix='')

@router.get('/api/models')
def models():
    return service.models()

@router.post('/api/test')
def test(body: dict):
    return service.test(body)

