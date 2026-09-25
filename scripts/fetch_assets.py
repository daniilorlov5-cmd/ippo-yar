"""Скачивает внешние картинки в репозиторий (один раз):
  - фон и фон шапки с ippo.ru (так указано в ТЗ);
  - фото для слайд-шоу из публичной папки Яндекс.Диска.
Повторный запуск ничего не перекачивает. FORCE_SLIDER=1 — пересобрать слайдер.
"""
import io, json, os, sys
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "img"
YADISK = os.environ.get("YADISK_URL", "https://disk.yandex.ru/d/yNURkvisEZJ3XA")
UA = {"User-Agent": "Mozilla/5.0 (site asset sync)"}

BG = {
    "bg.png": "https://www.ippo.ru/media/front/images/bg.png",
    "bg-header.png": "https://www.ippo.ru/media/front/images/bg-header.png",
}


def fetch_backgrounds():
    IMG.mkdir(parents=True, exist_ok=True)
    for name, url in BG.items():
        dst = IMG / name
        if dst.exists():
            continue
        r = requests.get(url, headers=UA, timeout=60)
        r.raise_for_status()
        dst.write_bytes(r.content)
        print("скачан", name, len(r.content))


def list_disk(path=None):
    params = {"public_key": YADISK, "limit": 200}
    if path:
        params["path"] = path
    r = requests.get("https://cloud-api.yandex.net/v1/disk/public/resources", params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    if data.get("type") == "file":
        return [data]
    files = []
    for it in data.get("_embedded", {}).get("items", []):
        if it["type"] == "dir":
            files += list_disk(it["path"])
        elif it.get("media_type") == "image":
            files.append(it)
    return files


def fetch_slider():
    out = ROOT / "data" / "slider.json"
    current = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    if current and os.environ.get("FORCE_SLIDER") != "1":
        return
    files = sorted(list_disk(), key=lambda f: f["name"])
    (IMG / "slider").mkdir(parents=True, exist_ok=True)
    result = []
    for i, f in enumerate(files, 1):
        url = f.get("file")
        if not url:
            continue
        try:
            r = requests.get(url, headers=UA, timeout=120)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content))
            try:
                from PIL import ImageOps
                im = ImageOps.exif_transpose(im)
            except Exception:
                pass
            im = im.convert("RGB")
            im.thumbnail((1600, 1600))
            name = f"img/slider/{i:02d}.jpg"
            im.save(ROOT / name, "JPEG", quality=82, optimize=True, progressive=True)
            result.append(name)
            print("слайд", name, f["name"])
        except Exception as e:
            print("не скачалось:", f.get("name"), e, file=sys.stderr)
    if result:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for step in (fetch_backgrounds, fetch_slider):
        try:
            step()
        except Exception as e:
            print(step.__name__, "ошибка:", e, file=sys.stderr)
