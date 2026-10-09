"""Minimal Chromium .pak (v5) reader + en/zh alignment + tiering prototype.

usage: python3 -I pak.py <en-US.pak> <zh-CN.pak> [out.tsv]
"""
import re, struct, sys


def read_pak(path):
    """-> {resource_id: bytes}. v5 header: u32 version, u32 encoding, u16 n_res, u16 n_alias;
    then (n_res+1) x (u16 id, u32 offset) [last = sentinel]; then n_alias x (u16 id, u16 entry_index)."""
    b = open(path, "rb").read()
    ver, enc, n, na = struct.unpack_from("<IIHH", b, 0)
    assert ver == 5, f"{path}: pak version {ver}, only 5 supported"
    assert enc == 1, f"{path}: encoding {enc} (1=UTF-8)"
    ents = [struct.unpack_from("<HI", b, 12 + 6 * i) for i in range(n + 1)]
    out = {ents[i][0]: b[ents[i][1]:ents[i + 1][1]] for i in range(n)}
    pos = 12 + 6 * (n + 1)
    for i in range(na):  # aliases: duplicate strings share one entry
        aid, idx = struct.unpack_from("<HH", b, pos + 4 * i)
        out[aid] = b[ents[idx][1]:ents[idx + 1][1]]
    return out


def texts(path):
    return {k: v.decode("utf-8", "replace") for k, v in read_pak(path).items()}


PH = re.compile(r"\$\d|<ph\b|\{[A-Za-z_0-9]+[,}]|<[a-z]+[ >/]")   # $1, <ph>, ICU {X, plural / {NAME}, html
ICU = re.compile(r"\{[A-Za-z_0-9]+,\s*(plural|select)")
CJK = re.compile(r"[一-鿿]")

# ponytail: curated English seeds matched by exact text; pak has no resource names, so IDs are found by label.
SEED = """Back|Forward|Reload|Copy|Paste|Cut|Undo|Redo|Select all|Delete|Open link in new tab|Open link in new window
Open link in incognito window|Open link in private window|Copy link address|Save link as...|Save image as...|Copy image
Copy image address|Open image in new tab|Save as...|Print...|Inspect|View page source|Translate to English
New tab|New window|New private window|New incognito window|History|Downloads|Bookmarks|Settings|Zoom|Find...|Find and edit
Exit|Help|Close tab|Close tabs to the right|Close other tabs|Reopen closed tab|Duplicate|Pin|Unpin|Mute site|Unmute site
Add tab to group|Move tab to new window|Bookmark all tabs...|Search|Search the web|Address and search bar|Bookmark this tab
Bookmark this tab...|Extensions|More tools|Full screen|Passwords|Appearance|Privacy and security|Search engine|Default browser
On startup|Languages|System|Reset settings|About Brave|Get started|Shields|Wallet|Rewards|Sync|Cancel|OK|Done|Save|Open|Close
Allow|Block|Clear browsing data|Show all|Edit|Remove|Rename|Add|Name|Folder|Address|Yes|No|Continue|Retry|Not now|Clear
Show in folder|Open when done|Downloads|Recently closed|Bookmark manager|Show bookmarks bar|Other bookmarks|Add page...
Add folder...|Cast...|Developer tools|Task manager|Show all downloads|Search Google for “$1”|Manage|Learn more|Send feedback""".replace("\n", "|").split("|")


MNEMONIC = re.compile(r"&(?=[^&\s])")  # "&Copy" = Views/GTK menu accelerator => it IS a menu item
SEED_N = {s.lower() for s in SEED}


def norm_en(e):
    return MNEMONIC.sub("", e).replace("&&", "&").replace("\u2026", "...").strip()


def norm_zh(z):
    return re.sub(r"\(&\w\)", "", z).replace("&", "").strip()


def tier(raw_en):
    en = norm_en(raw_en)
    if en.lower() in SEED_N or (MNEMONIC.search(raw_en) and not PH.search(en)):
        return 1
    if PH.search(en) or len(en) > 40 or len(en.split()) > 5:
        return 3
    return 2


def main(en_pak, zh_pak, out=None):
    en, zh = texts(en_pak), texts(zh_pak)
    pairs = {k: (en[k], zh[k]) for k in en.keys() & zh.keys()
             if en[k].strip() and CJK.search(zh[k]) and en[k] != zh[k]}
    print(f"en ids={len(en)} zh ids={len(zh)} common={len(en.keys() & zh.keys())} aligned(zh has CJK, differs)={len(pairs)}")
    print("placeholders:", sum(bool(PH.search(e)) for e, _ in pairs.values()),
          "icu plural/select:", sum(bool(ICU.search(e)) for e, _ in pairs.values()),
          "long(>5 words or >40ch):", sum(len(e) > 40 or len(e.split()) > 5 for e, _ in pairs.values()))
    tiers = {1: [], 2: [], 3: []}
    for k, (e, z) in sorted(pairs.items()):
        tiers[tier(e)].append((k, norm_en(e), norm_zh(z)))
    print("tier sizes:", {t: len(v) for t, v in tiers.items()},
          "tier1 unique en:", len({e for _, e, _ in tiers[1]}), "tier2 unique en:", len({e for _, e, _ in tiers[2]}))
    print("seeds not found:", sorted(SEED_N - {e.lower() for _, e, _ in tiers[1]}))
    if out:
        seen, rows = set(), []
        seeded = sorted(tiers[1], key=lambda r: (r[1].lower() not in SEED_N, r[0]))  # seeds first
        for k, e, z in seeded:  # dedupe same en->zh, keep first id
            if (e, z) not in seen:
                seen.add((e, z)); rows.append(f"{k}\t{e}\t{z}")
        open(out, "w").write("id\ten\tzh\n" + "\n".join(rows[:50]) + "\n")


if __name__ == "__main__":
    # self-check on a synthetic v5 pak: 2 entries + 1 alias
    import tempfile, os
    body = b"hiyo"
    hdr = struct.pack("<IIHH", 5, 1, 2, 1) + struct.pack("<HIHIHI", 1, 34, 2, 36, 0, 38) + struct.pack("<HH", 3, 0)
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(hdr + body)
    assert read_pak(f.name) == {1: b"hi", 2: b"yo", 3: b"hi"}; os.unlink(f.name)
    if len(sys.argv) >= 3:
        main(*sys.argv[1:4])
