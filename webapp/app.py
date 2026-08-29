# app.py — Reel Factory web service (Flask).
import os, json, time, threading, traceback
from flask import Flask, request, jsonify, render_template
import pipeline as P
import gpu as G

BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE, 'state')
UPLOADS = os.path.join(BASE, 'uploads')
CONFIG_PATH = os.path.join(STATE, 'config.json')
JOB_PATH = os.path.join(STATE, 'job.json')
HISTORY_PATH = os.path.join(STATE, 'history.json')

# server-side constants (matching the deployed 29aug pipeline)
FLUX_DIR = '/root/reels_r3'
LTX_DIR  = '/root/reels_ltx29'
MAN_ALL  = '/root/reels_r3/manifest_29aug_all.json'   # filename ltx_29.py reads
FLUX_OUT = '/root/reels_r3/out_29aug'
LTX_OUT_M = '/root/reels_ltx29/out_mobile'
LTX_OUT_D = '/root/reels_ltx29/out_desktop'

# local (host PC) output dirs — same structure as today
LOCAL_FLUX  = r'C:\ProjectComfy\reelsGPU2\flux_29aug'
LOCAL_LTX_M = r'C:\ProjectComfy\reelsGPU2\ltx_29aug_mobile'
LOCAL_LTX_D = r'C:\ProjectComfy\reelsGPU2\ltx_29aug_desktop'

CHANNELS = P.CHANNELS

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

LOCK = threading.Lock()
JOB = None


def load_config():
    d = {'gpu_host': '129.212.190.223', 'gpu_user': 'root',
         'gpu_key': r'C:\Users\tester\.ssh\id_newgpu',
         'burn_subtitles': True, 'mode': 'flux+ltx'}
    try:
        if os.path.exists(CONFIG_PATH):
            d.update(json.load(open(CONFIG_PATH, encoding='utf-8')))
    except Exception:
        pass
    return d


def save_config(d):
    os.makedirs(STATE, exist_ok=True)
    json.dump(d, open(CONFIG_PATH, 'w', encoding='utf-8'), indent=2)


TOPIC_DB_PATH = os.path.join(STATE, 'used_topics.json')


def load_used_topics():
    try:
        return set(json.load(open(TOPIC_DB_PATH, encoding='utf-8')))
    except Exception:
        return set()


def save_used_topics(used):
    os.makedirs(STATE, exist_ok=True)
    json.dump(sorted(used), open(TOPIC_DB_PATH, 'w', encoding='utf-8'), indent=2)


def _save_job(job):
    os.makedirs(STATE, exist_ok=True)
    json.dump(job, open(JOB_PATH, 'w', encoding='utf-8'), indent=2, default=str)


def _save_history(entry):
    try:
        hist = json.load(open(HISTORY_PATH, encoding='utf-8'))
    except Exception:
        hist = []
    hist.insert(0, entry)
    try:
        json.dump(hist, open(HISTORY_PATH, 'w', encoding='utf-8'), indent=2, default=str)
    except Exception:
        pass


def _update(job, **kw):
    with LOCK:
        job.update(kw)
        job['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        _save_job(job)


def _log(job, msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with LOCK:
        job.setdefault('log', []).append(line)
        _save_job(job)
    print(line, flush=True)


def _flux_script():
    return """#!/bin/bash
cd /root/reels_r3
PY=/root/ComfyUI/venv/bin/python
$PY tts_29.py manifest_web_g1.json > logs/web_tts_g1.log 2>&1 &
$PY tts_29.py manifest_web_g2.json > logs/web_tts_g2.log 2>&1 &
wait
echo TTS_DONE
$PY flux_gen_opt.py manifest_web_g1.json && echo FLUX_G1_DONE || echo FLUX_G1_FAIL
$PY flux_gen_opt.py manifest_web_g2.json && echo FLUX_G2_DONE || echo FLUX_G2_FAIL
$PY assemble_29.py manifest_web_g1.json && echo ASSEMBLE_G1_DONE || echo ASSEMBLE_G1_FAIL
$PY assemble_29.py manifest_web_g2.json && echo ASSEMBLE_G2_DONE || echo ASSEMBLE_G2_FAIL
echo FLUX_ALL_DONE
"""


def _ltx_script():
    return """#!/bin/bash
cd /root/reels_ltx29
PY=/root/ComfyUI/venv/bin/python
for ch in arabic-to-english chinese-to-english english-to-arabic english-to-chinese english-to-spanish spanish-to-english; do
  echo "START $ch"
  $PY ltx_29.py "$ch"
  echo "DONE $ch"
done
echo LTX_ALL_DONE
"""


def _poll_until(job, g, logfile, marker, stage, max_seconds=8 * 3600):
    t0 = time.time()
    while True:
        if job.get('_abort'):
            return False
        _, tailout, _ = g.run(f"tail -n 6 {logfile} 2>/dev/null", timeout=25)
        with LOCK:
            job['log_tail'] = tailout
            _save_job(job)
        if marker in tailout:
            return True
        if time.time() - t0 > max_seconds:
            _log(job, f"TIMEOUT waiting for {marker} after {max_seconds}s")
            return False
        time.sleep(25)


def _pull(job, g, remote_dir, local_dir, kind):
    files = g.list_remote(remote_dir, '.mp4')
    _log(job, f"pulling {len(files)} {kind} files ...")
    for i, rp in enumerate(files, 1):
        if job.get('_abort'):
            return
        rel = os.path.relpath(rp, remote_dir)
        local = os.path.join(local_dir, rel)
        if os.path.exists(local) and os.path.getsize(local) > 0:
            continue
        try:
            g.get(rp, local)
            job['reels_downloaded'] = job.get('reels_downloaded', 0) + 1
        except Exception as e:
            _log(job, f"  pull FAIL {rp}: {e}")
            continue
        if i % 5 == 0 or i == len(files):
            _update(job, reels_downloaded=job['reels_downloaded'],
                    current_stage=f'pulling {kind} ({i}/{len(files)})')
    _log(job, f"finished pulling {kind}")


def _poll_ltx(job, g, ltx_log):
    t0 = time.time()
    prev_done = -1  # force an initial incremental pull to catch up
    avg = 8.5 * 60
    total = job.get('reels_total', 24)
    while True:
        if job.get('_abort'):
            return
        _, tailout, _ = g.run(f"tail -n 6 {ltx_log} 2>/dev/null", timeout=25)
        _, full, _ = g.run(f"grep -c 'mobile=' {ltx_log} 2>/dev/null", timeout=25)
        try:
            done = int(full.strip().split()[-1])
        except Exception:
            done = job.get('reels_done', 0)
        eta_min = round((total - done) * avg / 60) if done < total else 0
        _update(job, reels_done=done, avg_sec=avg, eta_min=eta_min, log_tail=tailout)
        for line in tailout.splitlines():
            if 'START ' in line:
                ch = line.split('START ')[-1].strip()
                _update(job, current_channel=ch)
                _log(job, 'LTX channel: ' + ch)
        if done > prev_done:
            # incrementally download newly-completed reels (don't wait for the whole round)
            _pull(job, g, LTX_OUT_M, LOCAL_LTX_M, 'ltx_mobile')
            _pull(job, g, LTX_OUT_D, LOCAL_LTX_D, 'ltx_desktop')
            prev_done = done
        if 'LTX_ALL_DONE' in tailout:
            _pull(job, g, LTX_OUT_M, LOCAL_LTX_M, 'ltx_mobile')
            _pull(job, g, LTX_OUT_D, LOCAL_LTX_D, 'ltx_desktop')
            return
        if time.time() - t0 > 10 * 3600:
            _log(job, 'TIMEOUT waiting for LTX_ALL_DONE')
            return
        time.sleep(20)


def _finish(job, g):
    """End the run: mark done normally, or leave it 'paused' if the user aborted."""
    if job.get('_abort'):
        _log(job, "paused by user — server pipeline left running (Resume or End)")
        g.close()
        return
    g.close()
    _log(job, "DONE — results copied to host")
    _update(job, status='done', current_stage='complete')


def run_job(job, start_id, manifest_a, manifest_b):
    global JOB
    cfg = job['config']
    mode = cfg['mode']
    g = None
    try:
        _log(job, f"connecting to {cfg['gpu_host']} ...")
        g = G.GPU(cfg['gpu_host'], cfg['gpu_key'], cfg['gpu_user']).connect()

        _update(job, status='waiting_idle', current_stage='wait for server idle')
        _log(job, "waiting for server to be idle ...")
        waited = 0
        while g.pipeline_running():
            if job.get('_abort'):
                _log(job, "aborted while waiting for idle")
                _update(job, status='aborted', current_stage='aborted')
                g.close()
                return
            time.sleep(20)
            waited += 20
            if waited > 45 * 60:
                _log(job, "server busy >45min — aborting to avoid collision")
                _update(job, status='error')
                g.close()
                return
        _log(job, "server idle — proceeding")

        _update(job, status='uploading', current_stage='push manifests')
        g.put(manifest_a, f"{FLUX_DIR}/manifest_web_g1.json")
        g.put(manifest_b, f"{FLUX_DIR}/manifest_web_g2.json")
        g.put(job['merged_path'], MAN_ALL)
        # marker so the GPU status page (129.212.190.223) shows this batch + its JSON names
        g.put_text(f"{FLUX_DIR}/web_batch.json",
                   json.dumps({'files': job['files'], 'start_id': start_id,
                               'mode': mode, 'started_at': time.strftime('%Y-%m-%d %H:%M:%S')}))

        _update(job, status='flux_running', current_stage='FLUX round (TTS -> stills -> assemble)')
        _log(job, "launching FLUX round ...")
        g.put_text(f"{FLUX_DIR}/web_flux.sh", _flux_script())
        g.run(f"chmod +x {FLUX_DIR}/web_flux.sh", timeout=25)
        g.launch_detached(f"cd {FLUX_DIR} && bash web_flux.sh",
                          f"{FLUX_DIR}/logs/web_flux.log")
        _poll_until(job, g, f"{FLUX_DIR}/logs/web_flux.log", 'FLUX_ALL_DONE', 'flux_running')

        _update(job, current_stage='pulling FLUX videos')
        _pull(job, g, FLUX_OUT, LOCAL_FLUX, 'flux')

        if mode == 'flux+ltx':
            if job.get('_abort'):
                g.close()
                return
            _update(job, status='ltx_running', current_stage='LTX round (per channel)')
            _log(job, "launching LTX round ...")
            g.put_text(f"{LTX_DIR}/web_ltx.sh", _ltx_script())
            g.run(f"chmod +x {LTX_DIR}/web_ltx.sh", timeout=25)
            g.launch_detached(f"cd {LTX_DIR} && bash web_ltx.sh",
                              f"{LTX_DIR}/logs/web_ltx.log")
            _poll_ltx(job, g, f"{LTX_DIR}/logs/web_ltx.log")
            _update(job, current_stage='pulling LTX videos')
            _pull(job, g, LTX_OUT_M, LOCAL_LTX_M, 'ltx_mobile')
            _pull(job, g, LTX_OUT_D, LOCAL_LTX_D, 'ltx_desktop')

        _finish(job, g)
    except Exception as e:
        _log(job, f"ERROR: {e}")
        _log(job, traceback.format_exc())
        if g is not None:
            try:
                for lf in (f"{FLUX_DIR}/logs/web_flux.log", f"{LTX_DIR}/logs/web_ltx.log"):
                    if g.exists(lf):
                        _, t, _ = g.run(f"tail -n 25 {lf} 2>/dev/null", timeout=25)
                        if t.strip():
                            _log(job, f"--- server log: {lf} ---")
                            for line in t.splitlines():
                                _log(job, line)
            except Exception:
                pass
        _update(job, status='error', current_stage=f'error: {e}')
    finally:
        _save_history({'id': job['id'], 'files': job['files'], 'mode': mode,
                       'status': job['status'], 'downloaded': job.get('reels_downloaded'),
                       'finished_at': time.strftime('%Y-%m-%d %H:%M:%S')})


def resume_job(job):
    """Re-attach to a job whose pipeline is already running on the server (after an
    app/service restart). Polls the existing logs + pulls results; idempotent."""
    global JOB
    cfg = job['config']
    mode = cfg['mode']
    g = None
    try:
        _log(job, f"resuming job {job.get('id')} (was {job.get('status')})")
        g = G.GPU(cfg['gpu_host'], cfg['gpu_key'], cfg['gpu_user']).connect()

        _update(job, status='flux_running', current_stage='FLUX round (already running)')
        _poll_until(job, g, f"{FLUX_DIR}/logs/web_flux.log", 'FLUX_ALL_DONE', 'flux_running')
        _update(job, current_stage='pulling FLUX videos')
        _pull(job, g, FLUX_OUT, LOCAL_FLUX, 'flux')

        if mode == 'flux+ltx':
            if job.get('_abort'):
                g.close()
                return
            _update(job, status='ltx_running', current_stage='LTX round (per channel)')
            ltx_log = f"{LTX_DIR}/logs/web_ltx.log"
            _, ltail, _ = g.run(f"tail -n 3 {ltx_log} 2>/dev/null", timeout=25)
            if 'LTX_ALL_DONE' not in ltail and not g.pipeline_running():
                _log(job, "launching LTX round (was never started) ...")
                g.put_text(f"{LTX_DIR}/web_ltx.sh", _ltx_script())
                g.run(f"chmod +x {LTX_DIR}/web_ltx.sh", timeout=25)
                g.launch_detached(f"cd {LTX_DIR} && bash web_ltx.sh", ltx_log)
            _poll_ltx(job, g, ltx_log)
            _update(job, current_stage='pulling LTX videos')
            _pull(job, g, LTX_OUT_M, LOCAL_LTX_M, 'ltx_mobile')
            _pull(job, g, LTX_OUT_D, LOCAL_LTX_D, 'ltx_desktop')

        _finish(job, g)
    except Exception as e:
        _log(job, f"RESUME ERROR: {e}")
        _log(job, traceback.format_exc())
        _update(job, status='error', current_stage=f'error: {e}')
    finally:
        _save_history({'id': job['id'], 'files': job['files'], 'mode': mode,
                       'status': job['status'], 'downloaded': job.get('reels_downloaded'),
                       'finished_at': time.strftime('%Y-%m-%d %H:%M:%S')})


def auto_resume():
    """On startup, re-attach to any job that was mid-run when the app last died."""
    try:
        job = json.load(open(JOB_PATH, encoding='utf-8'))
    except Exception:
        return
    if job.get('status') in ('flux_running', 'ltx_running'):
        job.setdefault('_abort', False)
        global JOB
        JOB = job
        threading.Thread(target=resume_job, args=(job,), daemon=True).start()


# ================= routes =================
def _orig_name(saved):
    base = os.path.basename(saved)
    for sep in ('_a_', '_b_'):
        if sep in base:
            return base.split(sep, 1)[1]
    return base


def _analyze(reels):
    fmt = P.detect_format(reels)
    issues = P.validate(reels)
    redundant = P.check_dedup(reels, load_used_topics())
    return fmt, issues, redundant


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        d = request.get_json(force=True)
        save_config(d)
        return jsonify({'ok': True})
    return jsonify(load_config())


@app.route('/api/history')
def history():
    try:
        return jsonify(json.load(open(HISTORY_PATH, encoding='utf-8')))
    except Exception:
        return jsonify([])


@app.route('/api/upload', methods=['POST'])
def upload():
    f1 = request.files.get('file1')
    f2 = request.files.get('file2')
    if not f1 or not f2:
        return jsonify({'error': 'need file1 and file2'}), 400
    os.makedirs(UPLOADS, exist_ok=True)
    ts = time.strftime('%Y%m%d-%H%M%S')
    p1 = os.path.join(UPLOADS, f'{ts}_a_{f1.filename}')
    p2 = os.path.join(UPLOADS, f'{ts}_b_{f2.filename}')
    f1.save(p1)
    f2.save(p2)
    try:
        reels = P.load_json(p1)['reels'] + P.load_json(p2)['reels']
    except Exception as e:
        return jsonify({'error': f'bad JSON: {e}'}), 400
    fmt, issues, redundant = _analyze(reels)
    next_id = P.find_next_start_id()
    return jsonify({
        'file_a': os.path.basename(p1), 'file_b': os.path.basename(p2),
        'reels': len(reels), 'format': fmt, 'issues': issues,
        'redundant_topics': redundant,
        'next_id': next_id,
    })


@app.route('/api/start', methods=['POST'])
def start():
    global JOB
    body = request.get_json(force=True)
    with LOCK:
        if JOB and JOB.get('status') in ('queued', 'waiting_idle', 'uploading',
                                         'flux_running', 'ltx_running', 'paused'):
            return jsonify({'error': 'a job is already running'}), 409
    pa = os.path.join(UPLOADS, os.path.basename(body['file_a']))
    pb = os.path.join(UPLOADS, os.path.basename(body['file_b']))
    try:
        reels_a = P.load_json(pa)['reels']
        reels_b = P.load_json(pb)['reels']
    except Exception as e:
        return jsonify({'error': f'cannot read uploads: {e}'}), 400

    all_reels = reels_a + reels_b
    fmt, issues, redundant = _analyze(all_reels)
    if issues:
        return jsonify({'error': 'validation failed', 'issues': issues[:20]}), 400
    if redundant and not body.get('confirm_redundant'):
        return jsonify({'error': 'redundant topics exist', 'redundant_topics': redundant}), 409

    start_id = P.find_next_start_id()
    na = P.normalize(reels_a, fmt, start_id)
    nb = P.normalize(reels_b, fmt, start_id + len(na))
    merged = {'reels': na + nb}

    job_id = time.strftime('%Y%m%d-%H%M%S')
    ma = os.path.join(UPLOADS, f'manifest_{job_id}_g1.json')
    mb = os.path.join(UPLOADS, f'manifest_{job_id}_g2.json')
    mall = os.path.join(UPLOADS, f'manifest_{job_id}_all.json')
    for path, data in ((ma, na), (mb, nb), (mall, merged['reels'])):
        json.dump({'reels': data}, open(path, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)

    # record the new topics as "used" so future batches dedup against them
    used = load_used_topics()
    used.update(t for t in (r.get('topic') for r in all_reels) if t)
    save_used_topics(used)

    cfg = {
        'gpu_host': body.get('gpu_host') or load_config()['gpu_host'],
        'gpu_user': body.get('gpu_user') or 'root',
        'gpu_key': body.get('gpu_key') or load_config()['gpu_key'],
        'burn_subtitles': bool(body.get('burn_subtitles', True)),
        'mode': body.get('mode', 'flux+ltx'),
    }
    save_config(cfg)

    JOB = {
        'id': job_id,
        'files': [_orig_name(pa), _orig_name(pb)],
        'config': cfg,
        'status': 'queued', 'detected_format': fmt, 'start_id': start_id,
        'reels_total': len(merged['reels']), 'reels_done': 0, 'reels_downloaded': 0,
        'current_channel': None, 'current_stage': 'queued',
        'log': [], 'log_tail': '', 'merged_path': mall, '_abort': False,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    _save_job(JOB)
    _log(JOB, f"job {job_id} queued: {len(merged['reels'])} reels, format={fmt}, mode={cfg['mode']}")

    threading.Thread(target=run_job, args=(JOB, start_id, ma, mb), daemon=True).start()
    return jsonify({'job_id': job_id, 'start_id': start_id, 'format': fmt,
                    'reels': len(merged['reels'])})


@app.route('/api/status')
def status():
    global JOB
    d = JOB or {'status': 'idle'}
    return jsonify({'status': d.get('status'), 'reels_total': d.get('reels_total'),
                    'reels_done': d.get('reels_done'), 'reels_downloaded': d.get('reels_downloaded'),
                    'current_channel': d.get('current_channel'), 'current_stage': d.get('current_stage'),
                    'files': d.get('files'), 'detected_format': d.get('detected_format'),
                    'start_id': d.get('start_id'), 'updated_at': d.get('updated_at'),
                    'avg_sec': d.get('avg_sec'), 'eta_min': d.get('eta_min'),
                    'log': (d.get('log') or [])[-50:], 'log_tail': d.get('log_tail', '')})


@app.route('/api/abort', methods=['POST'])
def abort():
    global JOB
    if JOB:
        with LOCK:
            JOB['_abort'] = True
            JOB['status'] = 'paused'
            _save_job(JOB)
    return jsonify({'ok': True})


@app.route('/api/resume', methods=['POST'])
def resume():
    global JOB
    if JOB and JOB.get('status') == 'paused':
        with LOCK:
            JOB['_abort'] = False
            _save_job(JOB)
        threading.Thread(target=resume_job, args=(JOB,), daemon=True).start()
    return jsonify({'ok': True})


@app.route('/api/end', methods=['POST'])
def end():
    global JOB
    if JOB:
        job = JOB
        try:
            g = G.GPU(job['config']['gpu_host'], job['config']['gpu_key'],
                      job['config']['gpu_user']).connect()
            g.kill_pipeline()
            g.close()
            _log(job, "server pipeline terminated gracefully")
        except Exception as e:
            _log(job, f"kill pipeline error: {e}")
        with LOCK:
            job['_abort'] = True
            job['status'] = 'aborted'
            job['current_stage'] = 'aborted'
            _save_job(job)
        _save_history({'id': job['id'], 'files': job['files'],
                       'mode': job['config'].get('mode'),
                       'status': 'aborted',
                       'downloaded': job.get('reels_downloaded'),
                       'finished_at': time.strftime('%Y-%m-%d %H:%M:%S')})
        JOB = None
    return jsonify({'ok': True})


if __name__ == '__main__':
    from waitress import serve
    auto_resume()
    print('Reel Factory web service on http://0.0.0.0:5000')
    serve(app, host='0.0.0.0', port=5000, threads=8)


