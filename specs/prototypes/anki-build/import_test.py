import sys
from anki.collection import Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions
col = Collection(sys.argv[1] + "/collection.anki2")
# pre-existing new card to see where imported due positions land
m = col.models.by_name("Basic"); n = col.new_note(m); n["Front"] = "existing"; col.add_note(n, 1)
def show(tag):
    print("--", tag)
    for cid in col.find_cards("deck:中文*"):
        c = col.get_card(cid); n = c.note()
        print(col.decks.name(c.did), c.template()["name"], n["Hanzi"], n["English"], "due", c.due, "type", c.type, n.tags)
    print("notes", col.note_count(), "cards", col.card_count(), "media files", sorted(col.media.dir() and __import__('os').listdir(col.media.dir())))
for f in sys.argv[2:]:
    o = ImportAnkiPackageOptions(with_scheduling=False, merge_notetypes=True)
    r = col.import_anki_package(ImportAnkiPackageRequest(package_path=f, options=o))
    print(f, "new", len(r.log.new), "updated", len(r.log.updated), "dupe", len(r.log.duplicate), "first_field_match", len(r.log.first_field_match))
    show(f)
# scheduler order
col.decks.select(col.decks.id_for_name("中文"))
q = col.sched.get_queued_cards(fetch_limit=20)
print("queue order:", [col.get_card(c.card.id).note()["Hanzi"] + "/" + col.get_card(c.card.id).template()["name"] for c in q.cards])
col.close()
