# Letras

<div align="center">
   <img src="https://img.shields.io/github/actions/workflow/status/damarals/letras/test.yaml?label=ci" alt="Status dos CI" />
   <img src="https://img.shields.io/github/actions/workflow/status/damarals/letras/release.yaml?label=cd" alt="Status dos CD" />
    <a href="https://codecov.io/gh/damarals/letras" >
      <img src="https://codecov.io/gh/damarals/letras/graph/badge.svg?token=OZX22OK364" alt="Cobertura de Código"/>
   </a>
</div>

<div align="center">
   <strong>Coleta e Organização Automatizada de Letras Gospel</strong>
</div>
<div align="center">Uma ferramenta Python para coletar e organizar letras gospel do letras.mus.br</div>

<br />
<div align="center">
  <sub>Desenvolvido por <a href="https://github.com/damarals">Daniel Amaral</a> 👨‍💻</sub>
</div>
<br />

## Introdução

Letras é uma aplicação Python desenvolvida para automatizar a coleta e organização de letras de músicas gospel. O projeto faz a raspagem de dados do letras.mus.br, processa as informações e disponibiliza acesso organizado às letras através de um banco de dados DuckDB e arquivos de texto individuais. O sistema também rastreia a popularidade dos artistas através de suas visualizações.

## Funcionalidades

- Coleta automatizada de letras gospel do letras.mus.br
- Processamento multithread para coleta eficiente de dados
- Banco de dados DuckDB para armazenamento estruturado
- Arquivos de texto individuais para cada música
- Detecção inteligente de novas músicas
- Geração automática de relatórios de release
- Atualizações automáticas semanais via GitHub Actions
- Interface CLI com acompanhamento de progresso

## Releases

O projeto é atualizado automaticamente todas as semanas através do GitHub Actions. Cada release inclui:

- 📝 **Arquivo ZIP** com todas as letras em formato de texto (.txt)
- 📊 **Banco de Dados** DuckDB com dados estruturados
- 📋 **Notas de Release** detalhando:
  - Total de músicas e artistas adicionados
  - Top 5 artistas por visualizações
  - Lista completa de novas adições

Você pode acessar todas as releases através da [página de releases](https://github.com/damarals/letras/releases) do projeto.

## Instalação usando Poetry

```bash
# Clone o repositório
git clone https://github.com/damarals/letras
cd letras

# Instale as dependências com poetry
poetry install

# Execute o coletor
poetry run python main.py
```

## Estrutura dos Dados

O projeto organiza os dados em três tabelas principais:

![Diagrama ERD](.github/erd.png)

## Formato dos Arquivos de Texto

Cada arquivo de letra segue este formato:
```
<Título>
<Artista>

<Conteúdo da Letra>
```

Os arquivos são salvos como `<Artista> - <Título>.txt` no arquivo ZIP da release.

## Atualizações Automáticas

O repositório é atualizado automaticamente toda semana através do GitHub Actions. O workflow:

1. Executa testes e atualiza estatísticas de cobertura
2. Coleta e identifica novas músicas
3. Atualiza contagem de visualizações dos artistas
4. Gera relatório detalhado das mudanças
5. Cria uma nova release com:
   - Arquivo ZIP atualizado com todas as letras
   - Banco de dados atualizado
   - Notas de release em markdown

## Contribuindo

Contribuições são sempre bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests. Se encontrar algum problema ou quiser sugerir uma melhoria, não hesite em contribuir.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## Aviso Legal

Esta ferramenta é apenas para fins educacionais. Todas as letras são propriedade de seus respectivos donos e são coletadas de fontes publicamente disponíveis.