import httpx

from letras.source.fetcher import Fetcher


def test_fetcher_builds_paths_and_returns_body() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, text=f"BODY {request.url.path}")

    client = httpx.Client(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client)

    assert fetcher.song_page("aline-barros", "44039") == "BODY /aline-barros/44039/"
    assert fetcher.artist_index() == "BODY /estilos/gospelreligioso/todosartistas.html"
    assert "/aline-barros/44039/" in seen
