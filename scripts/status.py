#!/usr/bin/env python3
# status.py - live GPU/job status page on 127.0.0.1:8888 (fronted by Caddy :80).
# Also serves completed reels over HTTP (for host-PC pull) and accepts a
# "transferred" counter so the page can show how many reels are already on the host.
import http.server, json, subprocess, urllib.request, urllib.parse, socketserver, datetime, os, time

OUT   = '/root/reels_ltx29'
TOTAL = 24
FLUX_DIR = '/root/reels_r3'

HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>GPU Status</title>
<style>
body{font-family:monospace;background:#0b0f14;color:#c9d1d9;margin:18px}
h1{color:#58a6ff;font-size:20px}.sub{color:#8b949e;font-size:12px}
button{background:#238636;color:#fff;border:0;border-radius:5px;padding:10px 18px;font-size:15px;cursor:pointer;margin:8px 0}
button:hover{background:#2ea043}
.box{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px;margin:10px 0;white-space:pre-wrap;overflow-x:auto}
.s{color:#ffd33d;font-size:18px;font-weight:bold}
</style></head><body>
<h1>&#9650; GPU Server Status &mdash; LTX pipeline</h1>
<div class="box"><span class="s" id="sum">loading&hellip;</span></div>
 <div class="box" id="web">loading&hellip;</div>
<button onclick="poll()">&#8635; Refresh</button>
<div class="sub" id="upd"></div>
<div class="box" id="gpu">loading&hellip;</div>
<div class="box" id="queue">loading&hellip;</div>
<div class="box" id="log">loading&hellip;</div>
<script>
async function poll(){
  try{
    const r=await fetch('/api'); const d=await r.json();
    document.getElementById('sum').innerHTML=d.sum;
    document.getElementById('web').innerHTML=d.web_batch;
    document.getElementById('gpu').innerHTML=d.gpu;
    document.getElementById('queue').innerHTML=d.queue;
    document.getElementById('log').innerHTML=d.log;
    document.getElementById('upd').textContent='last update: '+d.time+' UTC';
  }catch(e){}
}
poll();
</script></body></html>"""

def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception:
        return ''

def count_done():
    try:
        return int(sh('ls %s/out_mobile/*/*.mp4 2>/dev/null | wc -l' % OUT).split()[-1])
    except Exception:
        return 0

def count_started():
    try:
        return int(sh("ls %s/clips_m/*.mp4 2>/dev/null | sed 's#.*/##' | cut -d_ -f1 | sort -u | wc -l" % OUT).split()[-1])
    except Exception:
        return 0

def count_errors():
    n = 0
    for log in ('%s/run.log' % OUT, '%s/run_all.log' % OUT):
        try:
            n += int(sh("grep -cE 'FAIL|ERROR' %s 2>/dev/null" % log).split()[-1] or '0')
        except Exception:
            pass
    return n

def summary():
    # current WEB batch summary (phase + progress + ETA/avg), not the stale per-batch counter
    try:
        with open('%s/web_batch.json' % FLUX_DIR) as f:
            b = json.load(f)
        names = ' + '.join(b.get('files', []))
        mode = b.get('mode', 'flux+ltx')
        start_id = b.get('start_id', '?')
    except Exception:
        return 'No web batch yet — start one via the Reel Factory site (104.211.18.21:5000)'

    flux = sh('cat %s/logs/web_flux.log 2>/dev/null' % FLUX_DIR)
    ltx = sh('cat %s/logs/web_ltx.log 2>/dev/null' % OUT)
    total = 24

    if 'LTX_ALL_DONE' in ltx:
        phase, done, per_reel = 'LTX COMPLETE', total, None
    elif ltx:
        starts = [l.split('START ')[-1].strip() for l in ltx.split('\n') if 'START ' in l]
        phase = 'LTX - channel %s' % (starts[-1] if starts else '?')
        done = ltx.count('mobile=')
        per_reel = 8.5 * 60
    elif 'FLUX_ALL_DONE' in flux:
        phase, done, per_reel = 'FLUX complete (LTX next)', total, None
    elif 'FLUX_G2_DONE' in flux or 'ASSEMBLE_' in flux:
        phase = 'FLUX - assembling videos'
        done = flux.count('dur=')
        per_reel = 47.0
    elif 'FLUX_G1_DONE' in flux:
        phase, done, per_reel = 'FLUX - stills (file 2/2)', 0, None
    elif 'OK ' in flux:
        phase, done, per_reel = 'FLUX - generating stills', 0, None
    elif 'TTS_DONE' in flux:
        phase, done, per_reel = 'FLUX - stills queued', 0, None
    elif flux:
        phase, done, per_reel = 'FLUX - TTS (voices)', 0, None
    else:
        phase, done, per_reel = 'preparing (TTS)', 0, None

    lines = ['BATCH: %s   (%d reels · ids %s+ · %s)' % (names, total, start_id, mode),
             'PHASE: %s' % phase,
             'done: %d/%d' % (done, total)]
    if per_reel:
        lines.append('avg: %.0f sec/reel' % per_reel)
    rem = total - done
    if per_reel and rem > 0:
        lines.append('ETA: ~%d min' % ((rem * per_reel) // 60))
    return '\n'.join(lines)

def gpu_status():
    return sh('rocm-smi 2>/dev/null | grep -E "^0 |VRAM%|GPU%|Temperature|Power"') or 'no GPU data'

def queue_status():
    try:
        q = json.loads(urllib.request.urlopen('http://127.0.0.1:8188/queue', timeout=6).read())
        return f"ComfyUI queue:  RUNNING={len(q.get('queue_running',[]))}  PENDING={len(q.get('queue_pending',[]))}"
    except Exception:
        return 'queue ERR'

def log_status():
    fl = sh('tail -8 %s/logs/web_flux.log 2>/dev/null' % FLUX_DIR)
    ll = sh('tail -6 %s/logs/web_ltx.log 2>/dev/null' % OUT)
    parts = []
    if fl:
        parts.append('— FLUX round —\n' + fl)
    if ll:
        parts.append('— LTX round —\n' + ll)
    return '\n\n'.join(parts) or 'no web pipeline log yet'

def web_batch_status():
    try:
        with open('%s/web_batch.json' % FLUX_DIR) as f:
            b = json.load(f)
        head = ('WEB BATCH: ' + ' + '.join(b.get('files', []))
                + '   (ids from %s, mode %s, started %s)' % (b.get('start_id'), b.get('mode'), b.get('started_at')))
    except Exception:
        head = 'WEB BATCH: (none recorded yet)'
    parts = [head]
    fl = sh('tail -5 %s/logs/web_flux.log 2>/dev/null' % FLUX_DIR)
    if fl:
        parts.append('  FLUX round: ' + fl.replace('\n', ' | '))
    ll = sh('tail -3 %s/logs/web_ltx.log 2>/dev/null' % FLUX_DIR.replace('reels_r3', 'reels_ltx29'))
    if ll:
        parts.append('  LTX round: ' + ll.replace('\n', ' | '))
    return '\n'.join(parts)

def list_files():
    items = []
    for kind, d in (('mobile', 'out_mobile'), ('desktop', 'out_desktop')):
        base = os.path.join(OUT, d)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if fn.endswith('.mp4'):
                    full = os.path.join(root, fn)
                    if time.time() - os.path.getmtime(full) < 60:
                        continue
                    rel = os.path.relpath(full, base)
                    items.append({'kind': kind, 'rel': rel.replace(os.sep, '/'), 'size': os.path.getsize(full)})
    return items

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        if p.path.startswith('/file/'):
            self._serve_file(p.path[len('/file/'):])
        elif p.path == '/list':
            self._send(json.dumps(list_files()).encode(), 'application/json')
        elif p.path == '/settransferred':
            self._set_transferred(urllib.parse.parse_qs(p.query))
        elif p.path == '/api':
            self._send(json.dumps({'time': sh('date -u +%H:%M:%S'), 'sum': summary(),
                                   'web_batch': web_batch_status(),
                                   'gpu': gpu_status(), 'queue': queue_status(), 'log': log_status()}).encode(),
                       'application/json')
        elif p.path in ('/', '/index.html'):
            self._send(HTML.encode(), 'text/html')
        else:
            self.send_response(404); self.end_headers()

    def _serve_file(self, rel):
        try:
            kind, rest = rel.split('/', 1)
        except ValueError:
            self.send_response(404); self.end_headers(); return
        d = 'out_mobile' if kind == 'mobile' else 'out_desktop'
        base = os.path.realpath(os.path.join(OUT, d))
        path = os.path.realpath(os.path.join(OUT, d, rest))
        if not path.startswith(base + os.sep) or not os.path.isfile(path):
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Content-Length', str(os.path.getsize(path)))
        self.end_headers()
        with open(path, 'rb') as f:
            self.wfile.write(f.read())

    def _set_transferred(self, q):
        try:
            n = int(q.get('n', ['0'])[0])
            with open('%s/transferred.txt' % OUT, 'w') as f:
                f.write(str(n))
            self._send(b'ok', 'text/plain')
        except Exception as e:
            self._send(('ERR ' + str(e)).encode(), 'text/plain')

    def _send(self, body, ctype):
        self.send_response(200); self.send_header('Content-Type', ctype); self.send_header('Cache-Control', 'no-store'); self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == '__main__':
    S(('127.0.0.1', 8888), H).serve_forever()

