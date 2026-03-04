import json
import os
import sys
import time

import requests

# lê .env

def read_env(path='.env'):
    d={}
    with open(path) as f:
        for l in f:
            l=l.strip()
            if not l or l.startswith('#'): continue
            if '=' in l:
                k,v=l.split('=',1)
                d[k.strip()]=v.strip()
    return d

env=read_env('.env')
if not env:
    print('No .env found', file=sys.stderr); sys.exit(1)

payload={'vortal_user':env.get('VORTAL_USER'),'vortal_password':env.get('VORTAL_PASSWORD'),'headless':False}
if env.get('ACINGOV_USER') and env.get('ACINGOV_PASSWORD'):
    payload['acingov_user']=env.get('ACINGOV_USER')
    payload['acingov_password']=env.get('ACINGOV_PASSWORD')

API='http://127.0.0.1:5000/api'
print('Submitting job to', API + '/jobs')
try:
    r=requests.post(API + '/jobs', json=payload, timeout=30)
except Exception as e:
    print('Submission failed:', e)
    sys.exit(2)
print('Response', r.status_code)
print(r.text)
if r.status_code!=201:
    sys.exit(3)
job_uuid=r.json().get('job_uuid')
print('Job UUID:', job_uuid)
open('/tmp/last_job_uuid.txt','w').write(job_uuid)

# Poll until finished
for i in range(0, 1800):
    try:
        jr=requests.get(f'{API}/jobs/{job_uuid}', timeout=10).json()
    except Exception as e:
        print(i, 'status fetch error', e)
        time.sleep(2)
        continue
    status=jr.get('status')
    print(i, status)
    # show recent API logs
    try:
        logs=requests.get(f'{API}/jobs/{job_uuid}/logs?limit=10', timeout=5).json()
        if logs:
            for l in logs:
                print('API_LOG:', l.get('created_at'), l.get('level'), str(l.get('message'))[:200])
    except Exception:
        pass
    if status not in ('pending','running'):
        print('Final state:', json.dumps(jr, ensure_ascii=False))
        break
    time.sleep(2)

# print worker log tail
print('\n--- worker log tail (last 200 lines) ---')
try:
    with open('logs/celery_worker.log','r', encoding='utf-8', errors='replace') as f:
        for l in f.readlines()[-200:]: print(l.rstrip())
except Exception as e:
    print('Cannot read worker log:', e)

# find job log file candidates
candidates=[os.path.join(os.path.abspath('.'),'logs'), '/tmp/nord_logs', '/tmp']
print('\nChecking candidates for job log:')
found=False
for d in candidates:
    p=os.path.join(d, f'job_{job_uuid}.log')
    try:
        print('exists?', p, os.path.exists(p))
        if os.path.exists(p):
            found=True
            print('\n--- job log tail', p, '---')
            with open(p,'r',encoding='utf-8',errors='replace') as fh:
                for l in fh.readlines()[-400:]: print(l.rstrip())
            break
    except Exception as e:
        print('check failed', d, e)

if not found:
    print('\nNo job log file found in candidates')

print('\nDone')
