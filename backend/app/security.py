"""Same-origin sessions and role checks. Unconfigured deployments are loopback-only."""
import hashlib
import hmac
import os
import secrets
import time
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

router = APIRouter(prefix='/api/auth', tags=['Access'])
SESSIONS = {}
FAILURES = {}
ROLE_LEVEL = {'viewer': 0, 'operator': 1, 'admin': 2}

def configured():
    return bool(os.getenv('CCTV_ADMIN_PASSWORD'))

def actor(request):
    return getattr(request.state, 'actor', {'name': 'local', 'role': 'admin'})

def require_role(request, role):
    if ROLE_LEVEL.get(actor(request)['role'], -1) < ROLE_LEVEL[role]:
        raise HTTPException(403, 'Insufficient role for this action')

async def access_middleware(request, call_next):
    if not request.url.path.startswith('/api/') and request.url.path != '/health':
        return await call_next(request)
    # Cookies are never accepted for cross-site mutation requests.
    origin = request.headers.get('origin')
    permitted = {str(request.base_url).rstrip('/'), 'http://localhost:5173', 'http://127.0.0.1:5173'}
    permitted.update(x.strip() for x in os.getenv('CORS_ORIGINS', '').split(',') if x.strip())
    if request.method not in ('GET','HEAD','OPTIONS') and origin and origin not in permitted:
        return JSONResponse({'detail':'Cross-origin action rejected'}, status_code=403)
    host = urlsplit(str(request.url)).hostname
    local = request.client and request.client.host in ('127.0.0.1','::1','testclient') and host in ('localhost','127.0.0.1','::1','testserver')
    if not configured():
        if not local:
            return JSONResponse({'detail':'Configure authentication before network access'}, status_code=403)
        request.state.actor = {'name':'local operator', 'role':'admin'}
    else:
        now = time.time()
        for token in [k for k,v in SESSIONS.items() if v['expires'] <= now]:
            SESSIONS.pop(token, None)
        session = SESSIONS.get(request.cookies.get('sentinel_session'))
        if session:
            request.state.actor = {k:session[k] for k in ('name','role')}
        elif request.url.path not in ('/api/auth/login','/api/auth/session') and request.method != 'OPTIONS':
            return JSONResponse({'detail':'Sign in required'}, status_code=401)
    if request.method not in ('GET','HEAD','OPTIONS') and not request.url.path.startswith('/api/auth/'):
        required = 'admin' if request.url.path.startswith(('/api/registry','/api/watchlist')) else 'operator'
        if ROLE_LEVEL.get(actor(request)['role'],-1) < ROLE_LEVEL[required]:
            return JSONResponse({'detail':'Insufficient role for this action'},status_code=403)
    if request.query_params.get('refresh') == 'true' and ROLE_LEVEL.get(actor(request)['role'],-1) < 2:
        return JSONResponse({'detail':'Administrator role required for catalogue import'},status_code=403)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

class Login(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=256)

@router.get('/session')
def session(request: Request):
    return {'authentication_configured':configured(), 'user':getattr(request.state,'actor',None),
            'mode':'AUTHENTICATED' if configured() else 'LOCAL_ONLY'}

@router.post('/login')
def login(body: Login, request: Request, response: Response):
    key = request.client.host
    now = time.time()
    attempts = [t for t in FAILURES.get(key,[]) if now-t < 300]
    if len(attempts) >= 10:
        raise HTTPException(429, 'Too many attempts; try again in five minutes')
    role = body.username.lower()
    expected = os.getenv(f'CCTV_{role.upper()}_PASSWORD', '') if role in ROLE_LEVEL else ''
    if not expected or not hmac.compare_digest(hashlib.sha256(body.password.encode()).digest(), hashlib.sha256(expected.encode()).digest()):
        FAILURES[key] = attempts + [now]
        raise HTTPException(401, 'Invalid credentials')
    FAILURES.pop(key,None)
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {'name':role,'role':role,'expires':now+8*3600}
    response.set_cookie('sentinel_session',token,httponly=True,samesite='strict',secure=os.getenv('SENTINEL_DEPLOYMENT', '').lower() == 'true' or request.url.scheme=='https',max_age=8*3600)
    return {'user':{'name':role,'role':role}}

@router.post('/logout')
def logout(request: Request,response: Response):
    SESSIONS.pop(request.cookies.get('sentinel_session'),None)
    response.delete_cookie('sentinel_session')
    return {'signed_out':True}
