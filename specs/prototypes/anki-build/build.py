"""Prototype: build tiny deck with genanki. usage: uv run --no-project --with genanki python -I build.py OUT.apkg [variant]"""
import genanki, json, re, sqlite3, subprocess, sys
from pathlib import Path
S = Path(__file__).resolve().parent.parent
APKG = S / "apkg"; MEDIA = Path(__file__).resolve().parent / "media_out"; MEDIA.mkdir(exist_ok=True)

# hanzi -> reference mp3 name, numbered file -> name
idx2name = json.load(open(Path(__file__).resolve().parent / "media_map.json"))
name2idx = {v: k for k, v in idx2name.items()}
h2a = {}
for (f,) in sqlite3.connect(APKG / "col.db").execute("select flds from notes"):
    p = f.split("\x1f"); a = re.findall(r"\[sound:(.+?)\]", f)
    if len(p) == 5 and a and a[0] in name2idx: h2a.setdefault(p[1], a[0])

def audio(hanzi):
    name = h2a.get(hanzi)
    if not name: return ""  # TTS fallback goes here
    out = MEDIA / name
    if not out.exists():  # new-format apkg stores media zstd-compressed
        out.write_bytes(subprocess.run(["zstd", "-dc", str(APKG / name2idx[name])], check=True, capture_output=True).stdout)
    return f"[sound:{name}]"

FIELDS = ["Hanzi", "Pinyin", "English", "Audio", "Components", "Mnemonic", "Example", "Source", "Listen"]
CSS = """.card{font-family:sans-serif;font-size:22px;text-align:center}
.hanzi{font-size:72px}.pequeno{font-size:16px;color:#888}.ex{font-size:20px}"""
BACK = """{{FrontSide}}<hr id=answer>
<div>{{Pinyin}}</div><div>{{English}}</div>{{Audio}}
{{#Components}}<div class=pequeno>{{Components}}</div>{{/Components}}
{{#Mnemonic}}<div class=pequeno>{{Mnemonic}}</div>{{/Mnemonic}}
{{#Example}}<div class=ex>{{Example}}</div>{{/Example}}
{{#Source}}<div class=pequeno>seen in: {{Source}}</div>{{/Source}}"""
MODEL = genanki.Model(
    1700000000001, "ZH Survival (EN)", fields=[{"name": f} for f in FIELDS], css=CSS,
    templates=[
        {"name": "Recognize", "qfmt": "<div class=hanzi>{{Hanzi}}</div>", "afmt": BACK},
        # only generated when Listen field non-empty (genanki computes req)
        {"name": "Listen", "qfmt": "{{#Listen}}{{Audio}}<div class=pequeno>listen</div>{{/Listen}}", "afmt": BACK},
    ])

class Note(genanki.Note):
    @property
    def guid(self): return genanki.guid_for(self.fields[0])  # stable on hanzi only

DECK = {"ui": genanki.Deck(1700000000101, "中文::1 Brave UI"), "words": genanki.Deck(1700000000102, "中文::2 Top words")}
v2 = len(sys.argv) > 2
rows = [  # (deck, rank, hanzi, pinyin, english, components, mnemonic, example, tags)
    ("ui", 1, "复制", "fùzhì", "copy", "复 again + 制 make", "make it again", "", ["brave", "ctxmenu"]),
    ("ui", 2, "搜索", "sōusuǒ", "search", "扌hand + 叟 / 索 rope", "hand pulls the rope to find", "", ["brave", "search"]),
    ("ui", 3, "下载", "xiàzài", "download", "下 down + 载 load", "load down", "", ["brave"]),
    ("words", 1, "的", "de", "(possessive particle)", "白 white + 勺 ladle", "", "我的书 my book", ["hsk1"]),
    ("words", 2, "爱", "ài", "to love" + (" (edited)" if v2 else ""), "爫 claw + 冖 cover + 友 friend", "", "", ["hsk1"]),
]
if v2: rows.append(("words", 3, "设置", "shèzhì", "settings", "", "", "", ["hsk5"]))
for d, rank, h, py, en, comp, mn, ex, tags in rows:
    DECK[d].add_note(Note(model=MODEL, fields=[h, py, en, audio(h), comp, mn, ex, "", "y" if d == "words" else ""],
                          tags=tags + [f"tier::{d}"], due=rank))
pkg = genanki.Package(list(DECK.values())); pkg.media_files = sorted(str(p) for p in MEDIA.glob("*.mp3"))
pkg.write_to_file(sys.argv[1]); print("wrote", sys.argv[1], len(pkg.media_files), "media")
