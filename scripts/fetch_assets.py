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
YADISK = os.environ.get("YADISK_URL", "https://disk.yandex.ru/d/WOpXanmdKpNRww")
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
    if not files:
        print("в папке Яндекс.Диска нет фото", file=sys.stderr)
        return
    (IMG / "slider").mkdir(parents=True, exist_ok=True)
    for old in (IMG / "slider").glob("*.jpg"):  # убираем фото прошлой папки
        old.unlink()
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


def diagnose():
    """Временная проверка домена (пишет data/diag.json)."""
    import json as _j
    out = {}
    for name in ("ippoyar.ru", "www.ippoyar.ru"):
        for srv in ("https://dns.google/resolve", "https://cloudflare-dns.com/dns-query"):
            try:
                r = requests.get(srv, params={"name": name, "type": "A"}, headers={"accept": "application/dns-json"}, timeout=15).json()
                out[srv.split("/")[2] + " " + name] = {"Status": r.get("Status"), "Answer": [a.get("data") for a in r.get("Answer", [])]}
            except Exception as e:
                out[srv.split("/")[2] + " " + name] = str(e)
    import subprocess
    def dig(*a):
        try:
            return subprocess.run(["dig"] + list(a), capture_output=True, text=True, timeout=25).stdout
        except Exception as e:
            return repr(e)
    t = dig("+norec", "@a.dns.ripn.net", "ippoyar.ru", "NS")
    out["ripn NS (делегирование в зоне .ru)"] = [l for l in t.splitlines() if "IN\tNS" in l or "status" in l]
    out["ripn DS"] = [l for l in dig("+norec", "@a.dns.ripn.net", "ippoyar.ru", "DS").splitlines() if "DS" in l or "status" in l]
    out["google DS"] = requests.get("https://dns.google/resolve", params={"name": "ippoyar.ru", "type": "DS"}, timeout=15).json()
    out["google A cd=1 (без DNSSEC)"] = requests.get("https://dns.google/resolve", params={"name": "ippoyar.ru", "type": "A", "cd": "1"}, timeout=15).json()
    out["dig trace"] = dig("+trace", "ippoyar.ru", "A")[-1500:]
    for url in ("http://ippoyar.ru/", "https://ippoyar.ru/", "https://www.ippoyar.ru/"):
        try:
            r = requests.get(url, timeout=20, allow_redirects=False)
            out[url] = {"status": r.status_code, "server": r.headers.get("Server"), "location": r.headers.get("Location"), "body": r.text[:120]}
        except Exception as e:
            out[url] = repr(e)[:300]
    (ROOT / "data" / "diag.json").write_text(_j.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    for step in (diagnose, fetch_backgrounds, fetch_slider):
        try:
            step()
        except Exception as e:
            print(step.__name__, "ошибка:", e, file=sys.stderr)
