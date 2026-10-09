from wordfreq import get_frequency_dict
import itertools
d = get_frequency_dict('zh')
fr = sorted(d.values(), reverse=True)
tot = sum(fr)
acc = list(itertools.accumulate(fr))
print('entries', len(fr), 'mass', round(tot,3))
for n in (100,300,500,1000,2000,3000,5000,10000):
    print(n, round(acc[n-1]/tot*100,1))
# HSK1 deck chars coverage, characters
