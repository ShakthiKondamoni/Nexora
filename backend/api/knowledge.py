"""HTTP contracts retained from the supplied application; implementation lives in services."""
from typing import List
from fastapi import APIRouter, Form, File, UploadFile
from backend.services import knowledge_service as service, document_chat_service

router = APIRouter(prefix='/api/kb')

@router.get('/doc-chat/selection')
def doc_chat_selection():
    return document_chat_service.selection()

@router.get('/collections')
def colls():
    return service.colls()

@router.post('/collections')
def mk_coll(body: dict):
    return service.mk_coll(body)

@router.patch('/collections/{i}')
def ren_coll(i: str, body: dict):
    return service.ren_coll(i, body)

@router.delete('/collections/{i}')
def del_coll(i: str):
    return service.del_coll(i)

@router.get('/collections/{i}/export')
def exp_coll(i: str):
    return service.exp_coll(i)

@router.get('/sources')
def sources(coll: str=''):
    return service.sources(coll)

@router.post('/sources')
async def add(coll: str=Form(...), ocr_model: str=Form(''), files: List[UploadFile]=File(...)):
    return await service.add(coll, ocr_model, files)

@router.get('/sources/{sid}')
def src(sid: str):
    return service.src(sid)

@router.delete('/sources/{sid}')
def del_src(sid: str):
    return service.del_src(sid)

@router.post('/sources/{sid}/reindex')
def re_src(sid: str, body: dict={}):
    return service.re_src(sid, body)

@router.get('/sources/{sid}/pages/{n}')
def page(sid: str, n: int):
    return service.page(sid, n)

@router.get('/sources/{sid}/pages/{n}/image')
def page_img(sid: str, n: int):
    return service.page_img(sid, n)

@router.post('/sources/{sid}/pages/{n}/retry')
def retry(sid: str, n: int, body: dict={}):
    return service.retry(sid, n, body)

@router.get('/sources/{sid}/export')
def export(sid: str, fmt: str='txt'):
    return service.export(sid, fmt)

@router.get('/search')
def search(q: str, coll: str=''):
    return service.search(q, coll)


@router.get('/sources/{sid}/text')
def document_text(sid: str):
    return service.document_text(sid)

@router.post('/collections/{i}/ask')
def ask_collection(i: str, body: dict):
    return service.ask_collection(i, body)
