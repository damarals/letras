#' obter_artistas
#'
#' @description Funcao para montagem da tabela de artistas
#'
#' @return Um dataframe com todos os artistas, do genero gospel, encontrados no
#' portal do vagalume.
#'
#' @noRd
obter_artistas <- function() {
  u <- "https://www.vagalume.com.br/browse/style/gospel.html"
  artistas_xml <- rvest::read_html(u) %>%
    rvest::html_elements(xpath = "//div[contains(@class, 'moreNamesContainer')]//a")
  artistas_nome <- artistas_xml %>%
    rvest::html_text()
  artistas_href <- artistas_xml %>%
    rvest::html_attr(name = "href")
  tibble::tibble(
    nome = artistas_nome, href = artistas_href
  )
}

#' obter_musicas
#'
#' @description Funcao para montagem da tabela de musicas
#'
#' @return Um dataframe com todas as musicas, para cada artista do genero gospel,
#' encontradas no portal do vagalume.
#'
#' @noRd
obter_musicas <- function() {
  load("data/artistas.rda")
  future::plan(future::multisession, workers = 10)
  furrr::future_map_dfr(1:nrow(artistas), function(id_artista) {
    artista <- artistas[id_artista,]
    artista_letras <- tryCatch({
      u <- glue::glue("https://www.vagalume.com.br{artista$href}")
      musicas_xml <- rvest::read_html(u) %>%
        rvest::html_elements(xpath = "//ol[@id='alfabetMusicList']") %>%
        rvest::html_elements(xpath = "//a[contains(@class, 'nameMusic')]")
      artista_nome <- artista$nome
      musicas_nome <- musicas_xml %>%
        rvest::html_text()
      musicas_href <- musicas_xml %>%
        rvest::html_attr(name = "href")
      tibble::tibble(
        artista = artista_nome, musica = musicas_nome, href = musicas_href
      )
    }, error = function(e) tibble::tibble(artista = NA, musica = NA, href = NA))
    return(artista_letras)
  })
}

#' obter_letras
#'
#' @description Funcao para montagem da tabela de letras das musicas
#'
#' @return Um dataframe com todas letras das musicas, para cada artista do
#' genero gospel, encontradas no portal do vagalume.
#'
#' @noRd
obter_letras <- function() {
  load("data/musicas.rda")
  future::plan(future::multisession, workers = 20)
  furrr::future_map_dfr(1:nrow(musicas), function(id_musica) {
    tryCatch({
      musica <- musicas[id_musica,]
      u <- glue::glue("https://www.vagalume.com.br{musica$href}")
      letra <- rvest::read_html(u) %>%
        rvest::html_elements(xpath = "//div[@id='lyrics']") %>%
        rvest::html_text2()
      dplyr::mutate(musica, href = NULL, letra = letra)
    }, error = function(e) {dplyr::mutate(musica, href = NULL, letra = NA)})
  })
}

#' dados_atualizados
#'
#' @description Funcao para leitura de tabelas atualizadas
#'
#' @param tabela tipo da tabela: artistas, musicas ou letras.
#'
#' @return Um dataframe atualizado com conteudo de acordo com a tabela
#' escolhida.
#'
#' @noRd
dados_atualizados <- function(tabela) {
  u <- glue::glue('https://github.com/damarals/letras/blob/master/data/{tabela}.rda?raw=true')
  load(url(u))
}
