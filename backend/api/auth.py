import secrets, time
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from backend.services import auth_service as s
from backend.services import github_service
router=APIRouter(prefix='/api/auth')

def _secure(request): return s.secure_cookies()
def _csrf_cookie(response,request,token=None):
    token=token or secrets.token_urlsafe(32)
    response.set_cookie(s.CSRF_COOKIE,token,max_age=s.SESSION_SECONDS,path='/',secure=_secure(request),httponly=False,samesite='strict')
    return token
def _session_response(request,raw,body,redirect=None):
    response=RedirectResponse(redirect,status_code=303) if redirect else JSONResponse(body)
    response.set_cookie(s.SESSION_COOKIE,raw,max_age=s.SESSION_SECONDS,path='/',secure=_secure(request),httponly=True,samesite='strict')
    _csrf_cookie(response,request)
    return response
def _clear_flow(response,request,name): response.delete_cookie(name,path='/',secure=_secure(request),httponly=True,samesite='lax')

@router.get('/status')
def status(request:Request):
    token=request.cookies.get(s.CSRF_COOKIE) or secrets.token_urlsafe(32)
    response=JSONResponse(s.public_status(request.cookies.get(s.SESSION_COOKIE),token))
    _csrf_cookie(response,request,token)
    response.headers['Cache-Control']='no-store'
    return response

@router.post('/register')
def register(body:dict,request:Request):
    raw=s.register(body.get('email',''),body.get('password',''))
    return _session_response(request,raw,{'ok':True,'message':'Local account created.'})

@router.post('/login')
def login(body:dict,request:Request):
    raw=s.login(body.get('email',''),body.get('password',''))
    return _session_response(request,raw,{'ok':True,'message':'Signed in.'})

@router.post('/logout')
def logout(request:Request):
    s.logout(request.cookies.get(s.SESSION_COOKIE))
    response=JSONResponse({'ok':True})
    response.delete_cookie(s.SESSION_COOKIE,path='/',secure=_secure(request),httponly=True,samesite='strict')
    _csrf_cookie(response,request)
    return response

@router.post('/password/forgot')
def forgot(body:dict): return s.send_reset(body.get('email',''))

@router.post('/password/reset')
def reset(body:dict,request:Request):
    raw=s.reset_password(body.get('token',''),body.get('password',''))
    return _session_response(request,raw,{'ok':True,'message':'Password updated.'})

@router.post('/password/change')
def change(body:dict,request:Request):
    raw=s.change_password(request.cookies.get(s.SESSION_COOKIE),body.get('current_password',''),body.get('new_password',''))
    return _session_response(request,raw,{'ok':True,'message':'Password updated.'})

@router.get('/setup/status')
def setup_status(request:Request):
    sess=s.session_for_token(request.cookies.get(s.SESSION_COOKIE))
    result=s.setup_status(sess)
    result['github']=github_service.status()
    return result

@router.post('/setup/google')
def configure_google(body:dict):
    cid=(body.get('client_id') or '').strip(); secret=body.get('client_secret') or ''
    if not cid.endswith('.apps.googleusercontent.com') or len(secret)<8 or len(secret)>500: raise HTTPException(400,'Enter a Google OAuth Web Client ID and Client Secret.')
    s.set_secret('google_client_id',cid);s.set_secret('google_client_secret',secret)
    return {'ok':True,'google':s._provider_google()}

@router.delete('/setup/google')
def remove_google():
    s.delete_secret('google_client_id');s.delete_secret('google_client_secret')
    return {'ok':True,'google':s._provider_google()}

@router.post('/setup/github')
def configure_github(body:dict):
    cid=(body.get('client_id') or '').strip();secret=body.get('client_secret') or ''
    if not cid or len(cid)>200 or len(secret)<8 or len(secret)>500: raise HTTPException(400,'Enter a GitHub App Client ID and Client Secret.')
    github_service.configure(cid,secret)
    return {'ok':True,'github':github_service.status()}

@router.delete('/setup/github')
def remove_github():
    result=github_service.clear_configuration()
    return {'ok':True,'warning':result.get('warning'),'github':github_service.status()}

@router.post('/setup/email')
def configure_email(body:dict): return {'ok':True,'email':s.save_smtp(body)}

@router.delete('/setup/email')
def remove_email():
    for name in ('smtp_host','smtp_port','smtp_security','smtp_username','smtp_password','smtp_from'): s.delete_secret(name)
    return {'ok':True,'email':{'configured':False,'ready':False}}

@router.get('/google/start')
def google_start(request:Request):
    flow=s.create_google_flow('login')
    response=RedirectResponse(flow['url'],status_code=303)
    response.set_cookie(s.GOOGLE_FLOW_COOKIE,flow['browser'],max_age=s.FLOW_SECONDS,path='/',secure=_secure(request),httponly=True,samesite='lax')
    return response

@router.post('/google/link')
def google_link(request:Request):
    sess=s.session_for_token(request.cookies.get(s.SESSION_COOKIE))
    if not sess: raise HTTPException(401,'Sign in before linking Google.')
    flow=s.create_google_flow('link',sess['token_hash'])
    response=JSONResponse({'url':flow['url']})
    response.set_cookie(s.GOOGLE_FLOW_COOKIE,flow['browser'],max_age=s.FLOW_SECONDS,path='/',secure=_secure(request),httponly=True,samesite='lax')
    return response

@router.get('/google/callback')
def google_callback(request:Request,code:str='',state:str='',error:str=''):
    browser=request.cookies.get(s.GOOGLE_FLOW_COOKIE)
    current=s.session_for_token(request.cookies.get(s.SESSION_COOKIE))
    session_hash=current['token_hash'] if current else None
    if error:
        try: flow=s.consume_google_denial(state,browser,session_hash)
        except HTTPException:
            response=RedirectResponse('/signin?error=google_state',status_code=303)
        else:
            response=RedirectResponse('/setup?google=denied' if flow.get('session_hash') else '/signin?error=google_denied',status_code=303)
        _clear_flow(response,request,s.GOOGLE_FLOW_COOKIE);return response
    try: result=s.finish_google(code,state,browser,session_hash)
    except HTTPException as exc:
        response=RedirectResponse('/signin?error=google_state' if exc.status_code==400 else '/signin?error=google_failed',status_code=303)
        _clear_flow(response,request,s.GOOGLE_FLOW_COOKIE);return response
    response=_session_response(request,result['session'],{'ok':True},'/setup?google=linked' if result['mode']=='link' else '/')
    _clear_flow(response,request,s.GOOGLE_FLOW_COOKIE)
    return response
