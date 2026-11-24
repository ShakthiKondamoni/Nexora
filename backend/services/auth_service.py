import hashlib, hmac, re, secrets, smtplib, ssl, time
from contextlib import contextmanager
from email.message import EmailMessage
from urllib.parse import urlencode, urlsplit
import keyring, requests
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import HTTPException
from backend.database.connection import connect, q

SERVICE='LocalAIStudio.Auth'
SESSION_COOKIE='studio_session'
CSRF_COOKIE='studio_csrf'
GOOGLE_FLOW_COOKIE='google_oauth_flow'
GOOGLE_CALLBACK='/api/auth/google/callback'
SESSION_SECONDS=12*60*60
FLOW_SECONDS=10*60
RESET_SECONDS=60*60
PH=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2,hash_len=32,salt_len=16)
EMAIL_RE=re.compile(r'^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$')

def digest(v): return hashlib.sha256((v or '').encode('utf-8')).hexdigest()
def normalize_email(value): return (value or '').strip().casefold()
def valid_email(value): return bool(value and len(value)<=254 and EMAIL_RE.fullmatch(value))
def validate_password(value):
    if not isinstance(value,str) or len(value)<12: raise HTTPException(400,'Use a password with at least 12 characters.')
    if len(value)>1024: raise HTTPException(400,'Password is too long.')
    return value

def app_origin():
    raw=__import__('os').environ.get('STUDIO_PUBLIC_ORIGIN','http://127.0.0.1:8501').strip().rstrip('/')
    u=urlsplit(raw)
    if u.scheme not in ('http','https') or u.hostname not in ('127.0.0.1','localhost','::1') or not u.port or u.path or u.query or u.fragment or u.username or u.password:
        raise RuntimeError('STUDIO_PUBLIC_ORIGIN must be a loopback origin such as http://127.0.0.1:8501.')
    return raw

def secure_cookies(): return urlsplit(app_origin()).scheme=='https'

@contextmanager
def db():
    c=connect()
    try:
        with c: yield c
    finally: c.close()

def owner_record(): return q('SELECT id,email,password_hash,google_sub,created,updated FROM auth_owner WHERE id=1',one=True)
def owner_exists(): return owner_record() is not None

def _keyring_ready():
    try:
        backend=keyring.get_keyring()
        priority=getattr(backend,'priority',1)
        if callable(priority): priority=priority()
        if priority is None or float(priority)<=0: return False
        return True
    except Exception: return False

def get_secret(name):
    if not _keyring_ready(): raise HTTPException(503,'OS credential manager is unavailable; provider secrets were not saved.')
    try: return keyring.get_password(SERVICE,name)
    except Exception as exc: raise HTTPException(503,'OS credential manager could not read provider settings.') from exc

def set_secret(name,value):
    if not _keyring_ready(): raise HTTPException(503,'OS credential manager is unavailable; provider secrets were not saved.')
    try: keyring.set_password(SERVICE,name,str(value))
    except Exception as exc: raise HTTPException(503,'OS credential manager could not store provider settings.') from exc

def delete_secret(name):
    old=get_secret(name)
    if old is None: return
    try: keyring.delete_password(SERVICE,name)
    except Exception as exc: raise HTTPException(503,'OS credential manager could not remove provider settings.') from exc

def _provider_google():
    try:
        cid=get_secret('google_client_id'); secret=get_secret('google_client_secret')
        good=bool(cid and secret and cid.endswith('.apps.googleusercontent.com'))
        return {'configured':good,'ready':good,'storage_available':True}
    except HTTPException: return {'configured':False,'ready':False,'storage_available':False}

def _provider_github():
    try:
        from backend.services import github_service
        st=github_service.status()
        return {'configured':bool(st.get('configured')),'ready':bool(st.get('configured')),'connected':bool(st.get('connected')),'login':st.get('login') if st.get('connected') else None,'callback_url':st.get('callback_url'),'storage_available':not bool(st.get('storage_error'))}
    except Exception: return {'configured':False,'ready':False,'connected':False,'login':None,'storage_available':False}

def _smtp_config():
    names=('smtp_host','smtp_port','smtp_security','smtp_username','smtp_password','smtp_from')
    vals={k:get_secret(k) for k in names}
    if not vals['smtp_host'] or not vals['smtp_port'] or not vals['smtp_security'] or not valid_email(vals['smtp_from'] or ''): return None
    try: port=int(vals['smtp_port'])
    except (ValueError,TypeError): return None
    if not (1<=port<=65535) or vals['smtp_security'] not in ('starttls','ssl'): return None
    return {'host':vals['smtp_host'],'port':port,'security':vals['smtp_security'],'username':vals['smtp_username'] or '', 'password':vals['smtp_password'] or '', 'from':vals['smtp_from']}

def setup_status(session=None):
    owner=owner_record()
    try: smtp=_smtp_config(); smtp_ready=bool(smtp)
    except HTTPException: smtp_ready=False
    return {'owner_exists':bool(owner),'authenticated':bool(session),'owner_email':owner['email'] if owner and session else None,'auth_required':bool(owner),'google':_provider_google(),'github':_provider_github(),'email':{'configured':smtp_ready,'ready':smtp_ready},'callbacks':{'google':app_origin()+GOOGLE_CALLBACK,'github':app_origin()+'/api/github/callback'},'authorized_origin':app_origin()}

def public_status(raw_session=None,csrf=None):
    sess=session_for_token(raw_session)
    st=setup_status(sess)
    st['csrf_token']=csrf
    return st

def _limit(bucket, maximum=8, window=900):
    now=time.time(); key=digest(bucket)
    with db() as c:
        row=c.execute('SELECT window_start,attempts FROM auth_rate_limits WHERE bucket=?',(key,)).fetchone()
        if row and now-row['window_start']<window:
            if row['attempts']>=maximum: return False
            c.execute('UPDATE auth_rate_limits SET attempts=attempts+1 WHERE bucket=?',(key,))
        else: c.execute('INSERT OR REPLACE INTO auth_rate_limits(bucket,window_start,attempts) VALUES(?,?,1)',(key,now))
    return True

def _clear_limit(bucket):
    with db() as c: c.execute('DELETE FROM auth_rate_limits WHERE bucket=?',(digest(bucket),))

def new_session(rotate_from=None):
    raw=secrets.token_urlsafe(48); hashed=digest(raw); now=time.time()
    with db() as c:
        c.execute('DELETE FROM auth_sessions WHERE expires<=?',(now,))
        if rotate_from: c.execute('DELETE FROM auth_sessions WHERE token_hash=?',(rotate_from,))
        c.execute('INSERT INTO auth_sessions(token_hash,created,expires,last_seen) VALUES(?,?,?,?)',(hashed,now,now+SESSION_SECONDS,now))
    return raw

def session_for_token(raw):
    if not raw or len(raw)>200: return None
    hashed=digest(raw); now=time.time()
    with db() as c:
        row=c.execute('SELECT expires FROM auth_sessions WHERE token_hash=?',(hashed,)).fetchone()
        if not row: return None
        if row['expires']<=now:
            c.execute('DELETE FROM auth_sessions WHERE token_hash=?',(hashed,));return None
        owner=c.execute('SELECT email FROM auth_owner WHERE id=1').fetchone()
        if not owner: return None
        c.execute('UPDATE auth_sessions SET last_seen=? WHERE token_hash=?',(now,hashed))
        return {'email':owner['email'],'token_hash':hashed}

def register(email,password):
    email=normalize_email(email)
    if not valid_email(email): raise HTTPException(400,'Enter a valid email address.')
    validate_password(password)
    hashed=PH.hash(password); now=time.time()
    try:
        with db() as c:
            if c.execute('SELECT 1 FROM auth_owner LIMIT 1').fetchone(): raise HTTPException(409,'This local installation already has its single owner account. Sign in instead.')
            c.execute('INSERT INTO auth_owner(id,email,password_hash,google_sub,created,updated) VALUES(1,?,?,NULL,?,?)',(email,hashed,now,now))
    except HTTPException: raise
    except Exception as exc: raise HTTPException(409,'A local account was created concurrently. Please sign in.') from exc
    return new_session()

def login(email,password):
    email=normalize_email(email)
    if not _limit('login:'+email): raise HTTPException(429,'Too many sign-in attempts. Try again later.')
    row=q('SELECT id,email,password_hash FROM auth_owner WHERE id=1 AND email=?',(email,),one=True)
    ok=False
    if row and row.get('password_hash'):
        try: ok=PH.verify(row['password_hash'],password or '')
        except (VerifyMismatchError,InvalidHashError,ValueError): ok=False
    if not ok: raise HTTPException(401,'Email or password was not recognized.')
    _clear_limit('login:'+email)
    return new_session()

def logout(raw):
    if raw:
        with db() as c:c.execute('DELETE FROM auth_sessions WHERE token_hash=?',(digest(raw),))

def change_password(raw,current,new_password):
    sess=session_for_token(raw)
    if not sess: raise HTTPException(401,'Your session expired. Sign in again.')
    validate_password(new_password)
    row=q('SELECT password_hash FROM auth_owner WHERE id=1',one=True)
    if not row or not row.get('password_hash'): raise HTTPException(400,'This account has no local password; use its connected sign-in provider.')
    try: valid=PH.verify(row['password_hash'],current or '')
    except (VerifyMismatchError,InvalidHashError,ValueError): valid=False
    if not valid: raise HTTPException(401,'Current password was not recognized.')
    hashed=PH.hash(new_password); now=time.time()
    with db() as c:
        c.execute('UPDATE auth_owner SET password_hash=?,updated=? WHERE id=1',(hashed,now))
        c.execute('DELETE FROM auth_sessions')
    return new_session()

def _new_oauth_state(provider,browser,verifier,nonce,session_hash=None):
    state=secrets.token_urlsafe(32); now=time.time()
    with db() as c:
        c.execute('DELETE FROM auth_oauth_state WHERE created<?',(now-FLOW_SECONDS,))
        c.execute('INSERT INTO auth_oauth_state(state_hash,provider,verifier,nonce,browser_hash,session_hash,created) VALUES(?,?,?,?,?,?,?)',(digest(state),provider,verifier,nonce,digest(browser),session_hash,now))
    return state

def consume_oauth_state(provider,state,browser):
    if not state or not browser: raise HTTPException(400,'Authorization state expired or did not match. Start again.')
    key=digest(state)
    with db() as c:
        row=c.execute('SELECT * FROM auth_oauth_state WHERE state_hash=?',(key,)).fetchone()
        c.execute('DELETE FROM auth_oauth_state WHERE state_hash=?',(key,))
    if not row or row['provider']!=provider or time.time()-row['created']>FLOW_SECONDS or not hmac.compare_digest(row['browser_hash'],digest(browser)):
        raise HTTPException(400,'Authorization state expired or did not match. Start again.')
    return dict(row)

def create_google_flow(mode='login',session_hash=None):
    cfg=_provider_google()
    if not cfg['ready']: raise HTTPException(503,'Google sign-in is not configured. Open Account & Integrations to set it up.')
    cid=get_secret('google_client_id'); verifier=secrets.token_urlsafe(48); challenge=__import__('base64').urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    state=secrets.token_urlsafe(32); nonce=secrets.token_urlsafe(32); browser=secrets.token_urlsafe(32)
    with db() as c:
        c.execute('DELETE FROM auth_oauth_state WHERE created<?',(time.time()-FLOW_SECONDS,))
        c.execute('INSERT INTO auth_oauth_state(state_hash,provider,verifier,nonce,browser_hash,session_hash,created) VALUES(?,?,?,?,?,?,?)',(digest(state),'google',verifier,nonce,digest(browser),session_hash,time.time()))
    redirect=app_origin()+GOOGLE_CALLBACK
    params={'client_id':cid,'redirect_uri':redirect,'response_type':'code','scope':'openid email profile','state':state,'nonce':nonce,'code_challenge':challenge,'code_challenge_method':'S256'}
    return {'url':'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode(params),'state':state,'browser':browser,'mode':mode}

def _verify_google_token(raw_token,client_id,nonce):
    try:
        from google.oauth2 import id_token
        from google.auth.transport.requests import Request
        claims=id_token.verify_oauth2_token(raw_token,Request(),audience=client_id)
    except Exception as exc: raise HTTPException(401,'Google identity could not be verified. Try again.') from exc
    if claims.get('iss') not in ('accounts.google.com','https://accounts.google.com'): raise HTTPException(401,'Google identity issuer was invalid.')
    aud=claims.get('aud')
    if isinstance(aud,list) and len(aud)>1 and claims.get('azp')!=client_id: raise HTTPException(401,'Google identity audience was invalid.')
    if not claims.get('sub') or not valid_email(claims.get('email','')) or claims.get('email_verified') not in (True,'true','True') or not hmac.compare_digest(str(claims.get('nonce','')),nonce):
        raise HTTPException(401,'Google identity could not be verified. Try again.')
    return claims

def finish_google(code,state,browser,session_hash=None):
    flow=consume_oauth_state('google',state,browser)
    if flow['session_hash']!=session_hash: raise HTTPException(401,'Your sign-in session expired. Start again.')
    if not code: raise HTTPException(400,'Google authorization response was incomplete.')
    cid=get_secret('google_client_id'); secret=get_secret('google_client_secret')
    try:
        resp=requests.post('https://oauth2.googleapis.com/token',data={'code':code,'client_id':cid,'client_secret':secret,'redirect_uri':app_origin()+GOOGLE_CALLBACK,'grant_type':'authorization_code','code_verifier':flow['verifier']},timeout=(8,20))
        if resp.status_code>=400: raise HTTPException(502,'Google sign-in could not be completed. Check provider setup.')
        token=resp.json().get('id_token')
    except requests.RequestException as exc: raise HTTPException(503,'Could not reach Google sign-in service.') from exc
    if not token: raise HTTPException(502,'Google did not return an identity token.')
    claims=_verify_google_token(token,cid,flow['nonce']); owner=owner_record(); sub=str(claims['sub']); email=normalize_email(claims['email']); now=time.time()
    if flow.get('session_hash'):
        if not owner or session_hash!=flow['session_hash']: raise HTTPException(401,'Your account session expired. Start linking again.')
        if owner.get('google_sub') and owner['google_sub']!=sub: raise HTTPException(409,'A different Google account is already linked.')
        with db() as c:c.execute('UPDATE auth_owner SET google_sub=?,updated=? WHERE id=1',(sub,now))
        return {'mode':'link','email':owner['email'],'session':new_session(rotate_from=session_hash)}
    if not owner:
        try:
            with db() as c:c.execute('INSERT INTO auth_owner(id,email,password_hash,google_sub,created,updated) VALUES(1,?,NULL,?,?,?)',(email,sub,now,now))
        except Exception as exc: raise HTTPException(409,'A local account was created during Google sign-in. Sign in and link Google from settings.') from exc
    elif owner.get('google_sub')!=sub:
        raise HTTPException(409,'This local installation already has an owner. Sign in first, then link Google from settings.')
    return {'mode':'login','email':email,'session':new_session()}

def consume_google_denial(state,browser,session_hash=None):
    flow=consume_oauth_state('google',state,browser)
    if flow['session_hash']!=session_hash: raise HTTPException(401,'Your sign-in session expired. Start again.')
    return flow

def _smtp_connect(cfg):
    try:
        if cfg['security']=='ssl': server=smtplib.SMTP_SSL(cfg['host'],cfg['port'],timeout=8,context=ssl.create_default_context())
        else:
            server=smtplib.SMTP(cfg['host'],cfg['port'],timeout=8);server.ehlo();server.starttls(context=ssl.create_default_context());server.ehlo()
        with server:
            if cfg['username']: server.login(cfg['username'],cfg['password'])
    except Exception as exc: raise HTTPException(400,'Email server connection or authentication failed. Check host, port, TLS, username and password.') from exc

def save_smtp(body):
    host=(body.get('host') or '').strip(); security=body.get('security') or ''; username=(body.get('username') or '').strip(); password=body.get('password') or ''; sender=normalize_email(body.get('from_email') or '')
    try: port=int(body.get('port'))
    except (TypeError,ValueError): raise HTTPException(400,'Enter a valid email server port.')
    if not host or len(host)>253 or any(ch.isspace() for ch in host) or not (1<=port<=65535): raise HTTPException(400,'Enter a valid email server host and port.')
    if security not in ('starttls','ssl') or not valid_email(sender): raise HTTPException(400,'Choose STARTTLS or SSL and enter a valid sender email address.')
    if username and not password: raise HTTPException(400,'Enter the email server password, or leave the username blank for an unauthenticated relay.')
    cfg={'host':host,'port':port,'security':security,'username':username,'password':password,'from':sender}
    _smtp_connect(cfg)
    for key,val in [('smtp_host',host),('smtp_port',str(port)),('smtp_security',security),('smtp_username',username),('smtp_password',password),('smtp_from',sender)]:set_secret(key,val)
    return {'configured':True,'ready':True}

def send_reset(email):
    email=normalize_email(email)
    if not _limit('reset:'+email,maximum=4,window=3600): return {'message':'If password recovery is configured for that account, a reset email will be sent.'}
    owner=owner_record(); cfg=_smtp_config()
    if owner and owner['email']==email and cfg:
        raw=secrets.token_urlsafe(40); now=time.time()
        with db() as c:c.execute('INSERT INTO auth_reset_tokens(token_hash,owner_id,expires,created,consumed) VALUES(?,?,?,?,NULL)',(digest(raw),owner['id'],now+RESET_SECONDS,now))
        link=app_origin()+'/signin?reset='+raw
        msg=EmailMessage();msg['Subject']='Reset your Nexora password';msg['From']=cfg['from'];msg['To']=email
        msg.set_content('A password reset was requested for your local Nexora account. If you did not request this, ignore this message.\n\nThis one-time link expires in 60 minutes:\n'+link+'\n')
        try:
            if cfg['security']=='ssl': server=smtplib.SMTP_SSL(cfg['host'],cfg['port'],timeout=8,context=ssl.create_default_context())
            else:
                server=smtplib.SMTP(cfg['host'],cfg['port'],timeout=8);server.ehlo();server.starttls(context=ssl.create_default_context());server.ehlo()
            with server:
                if cfg['username']:server.login(cfg['username'],cfg['password'])
                server.send_message(msg)
        except Exception:
            with db() as c:c.execute('DELETE FROM auth_reset_tokens WHERE token_hash=?',(digest(raw),))
    return {'message':'If password recovery is configured for that account, a reset email will be sent.'}

def reset_password(token,password):
    validate_password(password)
    key=digest(token)
    with db() as c:
        row=c.execute('SELECT owner_id,expires,consumed FROM auth_reset_tokens WHERE token_hash=?',(key,)).fetchone()
        if not row or row['consumed'] is not None or row['expires']<time.time(): raise HTTPException(400,'This password-reset link is invalid or expired. Request a new one.')
        hashed=PH.hash(password);now=time.time()
        c.execute('UPDATE auth_owner SET password_hash=?,updated=? WHERE id=?',(hashed,now,row['owner_id']))
        c.execute('UPDATE auth_reset_tokens SET consumed=? WHERE token_hash=?',(now,key))
        c.execute('DELETE FROM auth_sessions')
        c.execute('DELETE FROM auth_reset_tokens WHERE owner_id=?',(row['owner_id'],))
    return new_session()

def csrf_matches(cookie,header): return bool(cookie and header and len(cookie)<=200 and hmac.compare_digest(cookie,header))
