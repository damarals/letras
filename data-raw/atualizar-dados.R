# Obter letras atualizadas
artistas <- letras:::obter_artistas()
musicas <- tidyr::drop_na(letras:::obter_musicas())
letras <- tidyr::drop_na(letras:::obter_letras())

# Salvar letras no pacote
usethis::use_data(artistas, overwrite = TRUE, compress = "bzip2")
usethis::use_data(musicas, overwrite = TRUE, compress = "bzip2")
usethis::use_data(letras, overwrite = TRUE, compress = "bzip2")

# Salvar letras em csv
readr::write_csv(artistas, "inst/csv/artistas.csv")
readr::write_csv(musicas, "inst/csv/musicas.csv")
readr::write_csv(letras, "inst/csv/letras.csv")

# Salvar letras em txt
purrr::walk(1:nrow(letras), function(ix_letra) {
  letra <- letras[ix_letra,]
  letra_txt <- glue::glue("{letra$musica}\n{letra$artista}\n\n{letra$letra}")
  nome_arq <- paste0(gsub('[[:punct:]]+','', letra$musica), " - ",
                     gsub('[[:punct:]]+','', letra$artista))
  write.table(letra_txt, glue::glue("inst/txt/{nome_arq}.txt"),
              append = FALSE)
})

# Salvar letras em txt zipadas
letras_path <- Sys.glob(paths = "inst/txt/*.txt")
zip::zip(zipfile = "inst/letras.zip", files = letras_path, mode = 'cherry-pick')
