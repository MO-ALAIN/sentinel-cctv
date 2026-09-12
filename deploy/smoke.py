"""CI-only check of the running container, authentication and installed AI models."""
import json
import os
from http.cookies import SimpleCookie
from urllib.request import Request, urlopen
from urllib.error import HTTPError

base = 'http://127.0.0.1:8000'
password = os.environ['SENTINEL_SMOKE_PASSWORD']
for path in ('/api/cameras', '/health'):
    try:
        urlopen(base + path, timeout=10)
    except HTTPError as error:
        assert error.code == 401, (path, error.code)
    else:
        raise AssertionError('Anonymous access allowed: ' + path)
body = json.dumps({'username':'admin', 'password':password}).encode()
with urlopen(Request(base + '/api/auth/login', data=body,
             headers={'Content-Type':'application/json'}), timeout=15) as response:
    cookies = SimpleCookie(); cookies.load(response.headers['Set-Cookie'])
    session = cookies['sentinel_session']
    assert session['secure'] and session['httponly']
# This test talks directly to the container over loopback HTTP, before TLS termination.
headers = {'Cookie': 'sentinel_session=' + session.value}
with urlopen(Request(base + '/api/system/health', headers=headers), timeout=15) as response:
    assert json.load(response)['ai']['ready'], 'Vehicle model unavailable'
with urlopen(Request(base + '/api/anpr/stats', headers=headers), timeout=15) as response:
    telemetry = json.load(response)
    assert telemetry['ready'], 'OCR model unavailable'
    assert telemetry['trained_plate_detector_ready'], 'Plate detector unavailable'
print('Container login, access controls, vehicle detector, plate detector and OCR ready')
