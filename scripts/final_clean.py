files=['/root/reels_r3/assemble5.py','/root/reels_r3/flux_gen_opt.py','/root/reels_r3/tts_gen3.py','/root/reels_r3/flux_gen5.py','/root/reels_r3/gen_bed_r3.py']
for f in files:
    lines=open(f).readlines()
    if 'snt2508' in lines[0]:
        open(f,'w').writelines(lines[1:])
        print(f"cleaned {f}")
print("done")
