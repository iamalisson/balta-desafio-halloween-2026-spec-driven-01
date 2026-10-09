# Plano técnico

Lógica de implementação do kit de sobrevivência para imersão em chinês. Números marcados como (verificado) foram medidos
na máquina de desenvolvimento (Brave 1.96.61, deck de referência `assets/HSK PT-BR NOV 2016.apkg`, 2026-10-08). Itens
marcados como NÃO VERIFICADO precisam ser conferidos à mão.

## Contexto

- O usuário está no HSK1, quer o chinês como idioma principal o quanto antes e abandona o Anki porque estudar "antes"
  de usar não motiva.
- Mudança de rumo (aceita): **o navegador é o currículo, o Anki só guarda o que o navegador ensina.** A interface do
  Brave passa para chinês no Dia 1. O Anki vira um kit de sobrevivência ordenado pelo que o usuário vê a toda hora, e
  palavras novas entram por mineração com 1 clique durante a navegação.
- Foco: memorizar caracteres e palavras com facilidade. Dois fatos guiam o design:
  - Caracteres atingem cobertura muito mais rápido que palavras: cerca de 940 caracteres cobrem 90% de um texto,
    enquanto as 1000 palavras mais frequentes cobrem só cerca de 62% dos tokens (wordfreq; 81,5% em legendas
    SUBTLEX). Os caracteres são ensinados como peças, logo antes da primeira palavra que os usa.
  - 62% de cobertura está muito abaixo dos 95-98% necessários para uma leitura confortável. Um dicionário popup e
    input graduado são obrigatórios desde o Dia 1, não opcionais.
- O verso dos cards é em inglês (decisão do usuário). Orçamento: 30+ min/dia.

## Arquitetura

```
Brave paks (en-US/zh-CN) ─┐
wordfreq top-N (zh)       ├─> src/zh.py build ─> build/zh.apkg ─> Anki (desktop + AnkiDroid via AnkiWeb)
CC-CEDICT (pinyin, EN)    │                                           ^
Make Me a Hanzi (peças)   │                                           │ AnkiConnect
manythings cmn-eng (fr.)  │   src/zh.py yomidict ─> build/zh-parts.zip ─> Yomitan (Brave) ─┘ cards minerados com 1 clique
deck HSK de referência (pinyin, mp3; opcional)
edge-tts (áudio alternativo, em cache)
```

- Um arquivo, `src/zh.py`, com dois subcomandos: `build` (os decks) e `yomidict` (dicionário popup de peças dos
  caracteres). Roda com `uv run`. Listas curadas ficam em `src/curated.py`. Testes: `src/test_zh.py` (asserts
  simples). Protótipos de investigação ficam em `specs/prototypes/`.
- Dependências: `genanki`, `jieba`, `wordfreq`, `edge-tts`, `babel`; só em desenvolvimento: `anki` (teste de
  reimportação). O resto usa a stdlib (gzip, zipfile, sqlite3, json, gettext, urllib, subprocess chamando o CLI `zstd`
  instalado).
- Downloads ficam em cache em `cache/` e a saída do build vai para `build/`. Os dois são ignorados pelo git.
- Não construído (ferramentas existentes já cobrem): CLI de mineração, minerador de histórico, SRS próprio, app de
  streak, dashboard, extensão própria de navegador. Mineração = [Yomitan](https://yomitan.wiki/) + AnkiConnect.
  Streak e estatísticas = as do próprio Anki.

## Decisões

**D-01. As strings do Brave vêm dos paks de localização, não de captura de tela.**
`locales/en-US.pak` e `zh-CN.pak` (pak v5, UTF-8) são alinhados por ID de recurso: 18544 IDs em comum, 17598 pares
utilizáveis (verificado). O caminho do pak é resolvido em tempo de execução a partir de `readlink -f $(which brave)`.
**Por quê:** são as traduções oficiais do Brave, então batem exatamente com o que o usuário vê na tela. O caminho é
resolvido em runtime porque, no NixOS, o caminho na store muda a cada atualização.

**D-02. Normalização.**
en: remove o mnemônico `&`, `&&` -> `&`, `…` -> `...`. zh: remove `(&X)` e `&` que sobrar. Descarta pares cujo zh ainda
tem uma palavra em inglês não traduzida, com whitelist para marcas e termos técnicos (Brave, JavaScript, PDF, URL,
Google).
**Por quê:** os mnemônicos de menu são ruído no card, e pares meio em inglês não ensinam chinês; já as marcas aparecem
assim mesmo na interface chinesa.

**D-03. Escopo da interface = só tier 1.**
Tier 1 = uma lista curada de seeds (cerca de 80 rótulos: menu de contexto, menu de aba, menu do app, botões de
diálogo, seções de configurações, nessa ordem) mais strings com mnemônico de menu. As regras de descarte valem para
*todas* as strings, seeds incluídas: mais de 6 palavras, plurais ICU e placeholders são descartados (por exemplo,
'Search Google for "$1"' sai, 'Open link in Brave private window' fica). Duplicatas como 'Downloads' são removidas.
O tier 2 (cerca de 7,7 mil rótulos curtos) não gera cards e só é alcançado por mineração.
**Por quê:** o tier 1 é o que o usuário vê toda hora; transformar 7,7 mil rótulos em cards seria a sobrecarga de
revisões que faz o usuário desistir. O limite de 6 palavras mantém rótulos reais de menu sem aceitar frases longas.

**D-04. Ensinar *palavras* da interface, não frases da interface.**
As frases do tier 1 são segmentadas com jieba (`add_word` para 标签页, 书签栏, 另存为, 搜索引擎, 扩展程序, 无痕式窗口).
Isso dá cerca de 230 palavras de interface, ranqueadas pela frequência nas frases do tier 1 (打开 34, 页 21, 标签 20,
窗口 16, 链接 13, 复制 11 ...). Cards de frase existem só para seeds com mais de uma palavra (30 cards; seeds de uma
palavra já são cards de palavra), e cada um vem depois de todas as suas palavras. As outras frases aparecem como
`SeenIn` nos cards das suas palavras.
**Por quê:** nenhuma de 复制, 打开, 链接, 书签, 窗口, 搜索, 设置, 下载 está no top-1000 do wordfreq (verificado), então
uma lista só de frequência não ensinaria a interface. Palavras se reaproveitam entre frases; frases inteiras não.

**D-05. Lista de frequência = wordfreq `top_n_list('zh')`, só Han, as primeiras 1000 que têm glosa no CC-CEDICT.**
Palavras sem entrada no CC-CEDICT (blocos de número+classificador como 两个 e 一天; 14 verificadas) são puladas, e a
lista é completada a partir do rank 1001.
**Por quê:** tem licença (CC BY-SA 4.0), mistura web, Twitter, Wikipedia e legendas, e é a que mais bate com o deck de
referência (731 de 1000, verificado). Sem glosa não há verso de card.

**D-06. Uma única sequência de aprendizado, peças antes do todo.**
As palavras são intercaladas como palavra de UI, palavra de frequência, palavra de UI, ... (1:1) até acabarem as de UI,
depois vêm as palavras de frequência restantes. Duplicatas são removidas (13 palavras de UI também estão no top:
确定, 管理, 编辑 ...). Uma **nota de caractere** é inserida logo antes da primeira palavra que traz um caractere novo.
Palavras de um único caractere são notas de caractere (levam Audio e Example), então nunca existe um card de caractere
e um card de palavra com o mesmo Hanzi. Uma frase seed vai logo depois da sua última palavra. As posições são gravadas
em `due` e todas as notas geradas ficam em um único deck, então o Anki segue a sequência (o importador de .apkg mantém
`due` como está, verificado). **A sequência é congelada na primeira importação:** o importador nunca renumera cards
existentes, então toda entrada de ordenação (palavras de UI, de frequência, caracteres, frases) precisa estar no
primeiro build importado. Builds seguintes só mudam campos. Uma nota adicionada depois vai para o fim da sequência
(due = máximo anterior + 1).
**Por quê:** a interface dá motivação imediata e a frequência dá cobertura; intercalar entrega as duas. Ensinar o
caractere antes da palavra transforma cada palavra nova em combinação de peças já conhecidas (CA-03).

**D-07. Os cards de caractere carregam o trabalho de memorização.**
Frente: 字. Verso: pinyin, decomposição do Make Me a Hanzi (ex.: 好 = ⿰女子), radical, dica etimológica (587 de 691
caracteres do top-1000 têm uma), as palavras que o usam e um campo **Story** vazio, que o usuário preenche no Anki.
**Por quê:** conteúdo de Heisig e do Hanzi Movie Method não pode ser redistribuído, e escrever a própria história é o
que faz o caractere fixar.

**D-08. Só reconhecimento na v1.**
Um template por tipo de nota: chinês na frente, inglês/pinyin/áudio no verso. Sem card de produção e sem card de
escuta. Reavaliar no mês 1.
**Por quê:** cada tipo extra adicionaria de 1,3 a 3x as revisões, e sobrecarga de revisões é o principal motivo de
abandono.

**D-09. Regra de origem do pinyin.**
Primeiro o campo `Pinyin` do deck de referência, que tem marcas de tom e usa a leitura certa (的 de, 页 yè). Sem o deck
(ele é opcional), ou para palavras fora dele: leituras do CC-CEDICT em minúsculas e com sentido real (não variant/
surname/used in), no máximo 2. Pinyin numerado é convertido para marcas de tom.
**Por quê:** 109 palavras do top-1000 são polifônicas e 82 têm um nome próprio como primeira entrada no CC-CEDICT
(verificado); pegar a primeira leitura ensinaria a pronúncia errada.

**D-10. Glosa em inglês = os 2-3 primeiros sentidos do CC-CEDICT.**
**Por quê:** o verso é em inglês (decisão do usuário) e o deck de referência é em português, então ele só fornece
pinyin e áudio.

**D-11. Áudio.**
Primeiro o mp3 do deck de referência (cerca de 731 de 1000 palavras, cerca de 2,4 KB cada, voz humana). Alternativa:
edge-tts `zh-CN-XiaoxiaoNeural`, em cache em `cache/tts/`. Falha de TTS é aviso, não erro. O media map do deck de
referência é zstd + protobuf `MediaEntry{name=1,size=2,sha1=3}`, e os arquivos numerados também são comprimidos com
zstd (verificado).
**Por quê:** voz humana é melhor para pegar tons; o TTS cobre o resto sem bloquear o build quando a rede falha.

**D-12. Exemplos.**
manythings `cmn-eng` (Tatoeba, CC-BY 2.0 FR): só frases em chinês simplificado com 12 caracteres ou menos. A palavra
alvo precisa aparecer como *token* do jieba (não como substring), e vence a frase com as palavras mais fáceis (menor
rank máximo entre seus tokens). Para palavras de UI, o exemplo é a própria frase do Brave.
**Por quê:** frases curtas e fáceis cabem no nível HSK1; casar por token evita falsos positivos (ex.: 上 dentro de 上网).

**D-13. Identidade estável.**
`guid_for(kind, hanzi)` com kind = tipo de nota: `char`, `word` (palavras de UI e de frequência juntas, então as 13
sobreposições mantêm um único GUID) e `phrase`. IDs de modelo e de deck são constantes fixas. Rebuild + reimportação
com **Update notes: If newer** atualiza campos e mantém o agendamento (verificado). As histórias vivem no Anki, então
todo build primeiro puxa os campos Story via AnkiConnect e os grava de volta nas notas novas. Se o AnkiConnect estiver
inacessível e já existir uma importação anterior, o build se recusa a gravar o .apkg (`--first-import` libera isso só
no primeiro build). Antes de gravar, o build também pergunta ao AnkiConnect por qualquer Hanzi já presente com outro
GUID (um card minerado) e pula essa palavra, então a nota minerada sempre vence e não há duplicata.
**Por quê:** sem GUID estável, cada rebuild criaria notas novas e apagaria o progresso; sem puxar as histórias, um
rebuild sobrescreveria o que o usuário escreveu.

**D-14. Mineração = Yomitan + CC-CEDICT + AnkiConnect, zero código próprio.**
Shift + passar o mouse sobre qualquer palavra, 1 clique cria um card em `**********Yomitan**********` com a frase (sem
URL, ver Riscos). Para os caracteres também terem popup, `yomidict` gera um dicionário kanji no formato 3 do Yomitan a
partir do Make Me a Hanzi (decomposição, dica) mais as histórias do usuário.
**Por quê:** ferramentas maduras já fazem a mineração; o único buraco é que o dicionário Hanzi padrão do CC-CEDICT não
tem componentes (verificado).

**D-15. Opções do deck.**
FSRS ligado (para toda a coleção), retenção desejada 0,90, learning steps 1m 10m, **15 novos/dia**, **máximo 150
revisões/dia**, bury siblings, gather order Ascending position dentro de `中文::Survival`. O mesmo preset vale para
`**********Yomitan**********` (criado em 2026-10-08 via AnkiConnect, hoje no Default), aplicado com "Save to all
subdecks" e estudado primeiro a cada dia. Regra de carga: se as revisões ficarem acima de 120/dia por 3 dias, os novos
caem para 8.
**Por quê:** o limite de novos e a regra das 120 revisões são as defesas contra sobrecarga, o gatilho clássico de
abandono. Ascending position preserva a sequência da D-06.

**D-16. Celular.**
AnkiDroid + sincronização AnkiWeb, para revisar em tempo morto.
**Por quê:** é a maior alavanca de constância.

**D-17. Licenciamento.**
O deck completo (`build/zh.apkg`) é para uso pessoal e não é publicado: os direitos dos mp3 de referência e do áudio
do edge-tts não são claros, e CC-CEDICT e wordfreq são BY-SA. O README traz os CREDITS. Para compartilhar existe o
build público (`--public`, ver Contratos), sem mp3 empacotado.
**Por quê:** respeitar licenças sem impedir que o projeto seja usado por outras pessoas.

## Modelo de dados

Um tipo de nota por tipo de conteúdo, todos com ID de modelo fixo. O CSS reaproveita a classe `.pequeno` do deck de
referência para linhas secundárias.

| Tipo de nota | Campos (primeiro = chave de ordenação/duplicata) | Frente | Verso |
|---|---|---|---|
| ZH Char | Hanzi, Pinyin, Meaning, Audio, Parts, Radical, Hint, UsedIn, Example, ExampleEN, Story | Hanzi | Pinyin, Audio, Meaning, Parts, Radical, Hint, **Story**, Example, UsedIn + animação dos traços |
| ZH Word | Hanzi, Pinyin, English, Audio, Chars, Example, ExampleEN, SeenIn, Source | Hanzi | Pinyin, Audio, English, Chars (significado por caractere), Example, SeenIn + animação dos traços |
| ZH UI Phrase (seeds do Brave + deck Software) | Hanzi, Pinyin, English, Surface, Words, Audio | Hanzi (como aparece na tela) | English, Pinyin, decomposição em Words, Surface (plataforma) |
| ZH Slang | Hanzi, Pinyin, Meaning, Literal, Type, Example, ExampleEN, Audio | Hanzi | Pinyin, Audio, Meaning, "literally: ...", Example, Type |

Cards minerados vão para `**********Yomitan**********` (já criado no Anki) e usam o tipo de nota **Yomitan Hanzi**,
criado em 2026-10-08 via AnkiConnect (script: `specs/prototypes/anki-build/mk_model.py`). É uma cópia separada do
**Hanzi Writing** de `assets/_____MOST COMMON 3000 HANZI_____.apkg`: mesmos campos, CSS e fonte Kai
(`_FandolKai-Regular.otf`), mais um campo **Story**. As linhas HSK, rank, Traditional e Pinyin 2 ficam ocultas quando
vazias, e há suporte a modo noturno. O verso também toca uma **animação em loop da ordem dos traços** de cada
caractere, com radicais em azul (hanzi-writer 3.7.2 via jsDelivr, a mesma ideia de
`assets/___CHINESE PRACTICE VOCABULARY___...apkg`). Ela precisa de internet durante a revisão; offline, a animação é
pulada e o card continua funcionando. Os dados de traços têm licença Arphic, o que é aceitável para uso pessoal.

Mapeamento do Yomitan:

| Campo | Marcador do Yomitan |
|---|---|
| Hanzi (primeiro campo, chave de duplicata) | {expression} |
| Pinyin | {reading} |
| Meaning | {glossary-brief} |
| Example Words | {sentence} |
| Words Bold | {cloze-prefix}<span class=examplehanzi>{cloze-body}</span>{cloze-suffix} |
| Zein Definition | {glossary} |
| Audio | {audio} |
| Notes | `yomitan` (texto fixo, nunca {url}) |
| FrequencyRank | {frequency-harmonic-rank} (só se houver um dicionário de frequência instalado no Yomitan; senão vazio) |
| Pinyin 2, Traditional, HSK | vazio |
| Story | vazio (o usuário escreve o mnemônico no Anki) |

A checagem de duplicata do Yomitan roda no primeiro campo (Hanzi). Com escopo "collection", ela também marca os 2996
caracteres do deck 3000-Hanzi, que usa outro tipo de nota (NÃO VERIFICADO: conferir no primeiro card minerado). Os dois
tipos de nota são separados, então mudar o Yomitan Hanzi nunca afeta o deck 3000-Hanzi. A mineração só deve começar
depois da primeira importação, para o build enxergar as notas mineradas e pulá-las (D-13).

Decks: `**********Yomitan**********` (minerados, estudado primeiro, limitado pela regra de 5 minerações por sessão),
`中文::Survival` (caracteres + palavras + frases de UI, uma sequência), `中文::Software` e `中文::Slang`. Os "dois decks"
da spec (navegador e palavras frequentes) viram **tags** (`src::ui`, `src::freq`, `kind::char|word|phrase`,
`surface::ctxmenu|tabmenu|appmenu|dialog|settings`, `hsk1`..`hsk6`), para que um filtered deck ou o navegador do Anki
possa separá-los sem quebrar a ordem.

Tamanhos (build de 2026-10-08): Survival 1638 notas (783 de caractere + 825 de palavra + 30 de frase), Software cerca
de 305, Slang 729; 2672 cards, 23 MB com áudio. Com 8/4/3 novos por dia: Survival cerca de 7 meses, Software cerca de
2,5 meses, Slang cerca de 8 meses.

## Contratos

- `uv run src/zh.py build [--brave-dir DIR] [--no-tts] [--first-import]`
  - Lê os paks, o deck de referência (se existir) e as fontes em cache (baixa uma vez se faltarem).
  - Grava `build/zh.apkg` e imprime contagens: pares, frases do tier 1, palavras de UI, palavras de frequência,
    caracteres, áudio referência/TTS/nenhum, exemplos, seeds sem correspondência.
  - Antes de montar, puxa os campos Story e a lista de Hanzi existentes via AnkiConnect (localhost:8765). Se o
    AnkiConnect estiver inacessível, sai com código 1, a menos que `--first-import` seja passado (D-13).
  - Códigos de saída: 1 se os paks ou uma fonte obrigatória (CC-CEDICT, Make Me a Hanzi) faltar e não puder ser
    baixada. TTS e exemplos são só avisos.
  - O deck HSK de referência em `assets/` é opcional (não está no repositório público): sem ele, o pinyin vem do
    CC-CEDICT (D-09) e o áudio do TTS (D-11).
- `uv run src/zh.py build --public` grava `build/zh-public.apkg` sem nenhum mp3 empacotado (o áudio do deck HSK de
  referência e o do edge-tts têm direitos de redistribuição incertos). Os templates dos cards caem para o TTS embutido
  do Anki, `{{tts zh_CN:Hanzi}}`. O build público também ignora as histórias e as palavras mineradas do usuário (não
  consulta o AnkiConnect).
- `uv run src/zh.py yomidict` grava `build/zh-parts.zip` (formato 3 de dicionário do Yomitan, kanji_bank). O usuário
  importa uma vez no Yomitan e reimporta depois de escrever histórias.
- Importação no Anki: File > Import, marcar **Merge note types**, Update notes: **If newer**.
- Asserts em `src/test_zh.py`:
  - parser de pak sobre um pak v5 sintético com alias
  - `marks('Zhong1 wen2')=='Zhōng wén'`
  - `pinyin('页')=='yè'`, `pinyin('的')=='de'`
  - entrada 0 do media_map == `hsk6_1039.mp3`
  - o jieba mantém 标签页 inteiro
  - Hanzi único por tipo de nota
  - toda frase vem depois de todas as suas palavras, e toda palavra depois de todos os seus caracteres
  - reimportação via backend `anki` (dependência de dev) dá new=0, mantém o agendamento e mantém uma Story puxada

## Riscos

- **A troca de idioma do Brave no NixOS está NÃO VERIFICADA** (o teste headless travou). Ordem de tentativas:
  1. `LANGUAGE=zh_CN brave`
  2. `brave --lang=zh-CN`
  3. locale zh_CN na sessão, o que exige `i18n.extraLocales = ["zh_CN.UTF-8/UTF-8"]`; hoje o `locale -a` não o lista

  Feche o Brave por completo antes (`pkill -x brave`, confira que `pgrep -x brave` volta vazio, desligue "continuar
  executando apps em segundo plano"). Existem dois lançadores: `brave-browser.desktop` e `com.brave.Browser.desktop`.
  Sobrescreva **todas** as linhas `Exec=` dos dois, senão uma entrada abre em inglês sem avisar.
- Sobrecarga de revisões é o gatilho clássico de abandono. O limite de novos/dia e a regra das 120 revisões são as
  configurações mais importantes.
- Páginas web nativas continuam difíceis por meses (62% de cobertura). Input graduado (Du Chinese, Mandarin Companion,
  parcialmente pagos, planos gratuitos NÃO VERIFICADOS) evita a sensação de "estou falhando".
- Os IDs dos paks do Brave são gerados no build do Brave, então os seeds usam o texto em inglês como chave. Um rótulo
  renomeado some sem aviso, por isso o build imprime os seeds sem correspondência a cada execução.
- Algumas strings zh do Brave são estranhas ou misturam inglês (`Edit` -> 修改). Há filtro, mas espere alguns cards
  esquisitos.
- A saída `{reading}`/`{audio}` do Yomitan para chinês está NÃO VERIFICADA (marcas de tom vs números, áudio vazio).
  Conferir no primeiro card minerado.
- Gather order "Deck" com posição ascendente dentro de cada deck, e o comportamento da importação pela interface, foram
  verificados só com o backend `anki` 26.9.3, não no desktop 25.09.4 (NÃO VERIFICADO na interface gráfica).
- Privacidade: cards minerados guardam frases de páginas, e a sincronização com o AnkiWeb as envia. URLs nunca são
  guardadas (Source é texto fixo). As frases são aceitas como conteúdo pessoal de estudo. Não minere em páginas
  privadas (e-mail, banco).
- Mineração baseada no histórico foi adiada: hoje só existem 6 visitas a páginas zh-CN (verificado). Reavaliar no mês 1
  se mais de 30% da navegação for em chinês.
