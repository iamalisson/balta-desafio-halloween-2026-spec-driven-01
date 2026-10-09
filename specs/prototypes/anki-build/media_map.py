"""Decode new-format apkg 'media' (zstd-decompressed protobuf) -> {index: filename}. stdlib only."""
import sys, json
def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1; r |= (c & 0x7f) << s; s += 7
        if c < 0x80: return r, i
def fields(b):
    i = 0
    while i < len(b):
        k, i = varint(b, i); f, t = k >> 3, k & 7
        if t == 0: v, i = varint(b, i)
        elif t == 2: n, i = varint(b, i); v = b[i:i+n]; i += n
        else: raise ValueError(t)
        yield f, v
def media_map(pb):
    # MediaEntries{repeated MediaEntry entries=1}; MediaEntry{name=1,size=2,sha1=3}; position == numbered file
    return {str(n): dict(fields(e))[1].decode() for n, (f, e) in enumerate(fields(pb)) if f == 1}
if __name__ == "__main__":
    m = media_map(open(sys.argv[1], "rb").read())
    json.dump(m, open(sys.argv[2], "w"), ensure_ascii=False)
    print(len(m), list(m.items())[:3])
