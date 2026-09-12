"""Validate shared-hosting configuration before importing the AI application."""
import os
import sys
from pathlib import Path


def validate_environment(env):
    if env.get('SENTINEL_DEPLOYMENT', '').lower() != 'true':
        raise ValueError('Set SENTINEL_DEPLOYMENT=true for the shared-server launcher')
    password = env.get('CCTV_ADMIN_PASSWORD', '')
    if len(password) < 16 or password.lower() in ('change-this-password', 'your-admin-password'):
        raise ValueError('Set a unique CCTV_ADMIN_PASSWORD with at least 16 characters')
    used = {password}
    for role in ('OPERATOR', 'VIEWER'):
        value = env.get(f'CCTV_{role}_PASSWORD', '')
        if value and (len(value) < 16 or value in used):
            raise ValueError(f'Use a distinct password of at least 16 characters for {role}')
        if value: used.add(value)
    hosts = [h.strip() for h in env.get('SENTINEL_ALLOWED_HOSTS', '').split(',') if h.strip()]
    if not hosts or '*' in hosts or any('://' in h or '/' in h for h in hosts):
        raise ValueError('Set explicit SENTINEL_ALLOWED_HOSTS without schemes or paths')
    forwarded = env.get('FORWARDED_ALLOW_IPS', '127.0.0.1')
    if not forwarded or '*' in forwarded:
        raise ValueError('Trust only the actual reverse proxy address')


def prepare_environment(env):
    # Render terminates TLS; incoming proxy headers are not blindly trusted.
    if env.get('RENDER') == 'true':
        hostname = env.get('RENDER_EXTERNAL_HOSTNAME', '')
        if not hostname or any(c in hostname for c in '/:,* '):
            raise ValueError('Render must supply a valid external hostname')
        env.setdefault('SENTINEL_ALLOWED_HOSTS', hostname + ',localhost,127.0.0.1')
        origins = [x for x in env.get('CORS_ORIGINS', '').split(',') if x]
        origins.append('https://' + hostname)
        env['CORS_ORIGINS'] = ','.join(dict.fromkeys(origins))
    validate_environment(env)


def main():
    prepare_environment(os.environ)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
    import uvicorn
    # One process owns camera workers, SQLite and in-memory login sessions.
    uvicorn.run('app.main:app', host='0.0.0.0', port=int(os.getenv('PORT', '8000')), workers=1,
                proxy_headers=os.getenv('RENDER') != 'true', forwarded_allow_ips=os.getenv('FORWARDED_ALLOW_IPS','127.0.0.1'))


if __name__ == '__main__':
    try: main()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
