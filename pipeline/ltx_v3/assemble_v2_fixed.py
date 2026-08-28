#!/usr/bin/env python
# assemble_v2_fixed.py - assembles cached LTX v2 clips into mobile (1080x1920) and desktop (1920x1080)
import json, os, subprocess, time, concurrent.futures, shutil

ROOT = "/root/reels_ltx"
IMG_ROOT = "/root/reels_r3/img"
TTS_ROOT = "/root/reels_r3/tts"
BED = "/root/reels_r3/bed.wav"
CLIPS_M = os.path.join(ROOT, "clips_v2_mobile")
CLIPS_D = os.path.join(ROOT, "clips_v2_desktop")
OUT_M = os.path.join(ROOT, "out_v2_mobile")
OUT_D = os.path.join(ROOT, "out_v2_desktop")
BUILD = os.path.join(ROOT, "build_v2")
MAN = "/root/reels_r3/manifest_r4_b07_v2_realism.json"

FPS = 30
LEAD=0.35; GAP=0.30; TAIL=0.55; MINPANEL=7.5; RECAP=3.4
FONTS={'en':'Noto Sans','es':'Noto Sans','zh':'Noto Sans CJK SC','ar':'Noto Naskh Arabic'}

reels=json.load(open(MAN,encoding='utf-8'))['reels']

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def lang_of(v): return v.split('-')[0]
def esc(t): return t.replace('\\','\\\\').replace('{','\\{').replace('}','\\}')
def ts(s):
    h=int(s//3600); m=int((s%3600)//60); sec=s%60
    return f"{h}:{m:02d}:{sec:05.2f}"

_durc={}
def get_dur(p):
    if p not in _durc:
        r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True)
        _durc[p]=float(r.stdout.decode().strip())
    return _durc[p]

def tp(rid,name): return os.path.join(TTS_ROOT,f"{rid}_{name}.mp3")

def build_timeline(r):
    rid=r['id']; ls=lang_of(r['voice_src']); lt=lang_of(r['voice_tgt'])
    ev=[]; audio=[]; panels=[]; cur=0.0
    for k,line in enumerate(r['lines']):
        pstart=cur
        da=get_dur(tp(rid,f"L{k+1}a")); db=get_dur(tp(rid,f"L{k+1}b"))
        s0=cur+LEAD; t0=s0+da+GAP
        audio.append((tp(rid,f"L{k+1}a"),int(round(s0*1000))))
        audio.append((tp(rid,f"L{k+1}b"),int(round(t0*1000))))
        pend=max(pstart+MINPANEL,t0+db+TAIL)
        ev.append((s0-0.05,min(s0+da+0.25,pend-0.1),'Src',line['src']))
        ev.append((t0-0.05,pend-0.15,'Tgt',line['tgt']))
        if line.get('translit'): ev.append((t0-0.05,pend-0.15,'Tr',line['translit']))
        panels.append((pstart,pend,k)); cur=pend
    pstart=cur; wcur=cur+LEAD
    for j,w in enumerate(r['words']):
        da=get_dur(tp(rid,f"w{j+1}a")); db=get_dur(tp(rid,f"w{j+1}b"))
        s0=wcur; t0=s0+da+GAP; wend=t0+db
        audio.append((tp(rid,f"w{j+1}a"),int(round(s0*1000))))
        audio.append((tp(rid,f"w{j+1}b"),int(round(t0*1000))))
        wt=w['src'].title() if ls=='en' else w['src']
        wb=w['tgt'].title() if lt=='en' else w['tgt']
        if w.get('translit'): wb=wb+"  ("+w['translit']+")"
        ev.append((s0-0.05,wend+0.30,'Src',wt)); ev.append((s0-0.05,wend+0.30,'Tgt',wb))
        wcur=wend+0.45
    rstart=wcur+0.35; rend=rstart+RECAP
    ys={1:[960],2:[860,1120],3:[700,960,1220]}[len(r['words'])]
    for j,w in enumerate(r['words']):
        wt=w['src'].title() if ls=='en' else w['src']
        wb=w['tgt'].title() if lt=='en' else w['tgt']
        if w.get('translit'): wb=wb+"  ("+w['translit']+")"
        ev.append((rstart,rend,'Src','{\\pos(540,%d)}'%ys[j]+wt))
        ev.append((rstart,rend,'Tgt','{\\pos(540,%d)}'%(ys[j]+64)+wb))
    pend=max(pstart+MINPANEL,wcur+0.25,rend+0.35)
    panels.append((pstart,pend,3)); cur=pend
    return panels, ev, audio, cur

def make_ass(r, ev, w, h):
    ls=lang_of(r['voice_src']); lt=lang_of(r['voice_tgt'])
    fs=FONTS.get(ls,'Noto Sans'); ft=FONTS.get(lt,'Noto Sans')
    head=(f"[Script Info]\nPlayResX: {w}\nPlayResY: {h}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Src,{fs},56,&H00FFFFFF,&H00FFFFFF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,8,70,70,170,1\n"
        f"Style: Tgt,{ft},62,&H0000D7FF,&H0000D7FF,&H90000000,&H90000000,1,0,0,0,100,100,0,0,1,3,1.5,2,70,70,330,1\n"
        f"Style: Tr,{ft},38,&H00E8E8E8,&H00E8E8E8,&H90000000,&H90000000,0,2,0,0,100,100,0,0,1,2.5,1,2,70,70,210,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines=[]
    for (a,b,st,txt) in ev:
        body = txt if txt.startswith('{\\pos(') else esc(txt)
        lines.append(f"Dialogue: 0,{ts(a)},{ts(b)},{st},,0,0,0,,{body}")
    return head+"\n".join(lines)+"\n"

def run_cmd(cmd):
    p=subprocess.run(cmd,capture_output=True)
    if p.returncode!=0:
        raise RuntimeError('CMD FAIL '+cmd[0]+' :: '+p.stderr.decode()[-300:])

def build_seg_from_clip(clip, out, target_dur, frames, tw, th):
    vf=f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},fps=30"
    run_cmd(['ffmpeg','-y','-i',clip,'-t',f"{target_dur:.3f}",'-vf',vf,
             '-frames:v',str(frames),'-c:v','libx264','-preset','veryfast','-crf','19',
             '-pix_fmt','yuv420p','-an',out])

def build_static_recap(img, out, frames, tw, th, zoom):
    vf=f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},{zoom.format(n=frames)}"
    run_cmd(['ffmpeg','-y','-loop','1','-i',img,'-vf',vf,'-frames:v',str(frames),
             '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',out])

def assemble(r, clips_dir, out_dir, tw, th, clip_prefix):
    rid=r['id']
    d=os.path.join(BUILD, f"{rid}_{tw}x{th}")
    os.makedirs(d,exist_ok=True)
    panels, ev, audio, total = build_timeline(r)
    assp=os.path.join(d,rid+'.ass')
    open(assp,'w',encoding='utf-8').write(make_ass(r,ev,tw,th))

    zoom_m="zoompan=z='1.09':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/{n}':d={n}:s=1080x1920:fps=30"
    zoom_d="zoompan=z='1.09':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1920x1080:fps=30"
    zoom=zoom_m if tw==1080 else zoom_d

    segs=[]
    for i,(pstart,pend,k) in enumerate(panels):
        frames=max(30,int(round((pend-pstart)*FPS)))
        seg=os.path.join(d,f"seg{k+1}.mp4")
        if k<3:
            clip=os.path.join(clips_dir,f"{clip_prefix}_p{k+1}.mp4")
            if not os.path.exists(clip):
                raise RuntimeError(f"missing clip {clip}")
            if not (os.path.exists(seg) and os.path.getsize(seg)>100000):
                build_seg_from_clip(clip,seg,pend-pstart,frames,tw,th)
        else:
            img=os.path.join(IMG_ROOT,f"{rid}_s{k+1}.png")
            if not (os.path.exists(seg) and os.path.getsize(seg)>100000):
                build_static_recap(img,seg,frames,tw,th,zoom)
        segs.append(seg)

    lst=os.path.join(d,'segs.txt')
    open(lst,'w').write("".join(f"file '{s}'\n" for s in segs))
    vsub=os.path.join(d,'vsub.mp4')
    run_cmd(['ffmpeg','-y','-f','concat','-safe','0','-i',lst,
             '-vf',f"ass={assp}",'-c:v','libx264','-preset','veryfast',
             '-crf','19','-pix_fmt','yuv420p',vsub])

    out=os.path.join(out_dir,r['channel'],rid+'.mp4')
    os.makedirs(os.path.dirname(out),exist_ok=True)
    n=len(audio)
    fc="".join(f"[{i+1}]adelay={ms}|{ms}[a{i}];" for i,(p,ms) in enumerate(audio))
    fc+=f"[{n+1}]volume=0.13[mus];"
    fc+="".join(f"[a{i}]" for i in range(n))
    fc+="[mus]amix=inputs=%d:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]"%(n+1)
    cmd=['ffmpeg','-y','-i',vsub]
    for (p,ms) in audio: cmd+=['-i',p]
    cmd+=['-stream_loop','-1','-i',BED,'-filter_complex',fc,'-map','0:v','-map','[a]',
          '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',
          '-c:a','aac','-b:a','160k','-t',f"{total:.2f}",'-movflags','+faststart',out]
    run_cmd(cmd)

    sp=os.path.join(out_dir,r['channel'],rid+'.script.txt')
    with open(sp,'w',encoding='utf-8') as f:
        f.write(f"TITLE: {r['id']} | {r['topic']}\nMODE: {r.get('mode','realistic')}\nCHANNEL: {r['channel']} | PAIR: {r['pair']}\n\n=== WORDS ===\n")
        for w in r['words']:
            f.write(f"{w['src']} = {w['tgt']}")
            if w.get('translit'): f.write(f" ({w['translit']})")
            f.write("\n")
        f.write("\n=== DIALOG ===\n")
        for ln in r['lines']:
            f.write(f"SRC: {ln['src']}\nTGT: {ln['tgt']}")
            if ln.get('translit'): f.write(f"\nTRL: {ln['translit']}")
            f.write("\n\n")
        f.write("\n=== SCENES ===\n")
        for i,s in enumerate(r['scenes']):
            f.write(f"Scene {i+1}: {s}\n")
    shutil.copy(assp, os.path.join(out_dir,r['channel'],rid+'.ass'))
    return out, total

def main():
    t0=time.time()
    for r in reels:
        rid=r['id']
        try:
            m,mt=assemble(r, CLIPS_M, OUT_M, 1080, 1920, rid+"_m")
            d,dt=assemble(r, CLIPS_D, OUT_D, 1920, 1080, rid+"_d")
            log(f"DONE {rid} mobile={mt:.1f}s desktop={dt:.1f}s")
        except Exception as e:
            log(f"FAIL {rid}: {e}")
    log(f"ASSEMBLE_ALL_DONE total={int(time.time()-t0)}s")

if __name__=="__main__":
    main()
