"""HTTP contracts retained from the supplied application; implementation lives in services."""
from typing import List
from fastapi import APIRouter, Form, File, UploadFile
from backend.services import settings_service as service
from backend.services import web_research_service
from fastapi import HTTPException

router = APIRouter(prefix='')

@router.get('/api/settings')
def read_settings():
    return service.read_settings()

@router.put('/api/settings')
def write_settings(body: dict):
    return service.write_settings(body)

@router.post('/api/settings/test-connection')
def test_connection(body: dict={}):
    return service.test_connection(body)


@router.post('/api/settings/test-web-search')
def test_web_search(body: dict={}):
    try:return web_research_service.test_provider(body.get('instance_url'),body.get('timeout'))
    except Exception as e:raise HTTPException(503,str(e)[:400])
