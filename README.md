<h1 align="center">Letras</h1>
<div align="center">
    <img src="https://img.shields.io/github/v/tag/damarals/letras?color=success&label=" alt="Latest Tag" />
    <img src="https://img.shields.io/github/last-commit/damarals/letras/main?path=README.md&label=%C3%BAltima%20atualiza%C3%A7%C3%A3o&color=blue" alt="Última atualização" />
    <img src="https://img.shields.io/github/actions/workflow/status/damarals/letras/test.yaml?label=testes" alt="Testes" />
</div>
<br />
<div align="center"><strong>Um corpus de letras gospel em português</strong></div>
<div align="center">Letras evangélicas curadas, em banco SQLite e arquivos de texto,<br/> atualizadas automaticamente toda semana.</div>
<br />
<div align="center">
  <sub>Desenvolvido por <a href="https://github.com/damarals">Daniel Amaral</a> 👨‍💻</sub>
</div>
<br />

## Download

Baixe na última [release](https://github.com/damarals/letras/releases/latest):

<div align="center">
  <a href="https://github.com/damarals/letras/releases/latest/download/corpus.db"><img src="https://custom-icon-badges.demolab.com/badge/Baixar-SQLite-F25278?style=for-the-badge&logo=download&logoColor=white" alt="SQLite" /></a>
  <a href="https://github.com/damarals/letras/releases/latest/download/lyrics.zip"><img src="https://custom-icon-badges.demolab.com/badge/Baixar-Textos-F25278?style=for-the-badge&logo=download&logoColor=white" alt="Textos" /></a>
</div>

## Conteúdo

- **SQLite** (`corpus.db`) — tabelas `artists`, `songs` e `lyrics`. O banco guarda **tudo o que foi coletado**; o corpus curado é uma consulta:

  ```sql
  SELECT * FROM lyrics WHERE admitted = 1;
  ```

- **Textos** (`lyrics.zip`) — um arquivo `<Artista> - <Música>.txt` por música admitida.
- **RELEASE_NOTES.md** — resumo da release (quantas músicas, de quantos artistas).

## Curadoria

Uma letra entra no corpus (`admitted = 1`) quando é **gospel evangélica em português**. As regras (em [`src/letras/filters.yaml`](src/letras/filters.yaml)) mantêm apenas texto em português entre 100 e 4000 caracteres e excluem conteúdo católico, afro-brasileiro e não-protestante por palavra-chave (com correspondência sem acento e por palavra inteira). Tudo é coletado e guardado; a curadoria é aplicada na hora de gerar a release, então dá para reajustar as regras sem recoletar.

## Para mantenedores

Toolkit em Python (com [uv](https://docs.astral.sh/uv/)). Sem banco de dados, sem Docker: o estado é o `corpus.db` da última release.

```bash
uv sync
uv run letras run --incremental   # semanal: coleta só músicas novas
uv run letras run                 # reconciliação completa (recoleta tudo)
uv run letras export --out dist   # gera corpus.db + lyrics.zip + notas
```

Configurável por variáveis `LETRAS_` (ex.: `LETRAS_DELAY`, `LETRAS_MAX_WORKERS`).

## Atualizações automáticas

Toda semana, o GitHub Actions roda a coleta incremental, aplica a curadoria e publica uma nova release com o banco atualizado, os textos e as notas.

## Licença

MIT. Veja [LICENSE](LICENSE).

## Aviso Legal

Ferramenta para fins educacionais. As letras são propriedade de seus respectivos donos e foram coletadas de fontes publicamente disponíveis.
