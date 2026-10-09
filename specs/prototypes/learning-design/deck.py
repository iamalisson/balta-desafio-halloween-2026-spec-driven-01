import sqlite3, sys, re
from wordfreq import top_n_list
db = sqlite3.connect(sys.argv[1])
rows = db.execute("select flds from notes").fetchall()
deck = {}
for (f,) in rows:
    p = f.split('\x1f'); lvl = p[0].split('_')[0]
    w = re.sub('<[^>]+>','',p[1]).strip()
    deck.setdefault(w, lvl)
top = top_n_list('zh', 1000)
top = [w for w in top if re.fullmatch(r'[一-鿿]+', w)]
print('han words in top1000', len(top))
from collections import Counter
c = Counter(deck.get(w,'none') for w in top)
print(sorted(c.items()))
print('hsk1-2 in top1000:', c['1']+c['2'], 'not in any HSK:', c['none'])
print('sample non-HSK:', [w for w in top if w not in deck][:40])
