import sys
from anki.collection import Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions
col = Collection("testcol/collection.anki2")
print("existing basic card due:", [col.get_card(c).due for c in col.find_cards("existing")])
cid = col.find_cards("Hanzi:复制")[0]; c = col.get_card(cid)

c = col.get_card(cid); n = c.note(); 
print("before:", c.type, c.queue, c.due, n["Mnemonic"])
o = ImportAnkiPackageOptions(with_scheduling=False, merge_notetypes=True)
r = col.import_anki_package(ImportAnkiPackageRequest(package_path="v4.apkg", options=o))
print("updated", len(r.log.updated), "dupe", len(r.log.duplicate))
c = col.get_card(cid); print("after:", c.type, c.queue, c.due, c.note()["Mnemonic"], "revlog", col.db.scalar("select count() from revlog"))
col.close()
