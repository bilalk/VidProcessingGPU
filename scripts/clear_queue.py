import urllib.request, json
def post(url, data):
    req = urllib.request.Request(url, json.dumps(data).encode(), {'Content-Type': 'application/json'})
    try:
        return urllib.request.urlopen(req, timeout=30).read().decode()[:200]
    except Exception as e:
        return f'ERR {e}'
print('interrupt:', post('http://127.0.0.1:8188/interrupt', {}))
print('clear:', post('http://127.0.0.1:8188/queue', {'clear': True}))
