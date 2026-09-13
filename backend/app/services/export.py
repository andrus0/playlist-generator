"""Text/CSV/M3U renderers for a generated playlist."""

import csv
import io

from ..schemas import PlaylistOut


def to_txt(p: PlaylistOut) -> str:
    lines = [f"# {p.name}", ""]
    width = len(str(len(p.tracks)))
    for t in p.tracks:
        lines.append(f"{t.position:>{width}}. {t.artist} – {t.title} ({t.year})")
    return "\n".join(lines) + "\n"


def to_csv(p: PlaylistOut) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["position", "artist", "title", "year", "best_peak", "regions"])
    for t in p.tracks:
        best = min(c.peak for c in t.charts) if t.charts else ""
        w.writerow(
            [t.position, t.artist, t.title, t.year, best, "|".join(c.region for c in t.charts)]
        )
    return buf.getvalue()


def to_m3u(p: PlaylistOut) -> str:
    lines = ["#EXTM3U", f"#PLAYLIST:{p.name}"]
    for t in p.tracks:
        lines.append(f"#EXTINF:-1,{t.artist} - {t.title}")
        lines.append(f"{t.artist} - {t.title}.mp3")
    return "\n".join(lines) + "\n"
