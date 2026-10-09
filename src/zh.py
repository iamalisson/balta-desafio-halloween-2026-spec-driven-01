"""Chinese survival kit: builds the Anki deck from Brave's own UI strings + the top-1000 words.

usage:
  uv run src/zh.py build [--first-import] [--no-tts] [--brave-dir DIR]
  uv run src/zh.py yomidict

See specs/plan.md for the logic behind every step.
"""
import argparse, asyncio, gzip, hashlib, html, io, json, re, shutil, sqlite3, ssl, struct, subprocess, sys, urllib.request, zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE, BUILD = ROOT / "cache", ROOT / "build"
MEDIA = BUILD / "media"
REF_APKG = ROOT / "assets" / "HSK PT-BR NOV 2016.apkg"
URLS = {
    "cedict.txt.gz": "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz",
    "mmah.txt": "https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt",
    "cmn-eng.zip": "https://www.manythings.org/anki/cmn-eng.zip",
}
CJK = re.compile(r"[㐀-鿿]")
ANKICONNECT = "http://localhost:8765"


def fetch(name):
    """Download once into cache/, then reuse."""
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(exist_ok=True)
        print("downloading", URLS[name])
        # manythings answers 406 to browser and python user agents
        req = urllib.request.Request(URLS[name], headers={"User-Agent": "curl/8.0"})
        path.write_bytes(urllib.request.urlopen(req, timeout=120, context=ssl_context()).read())
    return path


def ssl_context():
    """uv's Python does not see NixOS's CA bundle, so fall back to the system file."""
    ctx = ssl.create_default_context()
    if not ctx.get_ca_certs():
        for f in ("/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/cert.pem"):
            if Path(f).exists():
                ctx.load_verify_locations(f); break
    return ctx


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


# ---------------------------------------------------------------- Brave paks (plan Decisions 1-3)

def read_pak(path):
    """Chromium pak v5 -> {id: bytes}. Header: u32 version, u32 encoding, u16 n, u16 n_alias;
    (n+1) x (u16 id, u32 offset), last is a sentinel; then n_alias x (u16 id, u16 entry_index)."""
    b = Path(path).read_bytes()
    ver, enc, n, na = struct.unpack_from("<IIHH", b, 0)
    if ver != 5 or enc != 1:
        sys.exit(f"{path}: pak version {ver} encoding {enc}, only v5 UTF-8 is supported")
    ents = [struct.unpack_from("<HI", b, 12 + 6 * i) for i in range(n + 1)]
    out = {ents[i][0]: b[ents[i][1]:ents[i + 1][1]] for i in range(n)}
    pos = 12 + 6 * (n + 1)
    for i in range(na):  # zh dedupes more strings than en, so aliases must be resolved
        aid, idx = struct.unpack_from("<HH", b, pos + 4 * i)
        out[aid] = b[ents[idx][1]:ents[idx + 1][1]]
    return out


def brave_locales(brave_dir=None):
    if brave_dir:
        return Path(brave_dir) / "locales"
    exe = shutil.which("brave") or shutil.which("brave-browser")
    if not exe:
        sys.exit("brave not found in PATH; pass --brave-dir")
    for root in Path(exe).resolve().parents:  # NixOS: the store path changes on every upgrade
        loc = root / "opt" / "brave.com" / "brave" / "locales"
        if loc.is_dir():
            return loc
    sys.exit(f"no locales dir found above {exe}; pass --brave-dir")


PLACEHOLDER = re.compile(r"\$\d|<ph\b|\{[A-Za-z_0-9]+[,}]|<[a-z]+[ >/]")
MNEMONIC = re.compile(r"&(?=[^&\s])")  # "&Copy" = menu accelerator, so the string IS a menu item
BRANDS = {"Brave", "JavaScript", "PDF", "URL", "Google", "Chrome", "Chromium", "Tor", "IPFS", "VPN", "Wi", "Fi", "Leo", "AI"}

# Seed labels in surface order: what the user meets first after the switch comes first in the deck.
SEED = {
    "ctxmenu": "Back|Forward|Reload|Open link in new tab|Open link in new window|Open link in Brave private window|"
               "Copy link address|Save link as...|Open image in new tab|Save image as...|Copy image|Copy|Paste|Cut|"
               "Select all|Save as...|Print...|Inspect|View page source",
    "tabmenu": "New tab|Close tab|Reopen closed tab|Duplicate|Pin|Unpin|Mute site|Close other tabs|"
               "Close tabs to the right|Move tab to new window",
    "appmenu": "New window|New private window|History|Downloads|Bookmarks|Bookmark this tab...|Bookmarks manager|"
               "Show bookmarks bar|Zoom|Find...|More tools|Extensions|Full screen|Settings|Help|Exit",
    "dialog": "OK|Cancel|Done|Save|Open|Close|Allow|Block|Continue|Retry|Not now|Learn more|Delete|Edit|Rename|"
              "Add|Remove|Undo|Redo",
    "settings": "Appearance|Privacy and security|Search engine|On startup|Languages|Passwords and autofill|"
                "Delete browsing data|Shields",
}
SEED_ORDER = [(surface, label) for surface, labels in SEED.items() for label in labels.split("|")]
UI_COMPOUNDS = ["标签页", "书签栏", "另存为", "搜索引擎", "扩展程序", "无痕式窗口", "隐私窗口", "源代码", "书签管理器"]


def norm_en(e):
    return MNEMONIC.sub("", e).replace("&&", "&").replace("…", "...").strip()


def norm_zh(z):
    return re.sub(r"\(&\w\)", "", z).replace("&", "").replace("…", "").strip()


def keep(en, zh):
    """Drop rules apply to every string, seeds included (plan Decision 3); 6 words keeps 'Open link in Brave private window'."""
    if PLACEHOLDER.search(en) or re.search(r"\{\w+,\s*(plural|select)", en):
        return False
    if len(en.split()) > 6 or len(en) > 40 or not CJK.search(zh):
        return False
    return all(w in BRANDS for w in re.findall(r"[A-Za-z]{2,}", zh))  # untranslated leftovers out


def brave_tier1(locales):
    """-> [(en, zh, surface)] ordered: seeds by surface, then other menu items by resource id."""
    en = {k: v.decode("utf-8", "replace") for k, v in read_pak(locales / "en-US.pak").items()}
    zh = {k: v.decode("utf-8", "replace") for k, v in read_pak(locales / "zh-CN.pak").items()}
    common = en.keys() & zh.keys()
    pairs = [(k, norm_en(en[k]), norm_zh(zh[k]), bool(MNEMONIC.search(en[k]))) for k in sorted(common)
             if en[k].strip() and en[k] != zh[k]]
    pairs = [p for p in pairs if keep(p[1], p[2])]
    by_en = {}
    for _, e, z, _ in pairs:  # one English label can have several zh variants: keep the most frequent
        by_en.setdefault(e.lower(), Counter())[z] += 1
    out, seen_zh = [], set()
    missing = []
    for surface, label in SEED_ORDER:
        variants = by_en.get(label.lower())
        if not variants:
            missing.append(label)
            continue
        z = variants.most_common(1)[0][0]
        if z not in seen_zh:
            seen_zh.add(z); out.append((label, z, surface))
    for _, e, z, mnem in pairs:
        if mnem and z not in seen_zh:
            seen_zh.add(z); out.append((e, z, "menu"))
    print(f"brave: {len(common)} common ids, {len(pairs)} kept pairs, {len(out)} tier-1 phrases")
    if missing:
        print("  seeds not found:", missing)
    return out


# ---------------------------------------------------------------- CC-CEDICT + pinyin (Decisions 9-10)

TONES = {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "ü": "ǖǘǚǜ"}


def marks(numbered):
    """'Zhong1 wen2' -> 'Zhōng wén'; 'nu:3' -> 'nǚ'; 'ma5' -> 'ma'."""
    out = []
    for syl in numbered.split():
        m = re.fullmatch(r"([A-Za-z:]+)([1-5])", syl)
        if not m:
            out.append(syl.replace("u:", "ü")); continue
        base, tone = m.group(1).replace("u:", "ü").replace("U:", "Ü"), int(m.group(2))
        low = base.lower()
        if tone != 5 and any(v in low for v in "aeiouü"):  # m2 / hm5 / ng2 have no vowel: left unmarked
            i = low.find("a") if "a" in low else low.find("e") if "e" in low else low.find("o") if "ou" in low else \
                max(low.rfind(v) for v in "iouü")
            ch = TONES[low[i]][tone - 1]
            base = base[:i] + (ch.upper() if base[i].isupper() else ch) + base[i + 1:]
        out.append(base)
    return " ".join(out)


BAD_SENSE = re.compile(r"^(variant of|old variant|archaic variant|Japanese variant|used in|surname |see |CL:)")


def load_cedict():
    """-> {simplified: [(pinyin_marked, [senses])]}, plus the set of traditional-only characters."""
    d, trad_only, simp_chars = {}, set(), set()
    for line in gzip.open(fetch("cedict.txt.gz"), "rt", encoding="utf-8"):
        m = re.match(r"^(\S+) (\S+) \[([^\]]+)\] /(.*)/$", line.strip())
        if not m:
            continue
        trad, simp, py, defs = m.groups()
        simp_chars.update(simp)
        if len(trad) == 1 and trad != simp:
            trad_only.add(trad)
        senses = [s for s in defs.split("/") if s and not BAD_SENSE.match(s)]
        if senses:
            d.setdefault(simp, []).append((marks(py), senses))
    return d, trad_only - simp_chars


class Lexicon:
    def __init__(self, cedict, ref):
        self.cedict, self.ref = cedict, ref

    def entries(self, w):
        ents = self.cedict.get(w, [])
        low = [e for e in ents if not e[0][:1].isupper()]
        # proper nouns (美国) only when nothing else exists; main reading first (打 dǎ before dá "dozen")
        return sorted(low or ents, key=lambda e: (e[1][0].startswith(("(onom.)", "(literary)")), -len(e[1])))

    def pinyin(self, w):
        if w in self.ref and self.ref[w]["pinyin"]:
            return self.ref[w]["pinyin"]
        readings = list(dict.fromkeys(p.replace(" ", "") for p, _ in self.entries(w)))[:2]
        return " / ".join(readings) or " ".join(self.first_pinyin(c) for c in w if len(w) > 1)

    def gloss(self, w, per_char_fallback=True):
        ents = self.entries(w)
        if ents:
            ref_py = self.ref.get(w, {}).get("pinyin", "")
            # first CEDICT entry with the reference reading, proper nouns excluded (比 Bǐ "Belgium")
            ent = next((e for e in self.cedict[w] if e in ents and e[0].replace(" ", "") == ref_py), ents[0])
            return "; ".join(ent[1][:3])
        if per_char_fallback and len(w) > 1:
            return " + ".join(f"{c} {self.short(c)}" for c in w)
        return ""

    def short(self, c):
        g = self.gloss(c, False).split(";")[0]
        g = re.sub(r"\s*radical in Chinese characters \(Kangxi radical \d+\)", " radical", g)
        g = re.sub(r",? (occurring in|aka) .*| \(Kangxi radical \d+\)| \(side part of split character\)", "", g)
        return re.sub(r"^\((bound form|literary|old)\)\s*", "", g).strip()

    def first_pinyin(self, w):
        return self.pinyin(w).split(" / ")[0]


# ---------------------------------------------------------------- reference HSK deck (Decisions 9, 11)

def zstd(data):
    return subprocess.run(["zstd", "-dc"], input=data, capture_output=True, check=True).stdout


def media_map(pb):
    """zstd-decompressed protobuf MediaEntries{repeated MediaEntry=1}; MediaEntry{name=1,size=2,sha1=3}.
    The position of each entry is the name of its numbered file inside the apkg."""
    def varint(b, i):
        r = s = 0
        while True:
            c = b[i]; i += 1; r |= (c & 0x7F) << s; s += 7
            if c < 0x80:
                return r, i

    def fields(b):
        i = 0
        while i < len(b):
            k, i = varint(b, i)
            if k & 7 == 0:
                v, i = varint(b, i)
            else:
                n, i = varint(b, i); v = b[i:i + n]; i += n
            yield k >> 3, v

    return {str(n): dict(fields(e))[1].decode() for n, (f, e) in enumerate(fields(pb)) if f == 1}


class RefDeck:
    """hanzi -> {pinyin, audio, hsk} from the user's HSK PT-BR deck (exact field matches only)."""

    def __init__(self, apkg=REF_APKG):
        self.words = {}
        if not apkg.exists():  # optional: without it pinyin comes from CC-CEDICT and audio from TTS
            print(f"reference deck not found ({apkg.name}): continuing without it")
            return
        self.zip = zipfile.ZipFile(apkg)
        db = CACHE / "ref-col.db"
        if not db.exists():
            CACHE.mkdir(exist_ok=True)
            db.write_bytes(zstd(self.zip.read("collection.anki21b")))
        self.name2idx = {v: k for k, v in media_map(zstd(self.zip.read("media"))).items()}
        for (f,) in sqlite3.connect(db).execute("select flds from notes"):
            p = f.split("\x1f")
            if len(p) != 5:
                continue
            w = strip_html(p[1])
            a = re.findall(r"\[sound:(.+?)\]", p[4])
            self.words.setdefault(w, {"pinyin": strip_html(p[2]), "audio": a[0] if a and a[0] in self.name2idx else "",
                                      "hsk": "hsk" + p[0].split("_")[0]})

    def __contains__(self, w):
        return w in self.words

    def __getitem__(self, w):
        return self.words[w]

    def get(self, w, default=None):
        return self.words.get(w, default)

    def audio(self, w):
        """-> mp3 file name in build/media, extracted on demand, or ''."""
        name = self.words.get(w, {}).get("audio")
        if not name:
            return ""
        out = MEDIA / name
        if not out.exists():
            out.write_bytes(zstd(self.zip.read(self.name2idx[name])))  # numbered files are zstd too
        return name


# ---------------------------------------------------------------- word lists + sequence (Decisions 4-7)

def jieba_ready():
    import warnings
    warnings.filterwarnings("ignore", category=SyntaxWarning)  # jieba 0.42 has old regex escapes (Python 3.12+)
    import jieba
    jieba.setLogLevel(60)
    for w in UI_COMPOUNDS:
        jieba.add_word(w)
    return jieba


def words_of(jieba, phrase):
    return [t for t in jieba.lcut(phrase) if CJK.search(t)]


def top_words(lex, n=1000):
    from wordfreq import top_n_list
    out = [w for w in top_n_list("zh", n * 3) if re.fullmatch(r"[㐀-鿿]+", w) and lex.entries(w)]
    return out[:n]  # words with no CEDICT entry (两个, 一天) are skipped and the list refills


def load_mmah():
    return {d["character"]: d for d in map(json.loads, open(fetch("mmah.txt"), encoding="utf-8"))}


IDC = re.compile(r"[⿰-⿿？]")
# Ideographic Description Characters: how the parts sit inside the character
IDC_NAMES = {"⿰": "left | right", "⿱": "top / bottom", "⿲": "left | middle | right", "⿳": "top / middle / bottom",
             "⿴": "outside surrounds inside", "⿵": "surround open at the bottom", "⿶": "surround open at the top",
             "⿷": "surround open at the right", "⿸": "wraps from top-left", "⿹": "wraps from top-right",
             "⿺": "wraps from bottom-left", "⿻": "overlaid"}


def parts(c, mmah, lex):
    d = mmah.get(c)
    if not d or IDC.sub("", d.get("decomposition", "")) in ("", c):
        return ""
    comps = [x for x in IDC.sub("", d["decomposition"]) if x != c]
    named = [f"{x} {(lex.short(x) or mmah.get(x, {}).get('definition', '').split(';')[0]).strip()}".strip() for x in comps]
    layout = IDC_NAMES.get(d["decomposition"][0], "")
    return f"{d['decomposition'][0]} {layout}: " + " + ".join(named) if layout else " + ".join(named)


def hint(c, mmah):
    ety = mmah.get(c, {}).get("etymology") or {}
    return f"{ety.get('type', '')}: {ety['hint']}" if ety.get("hint") else ""


def sequence(ui_words, freq_words, phrases, jieba):
    """One learning order, parts before wholes: each new character right before the first word that uses it,
    each phrase right after its last word. UI and frequency words alternate 1:1 until UI words run out."""
    merged = []
    for i in range(max(len(ui_words), len(freq_words))):
        for lst in (ui_words, freq_words):
            if i < len(lst) and lst[i] not in merged:
                merged.append(lst[i])
    seq, seen = [], set()
    # phrase cards only for seed labels; other menu strings show up as SeenIn on their words
    pending = [(z, set(words_of(jieba, z))) for _, z, surface in phrases
               if surface != "menu" and len(words_of(jieba, z)) > 1]
    for w in merged:
        for c in w:
            if CJK.match(c) and c not in seen:
                seen.add(c); seq.append(("char", c))
        if len(w) > 1 and w not in seen:
            seen.add(w); seq.append(("word", w))
        for p in [p for p in pending if p[1] <= seen | set(w)]:
            pending.remove(p); seq.append(("phrase", p[0]))
    return merged, seq


def check_order(seq, jieba):
    """AC-03: no phrase before its words, no word before its characters."""
    pos = {(k, h): i for i, (k, h) in enumerate(seq)}
    for i, (k, h) in enumerate(seq):
        if k in ("word", "phrase"):
            assert all(pos.get(("char", c), -1) < i for c in h if CJK.match(c)), f"{h} before its characters"
        if k == "phrase":
            for w in words_of(jieba, h):
                j = pos.get(("word", w), pos.get(("char", w)))
                assert j is not None and j < i, f"phrase {h} before word {w}"
    assert len({h for _, h in seq if _ != "phrase"}) == sum(1 for k, _ in seq if k != "phrase"), "duplicate Hanzi"


# ---------------------------------------------------------------- examples (Decision 12)

def load_examples(jieba, trad_only):
    """-> [(zh, en, tokens)] simplified sentences of 12 characters or fewer (manythings / Tatoeba, CC-BY 2.0 FR)."""
    with zipfile.ZipFile(fetch("cmn-eng.zip")) as z:
        text = z.read("cmn.txt").decode("utf-8")
    out = []
    for line in text.splitlines():
        p = line.split("\t")
        if len(p) < 2 or len(CJK.findall(p[1])) > 12 or any(c in trad_only for c in p[1]):
            continue
        out.append((p[1], p[0], set(words_of(jieba, p[1]))))
    return out


def best_example(w, rank, index):
    """Sentence that contains w as a whole token and whose hardest word is the easiest."""
    cands = index.get(w, [])
    if not cands:
        return None
    return min(cands, key=lambda s: (max(rank.get(t, 10 ** 6) for t in s[2]), len(s[0])))


# ---------------------------------------------------------------- audio fallback (Decision 11)

def tts_all(texts, enabled):
    """edge-tts mp3s cached in cache/tts/; failure is a warning, never an error."""
    import edge_tts
    tts_dir = CACHE / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)
    names = {t: f"tts_{hashlib.sha1(t.encode()).hexdigest()[:10]}.mp3" for t in texts}
    todo = [t for t in texts if not (tts_dir / names[t]).exists()]
    failed = []
    if enabled and todo:
        print(f"tts: generating {len(todo)} mp3s")
        sem = asyncio.Semaphore(8)

        async def one(t):
            async with sem:
                try:
                    await edge_tts.Communicate(t, "zh-CN-XiaoxiaoNeural").save(str(tts_dir / names[t]))
                except Exception as e:  # network / endpoint trouble: skip this audio
                    failed.append((t, e))
                    (tts_dir / names[t]).unlink(missing_ok=True)

        async def run():
            await asyncio.gather(*(one(t) for t in todo))

        asyncio.run(run())
        if failed:
            print(f"  warning: {len(failed)} tts failures, e.g. {failed[0][0]}: {failed[0][1]}")
    out = {}
    for t, n in names.items():
        if (tts_dir / n).exists():
            shutil.copyfile(tts_dir / n, MEDIA / n); out[t] = n
    return out


# ---------------------------------------------------------------- AnkiConnect (Decision 13)

def anki(action, **params):
    req = json.dumps({"action": action, "version": 6, "params": params}).encode()
    r = json.load(urllib.request.urlopen(ANKICONNECT, req, timeout=30))
    if r["error"]:
        raise RuntimeError(f"AnkiConnect {action}: {r['error']}")
    return r["result"]


def collection_state():
    """-> (stories {hanzi: story}, mined {hanzi}) or None when Anki is not running."""
    try:
        anki("version")
    except OSError:
        return None
    def notes(query):
        ids = anki("findNotes", query=query)
        return anki("notesInfo", notes=ids) if ids else []
    stories = {strip_html(n["fields"]["Hanzi"]["value"]): n["fields"]["Story"]["value"]
               for n in notes('note:"ZH Char"') if n["fields"]["Story"]["value"].strip()}
    mined = {strip_html(n["fields"]["Hanzi"]["value"]) for n in notes('note:"Yomitan Hanzi"')}
    return stories, mined


# ---------------------------------------------------------------- Software deck: Linux (KDE) + Android + iOS + dates

URLS.update({f"android-{n}-{l}.xml": f"https://raw.githubusercontent.com/aosp-mirror/{repo}/main/{path}/res/values{suf}/strings.xml"
             for n, repo, path in (("settings", "platform_packages_apps_settings", ""),
                                   ("systemui", "platform_frameworks_base", "packages/SystemUI"))
             for l, suf in (("en", ""), ("zh", "-zh-rCN"))})
URLS = {k: v.replace("/main//res", "/main/res") for k, v in URLS.items()}
KDE_LOCALE = Path("/run/current-system/sw/share/locale/zh_CN/LC_MESSAGES")
SOFT_BRANDS = BRANDS | {"WLAN", "USB", "NFC", "SIM", "eSIM", "GPS", "App", "ID", "SOS", "Apple", "Pay", "iPhone",
                        "Android", "Linux", "KDE", "Plasma", "Wi", "Fi", "Siri", "iCloud", "AirDrop", "HDMI", "DNS"}


def soft_keep(en, zh):
    if PLACEHOLDER.search(en) or re.search(r"%|\\n|\n", en) or len(en.split()) > 4 or len(en) > 32:
        return False
    if zh.lower() == en.lower():
        return False
    return all(w in SOFT_BRANDS for w in re.findall(r"[A-Za-z]{2,}", zh)) and (bool(CJK.search(zh)) or zh in SOFT_BRANDS)


def clean_label(en, zh):
    en = MNEMONIC.sub("", en.split("\x04")[-1]).replace("&&", "&").strip().rstrip(":：…").replace("...", "").strip()
    zh = re.sub(r"\(&\w\)|（&\w）", "", zh).replace("&", "").strip().rstrip(":：…").strip()
    return en, zh


def kde_labels():
    """KDE/Plasma gettext catalogs on this machine -> {en_lower: (en, most common zh, n_apps)}."""
    import gettext
    count, variants, orig = Counter(), {}, {}
    for f in sorted(KDE_LOCALE.glob("*.mo")):
        try:
            cat = gettext.GNUTranslations(open(f, "rb"))._catalog
        except Exception:
            continue
        seen = set()
        for k, v in cat.items():
            if not isinstance(k, str) or not k or not isinstance(v, str):
                continue
            en, zh = clean_label(k, v)
            low = en.lower()
            if low in ("your names", "your emails") or not soft_keep(en, zh) or low in seen:
                continue
            seen.add(low); count[low] += 1
            variants.setdefault(low, Counter())[zh] += 1; orig.setdefault(low, en)
    return {k: (orig[k], variants[k].most_common(1)[0][0], n) for k, n in count.items()}


def android_labels():
    """AOSP Settings + SystemUI official en / zh-CN strings (Apache-2.0) -> {en_lower: (en, zh)}."""
    import xml.etree.ElementTree as ET
    def load(name):
        out = {}
        for el in ET.parse(fetch(name)).getroot().iter("string"):
            if el.find("{urn:oasis:names:tc:xliff:document:1.2}g") is None:
                t = "".join(el.itertext()).strip().strip('"')
                if t:
                    out[el.get("name")] = t
        return out
    out = {}
    for n in ("settings", "systemui"):
        en, zh = load(f"android-{n}-en.xml"), load(f"android-{n}-zh.xml")
        for k in en.keys() & zh.keys():
            e, z = clean_label(en[k], zh[k])
            if soft_keep(e, z):
                out.setdefault(e.lower(), (e, z))
    return out


def date_labels():
    """CLDR (babel) weekdays, day periods and relative-time patterns + everyday time words."""
    from babel import Locale
    from curated import DATE_WORDS
    loc = Locale("zh")
    names = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
    out = [(names[i], loc.days["format"]["wide"][i]) for i in range(7)]
    out += [(f"{names[i][:3]} (short)", loc.days["format"]["abbreviated"][i]) for i in range(7)]
    periods = {"morning1": "early morning", "morning2": "morning (a.m.)", "afternoon1": "noon",
               "afternoon2": "afternoon (p.m.)", "evening1": "evening", "night1": "small hours (after midnight)",
               "midnight": "midnight"}
    out += [(en, loc.day_periods["format"]["wide"][k]) for k, en in periods.items()]
    for unit, n in (("second", 5), ("minute", 3), ("hour", 2), ("day", 1), ("week", 1), ("month", 1), ("year", 1)):
        f = loc._data["date_fields"][unit]
        out.append((f"{n} {unit}{'s' if n > 1 else ''} ago", f["past"]["other"].format(n)))
        out.append((f"in {n} {unit}{'s' if n > 1 else ''}", f["future"]["other"].format(n)))
    out += [("January ... December (month N)", "一月"), ("date: 8 October 2026", "2026年10月8日")]
    return out + DATE_WORDS


def software_items(taken):
    """-> [(en, zh, platform)] ordered round-robin across Android, iOS, Linux and dates, most used first."""
    from curated import ANDROID_SEEDS, ESCAPE, IOS
    kde, android = kde_labels(), android_labels()
    andr = [android[s.lower()] for s in ANDROID_SEEDS if s.lower() in android]
    missing = [s for s in ANDROID_SEEDS if s.lower() not in android]
    shared = sorted((k for k in android.keys() & kde.keys()), key=lambda k: -kde[k][2])
    andr += [android[k] for k in shared[:120]]
    linux = [kde[k][:2] for k in sorted(kde, key=lambda k: -kde[k][2]) if kde[k][2] >= 3][:250]
    streams = [[(e, z, "Android") for e, z in andr], [(e, z, "iOS") for e, z in IOS],
               [(e, z, "Linux") for e, z in linux], [(e, z, "date/time") for e, z in date_labels()]]
    # way back to English first (unless Survival already teaches it), then the platforms round-robin
    out = [x for x in ESCAPE if x[1] not in taken]
    seen = set(taken) | {z for _, z, _ in out}
    for i in range(max(map(len, streams))):
        for st in streams:
            if i < len(st) and st[i][1] not in seen:
                seen.add(st[i][1]); out.append(st[i])
    print(f"software: {len(kde)} KDE labels, {len(android)} Android labels -> {len(out)} cards "
          f"({Counter(p for _, _, p in out)})")
    if missing:
        print("  android seeds not found:", missing)
    return out


# ---------------------------------------------------------------- Slang deck: internet slang + 成语 + 歇后语

SLANG = re.compile(r"\((Internet slang|slang)\)|neologism")
TAG = re.compile(r"\((Internet slang|slang|idiom|neologism[^)]*|loanword|lit\.|fig\.)\)\s*")


def slang_items(lex, jieba, taken, n_slang=400, n_idioms=300):
    """-> [(hanzi, pinyin, meaning, type)] interleaved 2 slang : 1 idiom, a saying every 8th card."""
    from wordfreq import zipf_frequency
    from curated import XIEHOUYU
    slang, idioms = [], []
    for w, ents in lex.cedict.items():
        if not CJK.search(w) or w in taken:
            continue
        for py, senses in ents:
            sl = [x for x in senses if SLANG.search(x) and not re.search(r"\((Tw|Cantonese|HK)\)", x)]
            if sl and len(w) > 1:
                normal = [x for e in ents for x in e[1] if not SLANG.search(x)][:2]
                meaning = "; ".join(TAG.sub("", x) for x in sl[:2])
                if normal:  # 开车 = "to drive" first, the slang sense second
                    meaning = f"slang: {meaning}<br>normal: {'; '.join(normal)}"
                slang.append((w, py.replace(" ", ""), meaning, "internet slang", bool(normal)))
                break
            if len(w) == 4 and any("(idiom)" in x for x in senses):
                idioms.append((w, py.replace(" ", ""), "; ".join(TAG.sub("", x) for x in senses[:2]), "idiom 成语", False))
                break
    # pure slang first: a common word with a rare slang sense (鸡, 坦克) ranks 2 Zipf points lower
    freq = lambda r: -(zipf_frequency(r[0], "zh") - 2 * r[4])
    slang = [r[:4] for r in sorted(slang, key=freq) if zipf_frequency(r[0], "zh") > 0][:n_slang]
    idioms = [r[:4] for r in sorted(idioms, key=freq)[:n_idioms]]
    sayings = [(z, " —— ".join(" ".join(lex.first_pinyin(w) for w in words_of(jieba, part)) for part in z.split("——")),
                en, "saying 歇后语") for z, en in XIEHOUYU]
    out, i = [], 0
    while slang or idioms or sayings:
        if sayings and i % 8 == 7:
            out.append(sayings.pop(0))
        elif slang and (i % 3 != 2 or not idioms):
            out.append(slang.pop(0))
        elif idioms:
            out.append(idioms.pop(0))
        else:
            out.append(sayings.pop(0))
        i += 1
    print(f"slang: {Counter(t for *_, t in out)}")
    return out


# ---------------------------------------------------------------- Anki package

CSS = """.card { font-size: 20px; text-align: center; color: black; background-color: white; }
.nightMode .card { color: white; background-color: #222; }
@font-face { font-family: myfont; src: url("_FandolKai-Regular.otf"); }
.hanzi { font-family: myfont; word-wrap: break-word; font-size: 48px; }
.front-wrap { min-height: 80vh; display: flex; flex-direction: column; justify-content: center; align-items: center; }
.main-hanzi { font-size: 110px; line-height: 1.2; }
.back-hanzi { font-size: 72px; }
.pinyin { font-size: 28px; }
.blk { margin: 6px 0; }
.notes { font-size: 16px; }
.meaning { color: black; }
.nightMode .meaning { color: white; }
.sub { font-size: 14px; color: gray; }
.ex { font-family: myfont; font-size: 30px; }
.ex b { color: #337ab7; }
.py { font-family: sans-serif; font-size: 16px; color: gray; }
.story { font-size: 16px; color: #2a6; }
"""
STROKES = """<div id=hz-src style="display:none">{{text:Hanzi}}</div><div id=hz-target></div>
<script>
(function () {
  // Stroke-order animation (hanzi-writer from jsDelivr: needs internet, silently skipped offline).
  var chars = document.getElementById("hz-src").textContent.match(/[\\u3400-\\u9fff]/g) || [];
  var target = document.getElementById("hz-target");
  var night = document.body.classList.contains("nightMode") || document.documentElement.classList.contains("night-mode");
  function draw() {
    target.innerHTML = "";
    chars.forEach(function (c) {
      HanziWriter.create(target, c, { width: 90, height: 90, padding: 5, showOutline: true,
        strokeColor: night ? "#ffffff" : "#333333", outlineColor: night ? "#555555" : "#dddddd",
        radicalColor: "#337ab7", delayBetweenStrokes: 150, strokeAnimationSpeed: 1 }).loopCharacterAnimation();
    });
  }
  if (window.HanziWriter) { draw(); return; }
  var js = document.createElement("script");
  js.src = "https://cdn.jsdelivr.net/npm/hanzi-writer@3.7.2/dist/hanzi-writer.min.js";
  js.onload = draw;
  document.body.appendChild(js);
})();
</script>"""
FRONT = '<div class=front-wrap><div class="hanzi main-hanzi">{{Hanzi}}</div></div>'


def blk(field, cls="notes meaning"):
    return f"{{{{#{field}}}}}<div class='{cls} blk'>{{{{{field}}}}}</div>{{{{/{field}}}}}"


def model(mid, name, fields, back_parts, strokes):
    import genanki
    back = '<div class="hanzi back-hanzi">{{Hanzi}}</div>\n' + "\n".join(back_parts) + ("\n" + STROKES if strokes else "")
    return genanki.Model(mid, name, fields=[{"name": f} for f in fields], css=CSS,
                         templates=[{"name": "Recognize", "qfmt": FRONT, "afmt": back}])


# no mp3 (public build): Anki speaks the Hanzi with the device's own Chinese voice
AUDIO = "{{#Audio}}<div>{{Audio}}</div>{{/Audio}}{{^Audio}}{{tts zh_CN:Hanzi}}{{/Audio}}"
EXAMPLE = "{{#Example}}<div class='ex blk'>{{Example}}</div><div class='sub blk'>{{ExampleEN}}</div>{{/Example}}"
CHAR_FIELDS = ["Hanzi", "Pinyin", "Meaning", "Audio", "Parts", "Radical", "Hint", "UsedIn", "Example", "ExampleEN", "Story"]
WORD_FIELDS = ["Hanzi", "Pinyin", "English", "Audio", "Chars", "Example", "ExampleEN", "SeenIn", "Source"]
PHRASE_FIELDS = ["Hanzi", "Pinyin", "English", "Surface", "Words", "Audio"]
SLANG_FIELDS = ["Hanzi", "Pinyin", "Meaning", "Literal", "Type", "Example", "ExampleEN", "Audio"]
DECKS = {"survival": (1790000000201, "中文::Survival", 0), "software": (1790000000202, "中文::Software", 100000),
         "slang": (1790000000203, "中文::Slang", 200000)}  # (deck id, name, due offset)


def models():
    return {
        "char": model(1790000000101, "ZH Char", CHAR_FIELDS,
                      [AUDIO, blk("Pinyin", "pinyin blk"), blk("Meaning"), blk("Parts"), blk("Radical", "sub"),
                       blk("Hint", "sub"), blk("Story", "story"), EXAMPLE, blk("UsedIn", "sub")], True),
        "word": model(1790000000102, "ZH Word", WORD_FIELDS,
                      [AUDIO, blk("Pinyin", "pinyin blk"), blk("English"), blk("Chars", "sub"), EXAMPLE,
                       blk("SeenIn", "sub")], True),
        "phrase": model(1790000000103, "ZH UI Phrase", PHRASE_FIELDS,
                        [AUDIO, blk("Pinyin", "pinyin blk"), blk("English"), blk("Words", "sub"), blk("Surface", "sub")],
                        False),
        "slang": model(1790000000104, "ZH Slang", SLANG_FIELDS,
                       [AUDIO, blk("Pinyin", "pinyin blk"), blk("Meaning"),
                        "{{#Literal}}<div class='sub blk'>literally: {{Literal}}</div>{{/Literal}}", EXAMPLE,
                        blk("Type", "sub")], False),
    }


def bold(sentence, w):
    return sentence.replace(w, f"<b>{w}</b>")


def sentence_pinyin(jieba, s):
    """'我们还没还钱。' -> 'wǒmen hái méi huán qián。' pypinyin reads in context; syllables grouped by jieba word."""
    from pypinyin import pinyin, Style
    syl = [x[0] for x in pinyin(s, style=Style.TONE, errors=lambda t: [[c] for c in t])]  # one item per character
    out, i = [], 0
    for tok in jieba.lcut(s):
        part = "".join(syl[i:i + len(tok)]); i += len(tok)
        out.append(part if CJK.search(tok) else part.strip())
    return re.sub(r" ([，。！？、：；）])", r"\1", " ".join(t for t in out if t))


def with_py(jieba, s, cls="py"):
    """Chinese line + its pinyin line underneath (the user is a beginner: pinyin everywhere)."""
    return f"{s}<div class={cls}>{sentence_pinyin(jieba, strip_html(s))}</div>" if s else ""


def build(args):
    import genanki
    MEDIA.mkdir(parents=True, exist_ok=True)
    state = collection_state()
    if state is None and not args.first_import:
        sys.exit("Anki/AnkiConnect is not reachable: start Anki so stories can be pulled first "
                 "(or pass --first-import for the very first build)")
    stories, mined = state or ({}, set())
    if args.public:  # a shared deck never carries this collection's stories or mined words
        stories, mined = {}, set()

    jieba = jieba_ready()
    phrases = brave_tier1(brave_locales(args.brave_dir))
    cedict, trad_only = load_cedict()
    ref = RefDeck()
    lex = Lexicon(cedict, ref)
    mmah = load_mmah()

    count = Counter(w for _, z, _ in phrases for w in words_of(jieba, z))
    first = {}
    for _, z, _ in phrases:
        for w in words_of(jieba, z):
            first.setdefault(w, len(first))
    ui_words = sorted(count, key=lambda w: (-count[w], first[w]))  # 打开 34, 页 21, 标签 20 ...
    freq_words = top_words(lex)
    from curated import ESCAPE  # the way back to English is learned first, wherever it lives
    ui_words = list(dict.fromkeys([z for _, z, _ in ESCAPE if z in set(ui_words) | set(freq_words)] + ui_words))
    merged, seq = sequence(ui_words, freq_words, phrases, jieba)
    check_order(seq, jieba)
    ui_set, freq_set = set(ui_words), set(freq_words)
    print(f"words: {len(ui_words)} UI, {len(freq_words)} frequency, {len(merged)} merged; "
          f"{sum(k == 'char' for k, _ in seq)} chars, {sum(k == 'phrase' for k, _ in seq)} phrases")
    print("  top UI words:", ui_words[:8])

    rank = {h: i for i, (_, h) in enumerate(seq)}
    index = {}
    for s in load_examples(jieba, trad_only):
        for t in s[2]:
            index.setdefault(t, []).append(s)
    seen_in = {}
    for e, z, surface in phrases:
        for w in set(words_of(jieba, z)):
            seen_in.setdefault(w, []).append((z, e))
    surface_of = {z: s for _, z, s in phrases}
    english_of = {z: e for e, z, _ in phrases}

    taken = {h for _, h in seq}
    software = software_items(taken)
    slang = slang_items(lex, jieba, taken | {z for _, z, _ in software})

    every = [h for _, h in seq] + [z for _, z, _ in software] + [r[0] for r in slang]
    if args.public:  # no third-party audio in a published deck (reference deck and TTS rights are unclear)
        audio = {h: "" for h in every}
    else:
        audio = {h: ref.audio(h) for h in every}
        tts = tts_all([h for h, a in audio.items() if not a], not args.no_tts)
        audio = {h: a or tts.get(h, "") for h, a in audio.items()}

    ms = models()
    decks = {k: genanki.Deck(i, n) for k, (i, n, _) in DECKS.items()}
    deck = decks["survival"]
    used_in = {}
    for w in merged:
        for c in set(w):
            if len(w) > 1:
                used_in.setdefault(c, []).append(w)
    skipped, n_ex, n_gloss_missing = [], 0, 0
    for pos, (kind, h) in enumerate(seq, 1):
        tags = [f"kind::{kind}"] + (["src::ui"] if h in ui_set else []) + (["src::freq"] if h in freq_set else [])
        if h in ref and ref[h]["hsk"]:
            tags.append(ref[h]["hsk"])
        snd = f"[sound:{audio[h]}]" if audio[h] else ""
        ex = best_example(h, rank, index) if kind != "phrase" and h in merged else None
        n_ex += bool(ex)
        exz, exe = (with_py(jieba, bold(ex[0], h)), ex[1]) if ex else ("", "")
        if kind == "char":
            meaning = lex.gloss(h, False) or mmah.get(h, {}).get("definition", "")
            n_gloss_missing += not meaning
            fields = [h, lex.pinyin(h), meaning, snd, parts(h, mmah, lex), mmah.get(h, {}).get("radical", ""),
                      hint(h, mmah), "、".join(f"{w} {lex.first_pinyin(w)}" for w in used_in.get(h, [])[:6]), exz, exe, stories.get(h, "")]
        elif kind == "word":
            if h in mined:
                skipped.append(h); continue
            gloss = lex.gloss(h)
            n_gloss_missing += not gloss
            chars = " · ".join(f"{c} {lex.first_pinyin(c)} {lex.short(c) or mmah.get(c, {}).get('definition', '')}"
                               for c in h if CJK.match(c))
            fields = [h, lex.pinyin(h), gloss, snd, chars, exz, exe, "<br>".join(f"{z} {sentence_pinyin(jieba, z)} ({e})" for z, e in seen_in.get(h, [])[:2]),
                      "brave" if h in ui_set else "wordfreq"]
        else:
            ws = words_of(jieba, h)
            fields = [h, " ".join(lex.first_pinyin(w) for w in ws), english_of[h], surface_of[h],
                      " · ".join(f"{w} {lex.first_pinyin(w)} {lex.short(w)}" for w in ws), snd]
            tags.append(f"surface::{surface_of[h]}")
        deck.add_note(genanki.Note(model=ms[kind], fields=fields, tags=tags, due=pos,
                                   guid=genanki.guid_for(kind, h)))
    def snd(h):
        return f"[sound:{audio[h]}]" if audio.get(h) else ""

    for pos, (en, z, platform) in enumerate(software, 1 + DECKS["software"][2]):
        ws = words_of(jieba, z)
        fields = [z, " ".join(lex.first_pinyin(w) for w in ws), en, platform + (" (unverified)" if platform == "iOS" else ""),
                  " · ".join(f"{w} {lex.first_pinyin(w)} {lex.short(w)}" for w in ws), snd(z)]
        tags = ["kind::software", f"platform::{platform.replace('/', '-')}"] + (["curated"] if platform == "iOS" else [])
        decks["software"].add_note(genanki.Note(model=ms["phrase"], fields=fields, tags=tags, due=pos,
                                                guid=genanki.guid_for("phrase", z)))
    for pos, (h, py, meaning, typ) in enumerate(slang, 1 + DECKS["slang"][2]):
        lit_src = h.split("——")[0]
        literal = " · ".join(f"{c} {lex.first_pinyin(c)} {lex.short(c)}" for c in lit_src if CJK.match(c))
        ex = best_example(h, rank, index)
        fields = [h, py, meaning, literal, typ, with_py(jieba, bold(ex[0], h)) if ex else "", ex[1] if ex else "", snd(h)]
        tags = ["kind::slang", "type::" + typ.split()[0]] + (["curated"] if "歇后语" in typ else [])
        decks["slang"].add_note(genanki.Note(model=ms["slang"], fields=fields, tags=tags, due=pos,
                                             guid=genanki.guid_for("slang", h)))
    pkg = genanki.Package(list(decks.values()))
    pkg.media_files = sorted({str(MEDIA / a) for a in audio.values() if a})
    out = BUILD / ("zh-public.apkg" if args.public else "zh.apkg")
    pkg.write_to_file(out)
    print(f"audio: {sum(bool(a) and not a.startswith('tts_') for a in audio.values())} reference, "
          f"{sum(a.startswith('tts_') for a in audio.values())} tts, {sum(not a for a in audio.values())} none")
    print(f"examples: {n_ex} notes; missing gloss: {n_gloss_missing}; skipped (already mined): {len(skipped)}")
    print(f"stories pulled from Anki: {len(stories)}")
    print(f"wrote {out} (" + ", ".join(f"{d.name}: {len(d.notes)}" for d in decks.values())
          + f" notes, {out.stat().st_size // 1024} KB)")
    print("import: File > Import, tick 'Merge note types', Update notes: 'If newer'")


# ---------------------------------------------------------------- Yomitan character dictionary (Decision 14)

def yomidict(args):
    """Yomitan format-3 kanji dictionary: hover a character to see its parts, hint and your story."""
    cedict, _ = load_cedict()
    lex = Lexicon(cedict, {})
    mmah = load_mmah()
    state = collection_state()
    stories = state[0] if state else {}
    rows = []
    for c, d in mmah.items():
        meanings = [m for m in (parts(c, mmah, lex), hint(c, mmah), stories.get(c) and f"story: {stories[c]}") if m]
        if meanings:
            rows.append([c, " ".join(d.get("pinyin", [])), "", "", meanings, {}])
    BUILD.mkdir(exist_ok=True)
    out = BUILD / "zh-parts.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.json", json.dumps({"title": "ZH Parts", "revision": f"{len(rows)}-{len(stories)}", "format": 3,
                                             "author": "chinese-default-migration",
                                             "description": "Make Me a Hanzi parts/hints (LGPL) + your Anki stories"}))
        z.writestr("kanji_bank_1.json", json.dumps(rows, ensure_ascii=False))
    print(f"wrote {out}: {len(rows)} characters, {len(stories)} stories. Import it in Yomitan > Dictionaries.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build build/zh.apkg")
    b.add_argument("--first-import", action="store_true", help="allow building without Anki running")
    b.add_argument("--no-tts", action="store_true", help="skip generating missing audio")
    b.add_argument("--public", action="store_true",
                   help="shareable build: no bundled mp3s (Anki's own TTS reads the cards) -> build/zh-public.apkg")
    b.add_argument("--brave-dir", help="Brave install dir containing locales/ (default: from PATH)")
    sub.add_parser("yomidict", help="build build/zh-parts.zip for Yomitan")
    args = ap.parse_args()
    {"build": build, "yomidict": yomidict}[args.cmd](args)


if __name__ == "__main__":
    main()
