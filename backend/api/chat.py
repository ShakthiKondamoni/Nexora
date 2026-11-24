"""HTTP contracts retained from the supplied application; implementation lives in services."""
from typing import List
from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from io import BytesIO
import re
from backend.services import knowledge_service
from backend.services import chat_service as service

router = APIRouter(prefix='')

@router.get('/api/chats')
def chats():
    return service.chats()

@router.post('/api/chats')
def new_chat():
    return service.new_chat()

@router.patch('/api/chats/{i}')
def patch(i: str, body: dict):
    return service.patch(i, body)

@router.delete('/api/chats/{i}')
def delete(i: str):
    return service.delete(i)

@router.get('/api/chats/{i}/messages')
def messages(i: str):
    return service.messages(i)

@router.delete('/api/chats/{i}/last')
def drop_last(i: str):
    return service.drop_last(i)

@router.post('/api/projects')
def mk_project(body: dict):
    return service.mk_project(body)

@router.post('/api/chats/{cid}/send')
async def send(cid: str, text: str=Form(''), model: str=Form(''), ctx: int=Form(0), system: str=Form(''), regenerate: bool=Form(False), kb: str=Form(''), web_mode: str=Form('off'), doc_mode: bool=Form(False), files: List[UploadFile]=File(default=[])):
    return await service.send(cid, text, model, ctx, system, regenerate, kb, files, web_mode, doc_mode)

@router.post('/api/chats/{cid}/sources/{sid}/save')
async def save_web_source(cid: str, sid: str, body: dict):
    source=service.web_source(cid,sid);collection_id=str(body.get('collection_id') or '')
    if not source.get('content'):raise HTTPException(422,'This source has no extractable text.')
    title=re.sub(r'[^A-Za-z0-9._-]+','_',str(source.get('title') or 'web-source')).strip('._-')[:80] or 'web-source'
    note='Full extracted page' if source.get('full') else 'Search-result snippet only'
    text='# '+str(source.get('title') or 'Web source')+'\n\n'+f"Source URL: {source.get('url','')}\nRetrieved: {source.get('retrieved_at','')}\nExtraction: {note}\n\n"+str(source.get('content') or source.get('snippet') or '')
    upload=UploadFile(filename=title+'.md',file=BytesIO(text.encode('utf-8')))
    return {'results':await knowledge_service.add(collection_id,'',[upload])}


