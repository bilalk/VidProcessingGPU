p = '/root/reels_ltx/run_ltx_v3.py'
s = open(p, encoding='utf-8').read()
old = 'MAN = "/root/reels_r3/manifest_r4_b07_v2_realism.json"'
new = 'MAN = sys.argv[2] if len(sys.argv) > 2 else "/root/reels_r3/manifest_r4_b07_v2_realism.json"'
if old not in s:
    print('FAIL: MAN line not found'); raise SystemExit(1)
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('OK: MAN now accepts argv[2] (manifest path)')
