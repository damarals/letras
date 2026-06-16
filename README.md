<h1 align="center">Letras</h1>
<div align="center">
    <img src="https://img.shields.io/github/v/tag/damarals/letras?color=success&label=" alt="Latest Tag" />
    <img src="https://img.shields.io/github/last-commit/damarals/letras/main?path=README.md&label=%C3%BAltima%20atualiza%C3%A7%C3%A3o&color=blue" alt="Última atualização" />
</div>
<br />
<div align="center"><strong>Uma coletânea de milhares de letras gospel em português</strong></div>
<div align="center">Em formatos abertos (.txt e .xml), pronta para uso no OpenLP, Quelea ou em qualquer outra aplicação.</div>
<br />
<div align="center">
  <a href="https://github.com/damarals/letras/releases/latest/download/letras-txt.zip"><img src="https://custom-icon-badges.demolab.com/badge/Baixar-Letras%20(.txt)-F25278?style=for-the-badge&logo=download&logoColor=white" alt="Letras (.txt)" /></a>
  <a href="https://github.com/damarals/letras/releases/latest/download/letras-openlyrics.zip"><img src="https://custom-icon-badges.demolab.com/badge/Baixar-Letras%20(.xml)-F25278?style=for-the-badge&logo=download&logoColor=white" alt="Letras (.xml)" /></a>
</div>
<br />
<div align="center">
  <sub>Desenvolvido por <a href="https://github.com/damarals">Daniel Amaral</a> 👨‍💻</sub>
</div>
<br />

## Conteúdo

- **Textos** (`letras-txt.zip`): um arquivo `<Artista> - <Música>.txt` por música aprovada. Cada um traz título, artista, uma linha em branco e a letra.
- **OpenLyrics** (`letras-openlyrics.zip`): um `.xml` por música no formato [OpenLyrics](https://docs.openlyrics.org/). O OpenLP e o Quelea importam direto, com título e autor já nos campos certos.
- **SQLite** (`corpus.db`): tabelas `artists`, `songs` e `lyrics`. O banco guarda **tudo o que foi coletado**, inclusive o que a curadoria descartou. Os dois `.zip` trazem só as letras aprovadas, o resultado desta consulta:

  ```sql
  SELECT * FROM lyrics WHERE admitted = 1;
  ```

## Curadoria

Uma letra entra no corpus (`admitted = 1`) quando é gospel evangélica em português: idioma português, entre 100 e 4000 caracteres, e fora das listas de palavras-chave em [`src/letras/filters.yaml`](src/letras/filters.yaml). A coleta guarda tudo; a curadoria roda na hora da release, então você ajusta as regras sem recoletar.

## Para mantenedores

Toolkit em Python (com [uv](https://docs.astral.sh/uv/)). Sem banco de dados, sem Docker: o estado é o `corpus.db` da última release.

```bash
uv sync
uv run letras run --incremental   # semanal: coleta só músicas novas
uv run letras run                 # reconciliação completa (recoleta tudo)
uv run letras export --out dist   # gera corpus.db, os .zip e as notas
```

Configurável por variáveis `LETRAS_` (ex.: `LETRAS_DELAY`, `LETRAS_MAX_WORKERS`).

## Licença

MIT. Veja [LICENSE](LICENSE).
