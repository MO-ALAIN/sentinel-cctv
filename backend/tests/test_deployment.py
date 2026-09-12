"""Public hosting must fail closed and support TLS termination without insecure cookies."""
import importlib.util
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.security import router, access_middleware, SESSIONS, FAILURES

spec = importlib.util.spec_from_file_location('hosting_launcher', Path(__file__).resolve().parents[2] / 'deploy/serve.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def environment():
    return {'SENTINEL_DEPLOYMENT':'true', 'CCTV_ADMIN_PASSWORD':'test-password-with-entropy',
            'RENDER':'true', 'RENDER_EXTERNAL_HOSTNAME':'sentinel-test.onrender.com'}


@pytest.mark.parametrize('key,value', [('CCTV_ADMIN_PASSWORD','short'), ('SENTINEL_ALLOWED_HOSTS','*'),
    ('FORWARDED_ALLOW_IPS','*'), ('RENDER_EXTERNAL_HOSTNAME','https://bad.example'),
    ('CCTV_VIEWER_PASSWORD','test-password-with-entropy')])
def test_invalid_public_configuration_fails_closed(key, value):
    env = environment(); env[key] = value
    with pytest.raises(ValueError): launcher.prepare_environment(env)


def test_render_login_works_behind_tls_proxy_and_sets_secure_cookie(monkeypatch):
    env = environment(); launcher.prepare_environment(env)
    for key, value in env.items(): monkeypatch.setenv(key, value)
    SESSIONS.clear(); FAILURES.clear()
    app = FastAPI(); app.middleware('http')(access_middleware); app.include_router(router)
    with TestClient(app, base_url='http://sentinel-test.onrender.com') as client:
        denied = client.post('/api/auth/login', headers={'origin':'https://evil.example'},
                             json={'username':'admin','password':env['CCTV_ADMIN_PASSWORD']})
        assert denied.status_code == 403
        response = client.post('/api/auth/login', headers={'origin':'https://sentinel-test.onrender.com'},
                               json={'username':'admin','password':env['CCTV_ADMIN_PASSWORD']})
        assert response.status_code == 200
        assert 'Secure' in response.headers['set-cookie']
        assert 'HttpOnly' in response.headers['set-cookie']
        assert 'SameSite=strict' in response.headers['set-cookie']
    SESSIONS.clear(); FAILURES.clear()


def test_legacy_health_alias_requires_login(monkeypatch):
    monkeypatch.setenv('CCTV_ADMIN_PASSWORD', 'test-password-with-entropy')
    app = FastAPI(); app.middleware('http')(access_middleware)
    @app.get('/health')
    def details(): return {'private': 'operational details'}
    @app.get('/healthz')
    def live(): return {'status': 'ok'}
    with TestClient(app) as client:
        assert client.get('/health').status_code == 401
        assert client.get('/healthz').json() == {'status':'ok'}
