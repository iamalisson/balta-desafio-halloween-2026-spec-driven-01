# Constituição do projeto

## Stack

- Python 3.13 e uv. As dependências ficam em `pyproject.toml` e `uv.lock`; nada é instalado fora do uv.
- Anki é o app de estudo. Os baralhos saem como um arquivo `.apkg` que se importa com dois cliques.
- Toda dependência nova só entra com a justificativa escrita em `specs/plan.md`.

## Arquitetura

- Um programa só em `src/zh.py`, com dois comandos (`build` e `yomidict`). Dados curados à mão ficam em
  `src/curated.py`, e as verificações em `src/test_zh.py`. Nenhum outro arquivo em `src/`.
- Biblioteca padrão primeiro. Uma dependência só entra quando faz algo que algumas linhas de código não fazem.
- Fontes externas são baixadas uma vez para `cache/`; tudo o que é gerado vai para `build/`. Nenhum dos dois entra no
  git.
- O programa nunca escreve na coleção do Anki. Ele só lê (as histórias da pessoa) pelo AnkiConnect; quem importa é a
  pessoa.

## Qualidade

- Toda regra com lógica (parser, ordenação, escolha de leitura, reimportação) tem pelo menos um `assert` em
  `src/test_zh.py`. Sem framework de testes.
- `uv run src/test_zh.py` passa antes de qualquer commit.
- O build termina sem warnings e imprime as contagens de cada etapa (notas, áudios, exemplos, glosas faltando).
- Gerar o baralho de novo nunca duplica notas nem perde histórico de revisões ou histórias (testado em
  `test_reimport`).
- Tudo o que não foi verificado nesta máquina fica marcado como NÃO VERIFICADO nas specs.

## Convenções

- Um plano escrito antes do código: `spec.md` diz o quê e por quê, `plan.md` diz como, `tasks.md` diz em que ordem.
- Commits no padrão Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`), um commit por fase ou funcionalidade.
- Sem boilerplate: nada de interfaces com uma implementação só nem configuração para valores que nunca mudam.
- Toda tarefa aponta o requisito ou a decisão de onde veio, e tem um "Concluída quando" verificável.
- O progresso é revisado toda semana (T-21) e a cada mês (T-22).

## Governança

- Mudança de rumo entra primeiro como atualização datada em `spec.md`, depois em `plan.md` e `tasks.md`.
- Nenhuma tarefa é marcada como feita sem o sinal de verificação descrito no "Concluída quando".
- Conteúdo de terceiros com direitos incertos nunca entra numa versão publicada (RN-04).
