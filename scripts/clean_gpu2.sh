#!/bin/bash
for ws in /root/reels_g2_w01 /root/reels_g2_w02; do
    for f in assemble5.py tts_gen3.py flux_gen_opt.py gen_bed_r3.py; do
        if head -1 $ws/$f | grep -q snt2508; then
            tail -n +2 $ws/$f > ${ws}/${f}.clean && mv ${ws}/${f}.clean $ws/$f
            echo "CLEANED $f in $ws"
        fi
    done
    echo "$ws head=$(head -c 30 $ws/assemble5.py)"
done
echo "ALL CLEAN"
