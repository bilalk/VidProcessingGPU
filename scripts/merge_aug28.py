import json
SRC = r'C:\ProjectComfy\reels'
a = json.load(open(rf'{SRC}\manifest_aug28_g1.json', encoding='utf-8'))['reels']
b = json.load(open(rf'{SRC}\manifest_aug28_g2.json', encoding='utf-8'))['reels']
merged = {'reels': a + b}
json.dump(merged, open(rf'{SRC}\manifest_aug28_all.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'merged {len(a)}+{len(b)} = {len(merged["reels"])} reels -> manifest_aug28_all.json')
