
<!-- README.md is generated from README.Rmd. Please edit that file -->

# Pacote Letras

<!-- badges: start -->

[![R-CMD-check](https://github.com/damarals/letras/workflows/R-CMD-check/badge.svg)](https://github.com/damarals/letras/actions)
[![atualizar-dados](https://github.com/damarals/letras/actions/workflows/atualizar-dados.yaml/badge.svg)](https://github.com/damarals/letras/actions/workflows/atualizar-dados.yaml)
<!-- badges: end -->

O objetivo deste pacote é disponibilizar as letras do gênero Gospel
(Católica, Protestante, Internacional, etc). O pacote é atualizado
semanalmente através de um workflow com [GitHub
Actions](https://github.com/damarals/letras/actions).

Os dados foram obtidos do [Portal Letras](https://www.letras.mus.br/).

**Caso você não utilize R**, é possível **fazer download das letras**
através dos seguintes links:

-   *Letras Individuais* [Arquivo
    `.zip`](https://github.com/damarals/letras/raw/master/inst/letras.zip)
-   *Letras Individuais (Holyrics)* [Arquivo
    `.zip`](https://github.com/damarals/letras/raw/master/inst/letras_holyrics.zip)
-   *Tabela de Artistas* [Arquivo
    `.csv`](https://github.com/damarals/letras/raw/master/inst/csv/artistas.csv)
-   *Tabela de Músicas* [Arquivo
    `.csv`](https://github.com/damarals/letras/raw/master/inst/csv/musicas.csv)
-   *Tabela de Letras* [Arquivo
    `.csv`](https://github.com/damarals/letras/raw/master/inst/csv/letras.csv)

O arquivo de letras individuais, contem todas as letras do gênero gospel
em `.txt` zipadas, esse formato é aceito pelos mais comuns *softwares*
de apresentações em igrejas. Já os arquivos `.csv` foram salvos com
encoding UTF-8 e separados por vírgula. Adicionalmente, há um pacote de
letras para o software *Holyrics* (*Importar Música(s)*: Música ->
Importar -> Outros -> TXT File (ISO-8859-1)), que possui algumas
peculiaridades.

## Instalação

Este pacote pode ser instalado através do [GitHub](https://github.com/)
utilizando o seguinte código em `R`:

``` r
# install.packages("devtools")
devtools::install_github("damarals/letras")
library(letras)
```

## Como usar?

Caso você tenha conexão à internet, é possível buscar a base atualizada
usando a função `dados_atualizados()`:

``` r
letras_atualizadas <- letras::dados_atualizados(tabela = 'letras') 
```

Caso você não tenha conexão à internet, você pode utilizar a base
disponível no pacote. Porém as mesmas estarão atualizadas até a data em
que você instalou (ou atualizou) o pacote.

Abaixo segue um exemplo da base disponível:

``` r
dplyr::glimpse(letras::letras)
#> Rows: 49,994
#> Columns: 3
#> $ artista <chr> "Harpa Cristã", "Harpa Cristã", "Harpa Cristã", "Harpa Cristã"~
#> $ musica  <chr> "Porque Ele Vive", "A Alma Abatida", "Solta O Cabo da Nau", "E~
#> $ letra   <chr> "Deus enviou\nSeu Filho amado\nPara morrer, em meu lugar\nNa c~
```

### Exemplo de tabela

``` r
library(magrittr)
letras_atualizadas %>% 
  head(5) %>%
  knitr::kable() 
```

| artista          | musica                        | letra              |
|:-----------------|:------------------------------|:-------------------|
| Harpa Cristã     | Porque Ele Vive               | Deus enviou        |
| Seu F…           |                               |                    |
| Harpa Cristã     | A Alma Abatida                | Se tu, minh’alma,… |
| Harpa Cristã     | Solta O Cabo da Nau           | 1 Oh! Por que duv… |
| Harpa Cristã     | Em Fervente Oração            | 1                  |
| Em fervente ora… |                               |                    |
| Harpa Cristã     | Olhai Para O Cordeiro de Deus | Livres de pecado … |
