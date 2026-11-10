from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

from ...qt_compat import QColor, QPainter, QPen, QPixmap, Qt

ASSET_DIR = Path(__file__).resolve().parent / "assets"

_FILES = {
    "df1": "alignment_df_1.png",
    "df2": "alignment_df_2.png",
    "bf": "alignment_bf.png",
}

# Microscope-photo hosts were unreachable from this network. These dataset
# figures are reachable, but they are paper tables rather than a camera field,
# so Alignment draws a die-grid image when a download cannot be used.
_DOWNLOADS = {
    "df1": [],
    "df2": [],
    "bf": [],
}

_cache: dict[str, QPixmap] = {}
_ready = False


def ensure_simulated_alignment_images() -> None:
    """Use downloaded wafer photos when the network allows, otherwise draw stand-ins."""
    global _ready
    if _ready and all(_valid(ASSET_DIR / name) for name in _FILES.values()):
        return
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for key, filename in _FILES.items():
        path = ASSET_DIR / filename
        if _valid(path):
            continue
        if not _download(key, path):
            _generate(path, key)
    _ready = all(_valid(ASSET_DIR / name) for name in _FILES.values())


def pixmap_for_alignment_image(image_name: str) -> QPixmap | None:
    if not image_name or not str(image_name).startswith("Sim Cross Mark"):
        return None
    ensure_simulated_alignment_images()
    if "(BF)" in image_name:
        key = "bf"
    elif "2" in image_name or "Offset" in image_name:
        key = "df2"
    else:
        key = "df1"
    path = ASSET_DIR / _FILES[key]
    cached = _cache.get(str(path))
    if cached is None:
        cached = QPixmap(str(path))
        _cache[str(path)] = cached
    return None if cached.isNull() else cached


def _valid(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 2000


def _download(key: str, path: Path) -> bool:
    for url in _DOWNLOADS[key]:
        try:
            request = Request(url, headers={"User-Agent": "pumaUI-simulator"})
            with urlopen(request, timeout=8) as response:
                data = response.read()
        except Exception:
            continue
        if len(data) < 2000:
            continue
        download_path = path.with_suffix(".download")
        download_path.write_bytes(data)
        pixmap = QPixmap()
        if not pixmap.load(str(download_path)):
            download_path.unlink(missing_ok=True)
            continue
        saved = pixmap.save(str(path), "PNG")
        download_path.unlink(missing_ok=True)
        if saved and _valid(path):
            return True
    return False


def _generate(path: Path, kind: str) -> None:
    pixmap = QPixmap(960, 720)
    dark = kind != "bf"
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    base = QColor("#161616") if dark else QColor("#d5d5ce")
    street = QColor("#4a4a4a") if dark else QColor("#6a6a64")
    die = QColor("#2c2c2c") if dark else QColor("#c4c4bc")
    mark = QColor("#f4f4ee") if dark else QColor("#161616")
    painter.fillRect(pixmap.rect(), base)
    die_w, die_h = (84, 68) if kind != "df2" else (96, 74)
    offset = 24 if kind == "df2" else 0
    for x in range(-offset, pixmap.width() + die_w, die_w):
        for y in range(-offset, pixmap.height() + die_h, die_h):
            painter.fillRect(x + 7, y + 7, die_w - 14, die_h - 14, die)
            painter.setPen(QPen(QColor("#8d8d8d") if dark else QColor("#5c5c56"), 1))
            painter.drawLine(x + 14, y + die_h // 2, x + die_w - 16, y + die_h // 2)
            painter.drawLine(x + die_w // 2, y + 14, x + die_w // 2, y + die_h - 16)
        painter.fillRect(x, 0, 4, pixmap.height(), street)
    for y in range(-offset, pixmap.height() + die_h, die_h):
        painter.fillRect(0, y, pixmap.width(), 4, street)
    center_x = 520 if kind == "df2" else 470
    center_y = 340 if kind == "df2" else 360
    painter.setPen(QPen(mark, 12))
    painter.drawLine(center_x - 78, center_y, center_x + 78, center_y)
    painter.drawLine(center_x, center_y - 78, center_x, center_y + 78)
    painter.setPen(QPen(base, 4))
    painter.drawLine(center_x - 16, center_y, center_x + 16, center_y)
    painter.drawLine(center_x, center_y - 16, center_x, center_y + 16)
    painter.end()
    pixmap.save(str(path), "PNG")
