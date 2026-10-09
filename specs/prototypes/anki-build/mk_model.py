import json, urllib.request
def q(action, **params):
    r = json.load(urllib.request.urlopen("http://localhost:8765", json.dumps({"action": action, "version": 6, "params": params}).encode()))
    if r["error"]: raise SystemExit(f"{action}: {r['error']}")
    return r["result"]

css = (q("modelStyling", modelName="Hanzi Writing")["css"] + "\n.story{ font-size: 16px; color: #2a6; }\n.nightMode .card{ color: white; background-color: #222; }\n"
       ".front-wrap{ min-height: 80vh; display: flex; flex-direction: column; justify-content: center; align-items: center; }\n"
       ".main-hanzi{ font-size: 110px; line-height: 1.2; }\n.back-hanzi{ font-size: 72px; }\n"
       ".blk{ margin: 6px 0; }\n.meaning{ color: black; text-align: center; }\n.nightMode .meaning{ color: white; }\n"
       # Block centered on the card, lines inside left-aligned (overrides Yomitan's inline text-align).
       ".meaning > *{ display: inline-block; max-width: 90%; text-align: left !important; }\n"
       ".meaning *{ text-align: left !important; }\n"
       ".meaning ol, .meaning ul{ margin: 0; padding-left: 1.4em; }\n"
       ".nightMode .meaning *{ color: white !important; }\n")
front = """{{#HSK}}<div class=notes style='color:gray'>HSK:{{HSK}}{{#FrequencyRank}} | #{{FrequencyRank}}{{/FrequencyRank}}</div>{{/HSK}}
{{^HSK}}{{#FrequencyRank}}<div class=notes style='color:gray'>#{{FrequencyRank}}</div>{{/FrequencyRank}}{{/HSK}}
<div class=front-wrap><div class="hanzi main-hanzi">{{Hanzi}}</div>
{{#Traditional}}<a class=hanzi style='color:gray;' href='http://www.mdbg.net/chindict/chindict.php?page=chardict&cdcanoce=1&cdqchi={{Traditional}}'>{{Traditional}}</a>{{/Traditional}}
</div>
"""
back = """{{#HSK}}<div class=notes style='color:gray'>HSK:{{HSK}}{{#FrequencyRank}} | #{{FrequencyRank}}{{/FrequencyRank}}</div>{{/HSK}}
{{^HSK}}{{#FrequencyRank}}<div class=notes style='color:gray'>#{{FrequencyRank}}</div>{{/FrequencyRank}}{{/HSK}}
<div class="hanzi back-hanzi">{{Hanzi}}</div>
{{#Traditional}}<a class=hanzi style='color:gray;' href='http://www.mdbg.net/chindict/chindict.php?page=chardict&cdcanoce=1&cdqchi={{Traditional}}'>{{Traditional}}</a>{{/Traditional}}
{{#Audio}}<div>{{Audio}}</div>{{/Audio}}
<div class='pinyin blk'>{{Pinyin}}</div>
{{#Pinyin 2}}<div class='pinyin2 blk'>{{Pinyin 2}}</div>{{/Pinyin 2}}
{{#Words Bold}}<div class='hanzi blk'>{{Words Bold}}</div>{{/Words Bold}}
{{#Meaning}}<div class='notes meaning blk'>{{Meaning}}</div>{{/Meaning}}
{{#Zein Definition}}<div class='notes meaning blk'>{{Zein Definition}}</div>{{/Zein Definition}}
{{#Story}}<div class='story blk'>{{Story}}</div>{{/Story}}
<div id=hz-src style="display:none">{{text:Hanzi}}</div>
<div id=hz-target></div>
<script>
(function () {
  // Stroke-order animation (hanzi-writer, loaded from jsDelivr: needs internet, silently skipped offline).
  var chars = (document.getElementById("hz-src").textContent.match(/[\u3400-\u9fff]/g) || []);
  var target = document.getElementById("hz-target");
  var night = document.body.classList.contains("nightMode") || document.documentElement.classList.contains("night-mode");
  function draw() {
    target.innerHTML = "";
    chars.forEach(function (c) {
      HanziWriter.create(target, c, {
        width: 90, height: 90, padding: 5, showOutline: true,
        strokeColor: night ? "#ffffff" : "#333333", outlineColor: night ? "#555555" : "#dddddd",
        radicalColor: "#337ab7", delayBetweenStrokes: 150, strokeAnimationSpeed: 1
      }).loopCharacterAnimation();
    });
  }
  if (window.HanziWriter) { draw(); return; }
  var js = document.createElement("script");
  js.src = "https://cdn.jsdelivr.net/npm/hanzi-writer@3.7.2/dist/hanzi-writer.min.js";
  js.onload = draw;
  document.body.appendChild(js);
})();
</script>
"""
fields = q("modelFieldNames", modelName="Hanzi Writing") + ["Story"]
if "Yomitan Hanzi" in q("modelNames"):
    q("updateModelTemplates", model={"name": "Yomitan Hanzi", "templates": {"Card 1": {"Front": front, "Back": back}}})
    q("updateModelStyling", model={"name": "Yomitan Hanzi", "css": css})
else:
    q("createModel", modelName="Yomitan Hanzi", inOrderFields=fields, css=css, isCloze=False,
      cardTemplates=[{"Name": "Card 1", "Front": front, "Back": back}])
print(q("modelFieldNames", modelName="Yomitan Hanzi"))
note = {"deckName": "**********Yomitan**********", "modelName": "Yomitan Hanzi", "fields": {"Hanzi": "打开", "Pinyin": "dǎkāi"}}
print(q("canAddNotesWithErrorDetail", notes=[note]))
