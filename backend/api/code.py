"""Authenticated local coding APIs. No project commands are executed."""
from urllib.parse import urlsplit
from fastapi import APIRouter,Form,HTTPException
from backend.services import code_workspace_service as ws,chat_service,settings_service
router=APIRouter(prefix='')
def call(fn,*a):
 try:return fn(*a)
 except ws.WorkspaceError as e:raise HTTPException(400,str(e))
@router.post('/api/code/project/select')
def select_project():
 try:
  import tkinter as tk
  from tkinter import filedialog
  r=tk.Tk();r.withdraw();r.attributes('-topmost',True);path=filedialog.askdirectory(parent=r,title='Select a Nexora project folder');r.destroy()
  if not path:raise HTTPException(400,'No folder selected.')
  return call(ws.register,path)
 except HTTPException:raise
 except Exception:raise HTTPException(503,'Native folder selection is unavailable. Use a desktop session.')
@router.post('/api/code/projects')
def register_project(body:dict):return call(ws.register,body.get('path'))
@router.get('/api/code/projects/{token}/files')
def files(token:str):return call(ws.list_files,token)
@router.get('/api/code/projects/{token}/file')
def file(token:str,path:str):return {'path':path,'content':call(ws.read_file,call(ws.project,token),path)}
@router.get('/api/code/projects/{token}/search')
def search(token:str,q:str='',selected:str=''):return call(ws.search,token,q,selected)
@router.post('/api/code/projects/{token}/patch/preview')
def preview(token:str,body:dict):
 cs=call(ws.preview,call(ws.project,token),body.get('patch',''))
 return {'files':[{'path':c['path'],'old_sha256':c['old_sha256'],'new_sha256':c['new_sha256']} for c in cs],'diff':body.get('patch',''),'summary':f"Validated against {len(cs)} file(s). No files changed."}
@router.post('/api/code/projects/{token}/patch/apply')
def apply(token:str,body:dict):return call(ws.apply_patch,call(ws.project,token),body.get('patch',''),body.get('expected_hashes'))
@router.post('/api/code/chats/{cid}/send')
async def code_send(cid:str,text:str=Form(''),model:str=Form(''),ctx:int=Form(0),system:str=Form(''),regenerate:bool=Form(False),web_mode:str=Form('off')):
 if not ws.is_local_ollama_url(settings_service.ollama_url()):raise HTTPException(409,'Code context is sent only to a loopback Ollama endpoint. Set the Ollama URL to localhost, 127.0.0.1, or ::1 and retry.')
 return await chat_workspace_send(cid,text,model,ctx,system,regenerate,web_mode)
async def chat_workspace_send(cid,text,model,ctx,system,regenerate,web_mode):
 return await chat_service.send(cid,text,model,ctx,system,regenerate,'',[],web_mode)
