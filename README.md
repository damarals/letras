# Letras

<div align="center">
    <img src="https://img.shields.io/github/actions/workflow/status/damarals/letras/test.yml?label=testes" alt="Status dos Testes" />
    <img src="https://img.shields.io/codecov/c/github/damarals/letras" alt="Cobertura de Código" />
    <img src="https://img.shields.io/github/last-commit/damarals/letras" alt="Último Commit" />
</div>

<div align="center"><strong>Coleta e Organização Automatizada de Letras Gospel</strong></div>
<div align="center">Uma ferramenta Python para coletar, analisar e organizar letras gospel do letras.mus.br</div>

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
- Rastreamento de visualizações dos artistas
- Arquivos de texto individuais para cada música
- Detecção inteligente de novas músicas
- Geração automática de relatórios de release
- Atualizações automáticas semanais via GitHub Actions
- Interface CLI rica com acompanhamento de progresso

## Releases

O projeto é atualizado automaticamente todas as semanas através do GitHub Actions. Cada release inclui:

- 📝 **Arquivo ZIP** com todas as letras em formato texto
- 📊 **Banco de Dados** DuckDB com dados estruturados
- 📋 **Notas de Release** detalhando:
  - Total de músicas e artistas adicionados
  - Top 5 artistas por visualizações
  - Lista completa de novas adições

Você pode acessar todas as releases através da [página de releases](https://github.com/damarals/letras/releases) do projeto.

## Instalação

### 1. Usando Poetry (Recomendado)
```bash
# Clone o repositório
git clone https://github.com/damarals/letras
cd letras

# Instale as dependências
poetry install

# Execute o coletor
poetry run python main.py
```

### 2. Usando Docker
```bash
# Construa a imagem
docker build -t letras .

# Execute o container
docker run --rm -v $(pwd)/data:/app/data letras
```

## Estrutura dos Dados

O projeto organiza os dados em três tabelas principais:

1. **artists** - Informações sobre artistas gospel
   - id (CHAVE PRIMÁRIA)
   - name (nome)
   - slug (identificador URL)
   - views (número de visualizações)

2. **songs** - Metadados das músicas
   - id (CHAVE PRIMÁRIA)
   - artist_id (CHAVE ESTRANGEIRA)
   - name (nome)
   - slug (identificador URL)
   - added_date (data de adição)

3. **lyrics** - Letras e metadados das músicas
   - id (CHAVE PRIMÁRIA)
   - song_id (CHAVE ESTRANGEIRA)
   - content (conteúdo)
   - last_updated (última atualização)

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

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar bugs
- Sugerir funcionalidades
- Enviar pull requests

### Guia de Contribuição

1. Faça um fork do projeto
2. Crie sua branch de feature (`git checkout -b feature/MinhaFeature`)
3. Adicione seus commits (`git commit -m 'Adicionando nova feature'`)
4. Faça push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Aviso Legal

Esta ferramenta é apenas para fins educacionais. Todas as letras são propriedade de seus respectivos donos e são coletadas de fontes publicamente disponíveis.