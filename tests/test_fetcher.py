import threading
import time

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


def test_fetcher_retries_transient_errors() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, text="OK")

    client = httpx.Client(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client)

    assert fetcher.artist_index() == "OK"
    assert calls["n"] == 2  # one failure, one retry


def test_fetch_many_is_bounded_and_ordered() -> None:
    lock = threading.Lock()
    state = {"in_flight": 0, "max": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        with lock:
            state["in_flight"] += 1
            state["max"] = max(state["max"], state["in_flight"])
        time.sleep(0.02)
        with lock:
            state["in_flight"] -= 1
        return httpx.Response(200, text=request.url.path)

    client = httpx.Client(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client, max_workers=3)
    paths = [f"/p{i}" for i in range(9)]

    results = fetcher.fetch_many(paths)

    assert results == paths  # order preserved
    assert 1 < state["max"] <= 3  # concurrent but bounded
