"""Composition root. Run from the project directory with python -m backend.main."""
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from backend.core.config import FRONTEND
from backend.database.schema import initialize_database

initialize_database()
from backend.api import chat, models, settings, knowledge, monitoring, github, auth, code, diagnostics, library
from backend.services.knowledge_service import start_worker
from backend.services import auth_service

app = FastAPI()
for module in (settings, chat, models, monitoring, knowledge, github, auth, code, diagnostics, library):
    app.include_router(module.router)
app.mount('/assets', StaticFiles(directory=FRONTEND/'assets'), name='assets')

@app.middleware('http')
async def local_auth_security(request, call_next):
    path=request.url.path; method=request.method.upper()
    public={'/api/health','/signin','/setup','/api/auth/status','/api/auth/register','/api/auth/login','/api/auth/logout','/api/auth/password/forgot','/api/auth/password/reset','/api/auth/google/start','/api/auth/google/callback','/api/github/callback'}
    owner=auth_service.owner_exists()
    if method not in ('GET','HEAD','OPTIONS') and (owner or path.startswith('/api/auth/')):
        from urllib.parse import urlsplit
        expected=auth_service.app_origin()
        origin=request.headers.get('origin')
        referer=request.headers.get('referer')
        actual=origin or (f'{urlsplit(referer).scheme}://{urlsplit(referer).netloc}' if referer else '')
        if actual.rstrip('/')!=expected:
            return JSONResponse({'error':'Request origin was not trusted.'},status_code=403)
        if not auth_service.csrf_matches(request.cookies.get(auth_service.CSRF_COOKIE),request.headers.get('x-csrf-token')):
            return JSONResponse({'error':'CSRF validation failed. Refresh and try again.'},status_code=403)
    if owner and path not in public and not path.startswith('/assets/'):
        session=auth_service.session_for_token(request.cookies.get(auth_service.SESSION_COOKIE))
        if not session:
            if path.startswith('/api/'):
                return JSONResponse({'error':'Sign in to continue.','code':'authentication_required'},status_code=401)
            return RedirectResponse('/signin?expired=1',status_code=303)
        request.state.auth_user=session
    response=await call_next(request)
    response.headers.setdefault('X-Content-Type-Options','nosniff')
    response.headers.setdefault('X-Frame-Options','DENY')
    response.headers.setdefault('Referrer-Policy','same-origin')
    return response


@app.get('/')
def index():
    return FileResponse(FRONTEND/'index.html')

@app.get('/signin')
def signin():
    return FileResponse(FRONTEND/'signin.html',headers={'Cache-Control':'no-store'})

@app.get('/setup')
def setup():
    return FileResponse(FRONTEND/'setup.html',headers={'Cache-Control':'no-store'})

start_worker()

def run():
    uvicorn.run(app, host='127.0.0.1', port=8501)

if __name__ == '__main__':
    run()
