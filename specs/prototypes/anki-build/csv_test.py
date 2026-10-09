from anki.collection import Collection
col = Collection("csvcol/collection.anki2")
n = col.new_note(col.models.by_name("Basic")); n["Front"]="existing"; col.add_note(n,1)
for i in range(2):
    md = col.get_csv_metadata(path="t.tsv", delimiter=None)
    r = col.import_csv(col._backend.ImportCsvRequest(path="t.tsv", metadata=md)) if False else col.import_csv(__import__('anki.import_export_pb2',fromlist=['x']).ImportCsvRequest(path="t.tsv", metadata=md))
    print("run",i,"new",len(r.log.new),"updated",len(r.log.updated),"dupe",len(r.log.duplicate))
for cid in col.find_cards("deck:中文*"):
    c=col.get_card(cid); print(col.decks.name(c.did), c.note()["Front"], "due", c.due, c.note().guid)
