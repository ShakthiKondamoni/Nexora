import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from backend.services import auth_service as auth
from backend.database.connection import q

@pytest.fixture
def client():
    from backend.main import app
    with TestClient(app) as c: yield c

@pytest.fixture(autouse=True)
def clear_auth_rows():
    for table in ('auth_sessions','auth_oauth_state','auth_reset_tokens','auth_rate_limits','auth_owner'):
        q('DELETE FROM '+table)

def csrf_headers(client):
    r=client.get('/api/auth/status')
    assert r.status_code==200
    return {'Origin':'http://127.0.0.1:8501','X-CSRF-Token':client.cookies.get('studio_csrf')}

def test_local_auth_is_optional_and_providers_start_unconfigured(client,monkeypatch):
    monkeypatch.setattr(auth,'get_secret',lambda name: None)
    result=client.get('/api/auth/status').json()
    assert result['owner_exists'] is False and result['auth_required'] is False
    assert result['google']['ready'] is False
    assert result['email']['ready'] is False
    assert result['callbacks']['google']=='http://127.0.0.1:8501/api/auth/google/callback'

def test_single_owner_registration_session_cookie_and_logout(client):
    headers=csrf_headers(client)
    response=client.post('/api/auth/register',headers=headers,json={'email':'owner@example.test','password':'a long secure passphrase'})
    assert response.status_code==200
    assert 'httponly' in response.headers.get('set-cookie','').lower()
    assert 'samesite=strict' in response.headers.get('set-cookie','').lower()
    assert client.get('/api/settings').status_code==200
    headers=csrf_headers(client)
    second=client.post('/api/auth/register',headers=headers,json={'email':'other@example.test','password':'another secure passphrase'})
    assert second.status_code==409
    response=client.post('/api/auth/logout',headers=headers,json={})
    assert response.status_code==200
    assert client.get('/api/settings').status_code==401

def test_unsafe_auth_request_requires_csrf_and_same_origin(client):
    client.get('/api/auth/status')
    assert client.post('/api/auth/register',json={'email':'owner@example.test','password':'a long secure passphrase'}).status_code==403
    headers=csrf_headers(client);headers['Origin']='https://attacker.example'
    assert client.post('/api/auth/register',headers=headers,json={'email':'owner@example.test','password':'a long secure passphrase'}).status_code==403

def test_google_state_is_single_use_and_browser_bound(monkeypatch):
    monkeypatch.setattr(auth,'get_secret',lambda name: 'client.apps.googleusercontent.com' if name=='google_client_id' else 'secret')
    flow=auth.create_google_flow('login')
    with pytest.raises(HTTPException): auth.consume_oauth_state('google',flow['state'],'wrong-browser')
    with pytest.raises(HTTPException): auth.consume_oauth_state('google',flow['state'],flow['browser'])

def test_google_denial_callback_validates_state_before_reporting_denial(client,monkeypatch):
    monkeypatch.setattr(auth,'get_secret',lambda name: 'client.apps.googleusercontent.com' if name=='google_client_id' else 'secret')
    flow=auth.create_google_flow('login')
    client.cookies.set(auth.GOOGLE_FLOW_COOKIE,flow['browser'],path='/')
    response=client.get('/api/auth/google/callback',params={'error':'access_denied','state':flow['state']},follow_redirects=False)
    assert response.status_code==303 and response.headers['location']=='/signin?error=google_denied'
    response=client.get('/api/auth/google/callback',params={'error':'access_denied','state':'not-a-real-state'},follow_redirects=False)
    assert response.headers['location']=='/signin?error=google_state'

def test_configured_google_secret_is_never_returned(client,monkeypatch):
    store={}
    monkeypatch.setattr(auth,'_keyring_ready',lambda:True)
    monkeypatch.setattr(auth,'get_secret',lambda name:store.get(name))
    monkeypatch.setattr(auth,'set_secret',lambda name,value:store.__setitem__(name,value))
    headers=csrf_headers(client)
    secret='test-only-never-return-this'
    result=client.post('/api/auth/setup/google',headers=headers,json={'client_id':'client.apps.googleusercontent.com','client_secret':secret})
    assert result.status_code==200
    assert secret not in result.text
    assert secret not in client.get('/api/auth/status').text

def test_password_reset_rejects_invalid_or_expired_token():
    with pytest.raises(HTTPException): auth.reset_password('not-a-reset-token','a long secure passphrase')
