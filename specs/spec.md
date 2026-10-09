# Chinês como idioma padrão (chinese-default-migration)

## Problema

Uma pessoa no nível HSK1 quer passar a usar o chinês como idioma principal o quanto antes: no navegador, no
computador e nos celulares. Ela já tentou estudar com flashcards, mas não mantém a constância. Estudar "antes" para
só depois usar o idioma não motiva, e as listas de vocabulário genéricas não têm relação com o que ela vê no dia a dia.

## Objetivo

A pessoa vive em chinês desde o primeiro dia. As interfaces que ela usa todos os dias passam a ser o currículo, e
o estudo diário vira um "kit de sobrevivência" curto que ensina exatamente o que ela vê, sempre das partes para o
todo (caractere, depois palavra, depois frase). Meta: até o fim do ano, navegador, computador e celulares em chinês.

## Usuários

- Quem está aprendendo chinês do zero ou no nível HSK1 e quer imersão pelas próprias telas.
- Quem já usa um app de flashcards com repetição espaçada e quer conteúdo ligado ao uso real.

## Histórias

- H-01 Como iniciante, quero trocar o navegador para chinês no primeiro dia sem ficar perdido, porque os menus que
  mais uso são os primeiros que aprendo.
- H-02 Como iniciante, quero decorar caracteres com facilidade: ver de quais partes cada um é feito, como se escreve
  e criar minha própria história para lembrar dele.
- H-03 Como iniciante, quero pinyin em todo texto chinês que aparece no estudo, porque ainda não consigo ler sem ele.
- H-04 Como iniciante, quero transformar em card, com um clique, qualquer palavra desconhecida que eu encontrar
  navegando.
- H-05 Como pessoa que vai trocar o idioma do computador e dos celulares, quero aprender primeiro o caminho de volta
  para o inglês em cada aparelho, para que a troca nunca vire uma armadilha.
- H-06 Como quem consome conteúdo da internet chinesa, quero entender gírias e expressões cujo sentido literal não
  faz sentido (o equivalente a "estar nas nuvens").

## Requisitos funcionais

- RF-01 Os textos do navegador vêm das traduções oficiais do próprio navegador, para bater exatamente com o que
  aparece na tela.
- RF-02 Os textos do navegador são ordenados pelo uso real: menu do botão direito, menu de abas, menu principal,
  diálogos e configurações. Só os cerca de 200 rótulos mais vistos viram estudo; o resto é aprendido sob demanda.
- RF-03 As frases da interface são quebradas em palavras, e as palavras são estudadas antes das frases que as contêm.
- RF-04 As cerca de 1000 palavras mais frequentes do chinês moderno entram com pinyin, significado em inglês, áudio e
  uma frase de exemplo curta.
- RF-05 Cada caractere novo tem o próprio card (partes, radical, dica de origem, campo para a história pessoal e
  animação da ordem dos traços), logo antes da primeira palavra que o usa.
- RF-06 Todo card tem áudio da pronúncia.
- RF-07 Gerar o baralho de novo nunca duplica cards e nunca apaga o histórico de revisões nem as histórias escritas
  pela pessoa.
- RF-08 Uma palavra encontrada em qualquer página vira card com um clique, e passar o mouse sobre um caractere mostra
  as partes dele.
- RF-09 Um baralho de software ensina os rótulos de configuração de Linux, Android e iPhone, além de datas e horas,
  para que computador e celulares possam ser trocados para chinês com segurança.
- RF-10 O caminho de volta para o inglês em cada aparelho é a primeira coisa estudada, antes de qualquer troca.
- RF-11 Um baralho de gírias ensina gírias da internet, expressões idiomáticas de quatro caracteres e ditados de duas
  partes, cada um com o sentido literal palavra por palavra ao lado do sentido real.
- RF-12 Cada caractere ou palavra existe em um único card em todos os baralhos.
- RF-13 Todo texto chinês exibido no estudo (exemplos, listas de palavras, decomposições) vem acompanhado de pinyin.

## Regras de negócio

- RN-01 O verso dos cards é em inglês.
- RN-02 Só o sentido de reconhecimento (chinês para significado) na primeira versão; produção fica para depois.
- RN-03 Três baralhos estudados em paralelo, com limite diário somado: sobrevivência 8, software 4, gírias 3 cards
  novos por dia (15 no total).
- RN-04 Uso pessoal: conteúdo de terceiros com direitos incertos (áudio de outros baralhos) nunca vai para uma versão
  publicada. A versão publicada usa só fontes de licença aberta e a voz do próprio aparelho para o áudio.
- RN-05 Nada do histórico de navegação é lido ou guardado. Cards criados ao navegar guardam a frase, nunca o endereço
  da página.
- RN-06 Dia mínimo: 5 revisões e 1 consulta. Nunca falhar dois dias seguidos; depois de uma pausa, zero cards novos
  até a fila de revisões cair abaixo de 50.

## Casos de borda

- Uma palavra tem várias leituras (长 cháng/zhǎng, 还 hái/huán): vale a leitura mais comum, e a frase de exemplo usa a
  leitura do contexto.
- Uma palavra frequente não existe no dicionário (两个, 一天): fica de fora e a lista é completada com a próxima.
- Um rótulo da interface aparece traduzido de formas diferentes: vale a tradução mais frequente.
- Um rótulo mantém palavras em inglês (Brave, PDF, Wi-Fi/WLAN): só nomes de marca e siglas técnicas são aceitos.
- Uma gíria é também uma palavra comum (开车 = dirigir / gíria): o card mostra os dois sentidos.
- A pessoa já criou um card de uma palavra ao navegar: o baralho gerado não cria outro.
- O aparelho fica sem internet: a animação dos traços some, o resto do card funciona.
- Não existe tradução aberta de um sistema (iPhone): a lista é curada à mão e marcada como "a verificar".

## Fora de escopo

Cards de produção (inglês para chinês), cards só de áudio, leitura do histórico de navegação, extensões próprias de
navegador, apps de sequência ou painel de estatísticas, caracteres tradicionais.

## Critérios de aceite

- CA-01 O navegador abre em chinês por qualquer atalho depois de sair e entrar de novo na sessão.
- CA-02 O baralho gerado importa sem duplicatas, e uma segunda importação acrescenta 0 cards.
- CA-03 No baralho de sobrevivência, nenhum card mostra uma frase antes das palavras dela, nem uma palavra antes dos
  caracteres dela.
- CA-04 Passar o mouse numa página em chinês mostra a definição e um botão para criar o card; num caractere, mostra as
  partes dele.
- CA-05 Em 30 dias, pelo menos 25 dias com o mínimo cumprido, e o navegador nunca voltou para o inglês.
- CA-06 Os rótulos do caminho de volta para o inglês estão entre os 10 primeiros cards do baralho em que aparecem.
- CA-07 Depois de trocar cada aparelho para chinês, a pessoa consegue voltar para o inglês usando só o que estudou.
