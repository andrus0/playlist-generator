def test_meta(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    m = r.json()
    assert m["songs"] == 16  # 15 US + "Geno" (UK only)
    assert m["decades"][0] == "1960s"
    assert {x["code"]: x["songs"] for x in m["regions"]}["UK"] == 3


def test_artists_autocomplete(client):
    r = client.get("/api/artists", params={"q": "beat"})
    assert r.json()[0]["name"] == "The Beatles"
    assert r.json()[0]["songs"] == 2


def test_playlist_json(client):
    r = client.get("/api/playlist", params={"decades": "1980s", "level": "no1", "seed": 7})
    assert r.status_code == 200
    p = r.json()
    assert p["seed"] == 7
    assert p["query"]["decades"] == ["1980s"]
    assert all(any(c["peak"] == 1 for c in t["charts"]) for t in p["tracks"])
    assert p["tracks"][0]["position"] == 1


def test_playlist_txt(client):
    r = client.get("/api/playlist", params={"artists": "Queen", "sort": "year", "format": "txt"})
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert "Queen – Bohemian Rhapsody (1975)" in body
    assert body.startswith("# Queen")


def test_playlist_csv_and_m3u(client):
    r = client.get("/api/playlist", params={"artists": "Toto", "format": "csv"})
    assert r.text.splitlines()[0] == "position,artist,title,year,best_peak,regions"
    r = client.get("/api/playlist", params={"artists": "Toto", "format": "m3u"})
    assert r.text.startswith("#EXTM3U")


def test_validation(client):
    assert client.get("/api/playlist", params={"count": 0}).status_code == 422
    assert client.get("/api/playlist", params={"level": "top5"}).status_code == 422


def test_healthz(client):
    assert client.get("/api/healthz").json() == {"status": "ok"}
