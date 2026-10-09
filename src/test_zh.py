"""Plain-assert checks. Run: uv run src/test_zh.py  (needs cache/ from one build and build/zh.apkg)."""
import os, struct, tempfile
import zh


def test_pak():
    hdr = struct.pack("<IIHH", 5, 1, 2, 1) + struct.pack("<HIHIHI", 1, 34, 2, 36, 0, 38) + struct.pack("<HH", 3, 0)
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(hdr + b"hiyo")
    assert zh.read_pak(f.name) == {1: b"hi", 2: b"yo", 3: b"hi"}  # id 3 is an alias of entry 0
    os.unlink(f.name)


def test_marks():
    assert zh.marks("Zhong1 wen2") == "Zhōng wén"
    assert zh.marks("nu:3") == "nǚ"
    assert zh.marks("ma5") == "ma"
    assert zh.marks("m2") == "m"
    assert zh.marks("gou3") == "gǒu" and zh.marks("gui4") == "guì"


def test_lexicon():
    if not zh.REF_APKG.exists():
        return print("skip test_lexicon: reference deck not in assets/")
    lex = zh.Lexicon(zh.load_cedict()[0], zh.RefDeck())
    assert lex.pinyin("页") == "yè", lex.pinyin("页")
    assert lex.pinyin("的") == "de"
    assert lex.gloss("打").startswith("to hit"), lex.gloss("打")
    assert lex.ref.audio("搜索") == "hsk5_901.mp3"
    assert (zh.MEDIA / "hsk5_901.mp3").read_bytes()[:2] == b"\xff\xf3"


def test_media_map():
    if not zh.REF_APKG.exists():
        return print("skip test_media_map: reference deck not in assets/")
    ref = zh.RefDeck()
    assert {v: k for k, v in ref.name2idx.items()}["0"] == "hsk6_1039.mp3"


def test_order():
    jieba = zh.jieba_ready()
    assert "标签页" in zh.words_of(jieba, "在新标签页中打开链接")
    phrases = [("Open link in new tab", "在新标签页中打开链接", "ctxmenu")]
    merged, seq = zh.sequence(["打开", "链接"], ["的", "在", "新", "中", "标签页"], phrases, jieba)
    zh.check_order(seq, jieba)
    assert seq[0] == ("char", "打") and ("phrase", "在新标签页中打开链接") in seq


def test_reimport():
    """Second import of the same build adds nothing and keeps scheduling (FR-07, AC-02)."""
    from anki.collection import Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions
    apkg = str(zh.BUILD / "zh.apkg") if (zh.BUILD / "zh.apkg").exists() else str(zh.BUILD / "zh-public.apkg")
    with tempfile.TemporaryDirectory() as d:
        col = Collection(os.path.join(d, "collection.anki2"))
        opts = ImportAnkiPackageOptions(merge_notetypes=True, with_scheduling=False)
        first = col.import_anki_package(ImportAnkiPackageRequest(package_path=apkg, options=opts))
        assert len(first.log.new) > 1000
        cid = col.find_cards("Hanzi:打开")[0]
        from anki.scheduler.v3 import CardAnswer
        card = col.get_card(cid); card.start_timer()
        states = col._backend.get_scheduling_states(cid)
        col.sched.answer_card(col.sched.build_answer(card=card, states=states, rating=CardAnswer.GOOD))
        story_nid = col.find_notes('"note:ZH Char" Hanzi:打')[0]
        note = col.get_note(story_nid); note["Story"] = "hand + nail = hit"; col.update_note(note)
        second = col.import_anki_package(ImportAnkiPackageRequest(package_path=apkg, options=opts))
        assert len(second.log.new) == 0, len(second.log.new)
        assert col.get_card(cid).type != 0, "scheduling lost"
        assert col.db.scalar("select count() from revlog") == 1
        assert col.get_note(story_nid)["Story"] == "hand + nail = hit", "story overwritten"
        order = [col.get_card(c).note()["Hanzi"] for c in sorted(col.find_cards("is:new"), key=lambda c: col.get_card(c).due)]
        assert order[:3] == ["系", "统", "系统"], order[:3]  # way back to English first, characters before the word
        col.close()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
