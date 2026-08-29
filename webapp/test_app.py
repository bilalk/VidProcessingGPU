import io, json, sys
sys.path.insert(0, r'C:\ReelFactoryWeb')
import app

c = app.app.test_client()

r = c.get('/'); print('GET /           ->', r.status_code, 'bytes', len(r.data))
r = c.get('/api/config'); print('GET /api/config ->', r.status_code, r.get_json())
r = c.get('/api/status'); print('GET /api/status ->', r.status_code, r.get_json())
r = c.get('/api/history'); print('GET /api/history->', r.status_code, r.get_json())

# upload two same-format samples
with open(r'C:\ProjectComfy\29Aug1.json', 'rb') as f1, open(r'C:\ProjectComfy\29Aug2.json', 'rb') as f2:
    r = c.post('/api/upload', data={'file1': (f1, '29Aug1.json'), 'file2': (f2, '29Aug2.json')},
               content_type='multipart/form-data')
print('\nPOST /api/upload ->', r.status_code)
d = r.get_json()
print('  reels=', d.get('reels'), 'format=', d.get('format'), 'issues=', len(d.get('issues', [])),
      'redundant=', len(d.get('redundant_topics', [])), 'next_id=', d.get('next_id'))
print('  sample redundant:', d.get('redundant_topics', [])[:4])

# start WITHOUT confirm -> should reject with 409 (redundant topics), no GPU launch
r = c.post('/api/start', json={'file_a': d['file_a'], 'file_b': d['file_b'], 'mode': 'flux'})
print('\nPOST /api/start (no confirm) ->', r.status_code)
print('  body=', r.get_json())
