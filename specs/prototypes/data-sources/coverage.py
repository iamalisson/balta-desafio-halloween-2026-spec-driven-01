import sqlite3, json, sys, re, collections
dl, db = sys.argv[1], sys.argv[2]
rows = [l.split('\t') for l in open(dl+'/sx/SUBTLEX-CH-WF', encoding='gb18030').read().splitlines()[3:]]
words = [(r[0], int(r[1])) for r in rows if len(r) > 1]
total = 33546516
han = re.compile(r'^[一-鿿]+$')
print('subtlex rows', len(words), 'non-han rows', sum(1 for w,_ in words if not han.match(w)))
for n in (100, 500, 1000, 2000, 3000, 5000):
    print(f'top{n} token coverage {sum(c for _,c in words[:n])/total:.1%}')
top = [w for w,_ in words[:1000]]
# deck
con = sqlite3.connect(db)
flds = [r[0].split('\x1f') for r in con.execute('select flds from notes')]
deck = {}
for f in flds:
    c = re.sub(r'<[^>]+>|&nbsp;', '', f[1]).strip()
    deck.setdefault(c, f[-1])
print('deck notes', len(flds), 'distinct Caracter', len(deck))
inter = [w for w in top if w in deck]
print('top1000 in deck exact', len(inter))
print('top1000 missing sample', [w for w in top if w not in deck][:40])
# HSK 3.0
h = json.load(open(dl+'/hsk.json'))
lv = collections.Counter(); new = {}
for e in h:
    for l in e['level']:
        if l.startswith('new-'): new.setdefault(e['simplified'], l); lv[l]+=1
print('hsk3 counts', sorted(lv.items()))
print('top1000 in hsk3.0 any', sum(w in new for w in top), 'by level', sorted(collections.Counter(new[w] for w in top if w in new).items()))
hsk3_1_3 = {w for w,l in new.items() if l in ('new-1','new-2','new-3')}
print('hsk3 L1-3 size', len(hsk3_1_3), 'in deck', sum(w in deck for w in hsk3_1_3))
# MMAH chars
mm = {json.loads(l)['character'] for l in open(dl+'/mmah_dict.txt')}
chars = {ch for w in top for ch in w}
print('distinct chars in top1000', len(chars), 'in MMAH', len(chars & mm))
# CEDICT
ce = set()
import gzip
for l in gzip.open(dl+'/cedict.txt.gz','rt',encoding='utf-8'):
    if not l.startswith('#'): ce.add(l.split(' ',2)[1])
print('top1000 in CEDICT', sum(w in ce for w in top))
norm = set()
for k in deck:
    for p in re.split(r'[…\.。,，、/／|（）()\s　]+', k):
        if p: norm.add(p)
    norm.add(re.sub(r'[（(][^）)]*[）)]', '', k))
hit = [w for w in top if w in norm]
print('top1000 in deck after splitting 虽然…但是… / 没(有) variants', len(hit))
hz_chars = {ch for k in norm for ch in k}
print('top1000 words whose every char appears somewhere in deck', sum(all(ch in hz_chars for ch in w) for w in top))
open(dl+'/../top1000_missing_from_deck.txt','w').write('\n'.join(w for w in top if w not in norm))
