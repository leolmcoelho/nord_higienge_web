import json
import os
import time

import requests

# lê .env simples (opcional)
env = {}
env_paths = ['.env', '/app/.env']
for env_path in env_paths:
    if os.path.exists(env_path):
        with open(env_path) as f:
            for l in f:
                l = l.strip()
                if not l or l.startswith('#'):
                    continue
                if '=' in l:
                    k, v = l.split('=', 1)
                    env[k.strip()] = v.strip()
        break

vortal_user = env.get('VORTAL_USER')
vortal_password = env.get('VORTAL_PASSWORD')
acingov_user = env.get('ACINGOV_USER')
acingov_password = env.get('ACINGOV_PASSWORD')

payload = {
    'vortal_user': vortal_user,
    'vortal_password': vortal_password,
    'headless': True
}
if acingov_user and acingov_password:
    payload['acingov_user'] = acingov_user
    payload['acingov_password'] = acingov_password

BASE = os.environ.get('BASE_URL', 'http://web:5000')
API = BASE + '/api'

print('Submitting job...')
r = requests.post(API + '/jobs', json=payload, timeout=30)
print('Status', r.status_code, r.text)
if r.status_code != 201:
    raise SystemExit('Job submission failed')
data = r.json()
job_uuid = data['job_uuid']
print('Job UUID', job_uuid)

for i in range(900):
    try:
        rr = requests.get(API + f'/jobs/{job_uuid}', timeout=10)
        rj = rr.json()
        s = rj.get('status')
    except Exception as e:
        print('Error fetching status', e)
        s = 'error'
    print(i, s)
    if s not in ('pending', 'running'):
        print('Final:', json.dumps(rj, indent=2))
        break
    time.sleep(2)

# print tail of log if exists
candidates = [os.path.join('/app', 'logs'), '/tmp/nord_logs']
for d in candidates:
    p = os.path.join(d, f'job_{job_uuid}.log')
    if os.path.exists(p):
        print('\nFound log at', p)
        with open(p) as f:
            for l in f.readlines()[-200:]:
                print(l.rstrip())
        break
else:
    print('\nNo log file found for job at candidates')
