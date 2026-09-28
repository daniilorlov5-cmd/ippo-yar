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


def diagnose():
    """Временная диагностика домена (запускается роботом, пишет data/diag.json)."""
    import socket, ssl, json as _j
    out = {}
    for name in ("ippoyar.ru", "www.ippoyar.ru"):
        for t in ("NS", "A", "AAAA", "CNAME"):
            for srv in ("https://dns.google/resolve", "https://cloudflare-dns.com/dns-query"):
                try:
                    r = requests.get(srv, params={"name": name, "type": t}, headers={"accept": "application/dns-json"}, timeout=15).json()
                    out[f"{srv.split('/')[2]} {name} {t}"] = {"Status": r.get("Status"), "Answer": [a.get("data") for a in r.get("Answer", [])], "Authority": [a.get("data") for a in r.get("Authority", [])]}
                except Exception as e:
                    out[f"{srv.split('/')[2]} {name} {t}"] = str(e)
    try:
        s = socket.create_connection(("whois.tcinet.ru", 43), timeout=15); s.sendall(b"ippoyar.ru\r\n")
        buf = b""
        while True:
            d = s.recv(4096)
            if not d: break
            buf += d
        out["whois"] = buf.decode("utf-8", "replace")[-1500:]
    except Exception as e:
        out["whois"] = str(e)
    for url in ("http://ippoyar.ru/", "https://ippoyar.ru/", "https://www.ippoyar.ru/"):
        try:
            r = requests.get(url, timeout=20, allow_redirects=False)
            out[url] = {"status": r.status_code, "headers": dict(r.headers), "body": r.text[:400]}
        except Exception as e:
            out[url] = repr(e)[:400]
    try:
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection(("ippoyar.ru", 443), timeout=15) as sock:
            with ctx.wrap_socket(sock, server_hostname="ippoyar.ru") as ss:
                der = ss.getpeercert(binary_form=True)
                out["cert_der_len"] = len(der)
        out["cert_verified"] = "?"
        ctx2 = ssl.create_default_context()
        with socket.create_connection(("ippoyar.ru", 443), timeout=15) as sock:
            with ctx2.wrap_socket(sock, server_hostname="ippoyar.ru") as ss:
                c = ss.getpeercert(); out["cert"] = {"subject": c.get("subject"), "issuer": c.get("issuer"), "notAfter": c.get("notAfter"), "san": c.get("subjectAltName")}
    except Exception as e:
        out["cert_error"] = repr(e)[:400]
    (ROOT / "data" / "diag.json").write_text(_j.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    for step in (diagnose, fetch_backgrounds, fetch_slider):
        try:
            step()
        except Exception as e:
            print(step.__name__, "ошибка:", e, file=sys.stderr)
