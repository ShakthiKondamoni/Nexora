from fastapi import APIRouter,Query,HTTPException,Request
import secrets
from fastapi.responses import RedirectResponse,HTMLResponse
from backend.services import github_service as s
router=APIRouter(prefix='/api/github')
@router.get('/status')
def status():return s.status()
@router.get('/connect')
def connect(request:Request):
 from backend.services import auth_service as auth
 browser=secrets.token_urlsafe(32);session=auth.session_for_token(request.cookies.get(auth.SESSION_COOKIE))
 url=s.authorization_url(browser,session['token_hash'] if session else None)
 response=RedirectResponse(url,status_code=303)
 response.set_cookie('github_oauth_flow',browser,max_age=600,path='/',secure=auth.secure_cookies(),httponly=True,samesite='lax')
 return response
@router.get('/callback')
def callback(request:Request,code:str='',state:str='',error:str=''):
 from backend.services import auth_service as auth
 browser=request.cookies.get('github_oauth_flow');session=auth.session_for_token(request.cookies.get(auth.SESSION_COOKIE))
 if auth.owner_exists() and not session:return RedirectResponse('/?github_error=session_expired',status_code=303)
 session_hash=session['token_hash'] if session else None
 try:
  if error:s.cancel(state,browser,session_hash);target='/?github_error=authorization_denied'
  else:s.finish(code,state,browser,session_hash);target='/?github_connected=1'
 except HTTPException as exc:
  target='/?github_error=session_expired' if 'session' in str(exc.detail).lower() else '/?github_error=authorization_failed'
 response=RedirectResponse(target,status_code=303)
 response.delete_cookie('github_oauth_flow',path='/',secure=auth.secure_cookies(),httponly=True,samesite='lax')
 return response
@router.delete('/connection')
def disconnect():return s.disconnect()
@router.get('/repos')
def repos(page:int=Query(1,ge=1)):return s.repositories(page)
@router.get('/repos/{rid}/branches')
def branches(rid:int):return s.branches(rid)
@router.get('/repos/{rid}/tree')
def tree(rid:int,branch:str):return s.tree(rid,branch)
@router.get('/repos/{rid}/preview')
def preview(rid:int,branch:str,path:str):return s.preview_repo(rid,branch,path)
@router.post('/projects')
def create(body:dict):return s.create_project(body.get('repo_id'),body.get('branch'),body.get('paths'))
@router.get('/projects')
def projects():return {'projects':s.projects()}
@router.get('/projects/{pid}')
def project(pid:str):
 p=s._project(pid);p['files']=s.files(pid);return p
@router.get('/projects/{pid}/files')
def files(pid:str):return {'files':s.files(pid)}
@router.get('/projects/{pid}/preview')
def project_preview(pid:str,path:str):return s.preview_file(pid,path)
@router.post('/projects/{pid}/sync')
def sync(pid:str,body:dict={}):return s.sync_project(pid,body.get('branch'))
@router.delete('/projects/{pid}')
def remove(pid:str):return s.remove_project(pid)
@router.get('/jobs/{jid}')
def job(jid:str):return s.job(jid)
@router.post('/jobs/{jid}/cancel')
def cancel(jid:str):return s.cancel(jid)
@router.get('/projects/{pid}/conversations')
def conversations(pid:str,branch:str):return {'conversations':s.conversations(pid,branch)}
@router.get('/projects/{pid}/conversations/{cid}/messages')
def messages(pid:str,cid:str):return {'messages':s.messages(pid,cid)}
@router.post('/projects/{pid}/chat')
def chat(pid:str,body:dict):return s.chat(pid,body.get('question',''),body.get('model',''),body.get('ctx',4096),body.get('conversation_id'),body.get('branch'))
