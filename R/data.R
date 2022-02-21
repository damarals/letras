#' Nomes e Links do Portfolio Relativo de Musicas de Artistas do Genero
#' Gospel no Portal de Letras Vagalume.
#'
#' Names and Relative Links of the  Music Portfolio of Artists of the Genre
#' Gospel on the Vagalume Lyrics Portal.
#'
#' @format Um conjunto de dados com `r nrow(artistas)` artistas e 2 variaveis:
#' \describe{
#'   \item{nome}{nome do artista}
#'   \item{href}{link relativo para o portfolio de musicas do artista}
#' }
#' @source \url{https://www.vagalume.com.br/browse/style/gospel.html}
"artistas"

#' Nomes do Artista e Musicas, com Links Relativos das Letras do Genero
#' Gospel no Portal de Letras Vagalume.
#'
#' Artist Names and Songs, with Relative Links of Gospel Lyrics Genre
#' on the Vagalume Lyrics Portal.
#'
#' @format Um conjunto de dados com `r nrow(musicas)` musicas e 3 variaveis:
#' \describe{
#'   \item{nome}{nome do artista}
#'   \item{musica}{nome da musica}
#'   \item{href}{link relativo para a letra da musica}
#' }
#' @source \url{https://www.vagalume.com.br/browse/style/gospel.html}
"musicas"

#' Letras e Nomes de Musicas de todos os Artistas do Genero Gospel no
#' Portal de Letras Vagalume.
#'
#' Lyrics and Song Names of all Genero Gospel Artists on Portal of
#' Vagalume Lyrics.
#'
#' @format Um conjunto de dados com `r nrow(letras)` letras e 3 variaveis:
#' \describe{
#'   \item{nome}{nome do artista}
#'   \item{musica}{nome da musica}
#'   \item{lyric}{letra da musica}
#' }
#' @source \url{https://www.vagalume.com.br/browse/style/gospel.html}
"letras"
