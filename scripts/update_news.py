"""Собирает новости сайта из постов ВКонтакте.

Источники постов:
  1. data/vk-links.txt — ссылки, добавленные вручную или из админки (по одной в строке).
  2. Если задан секрет VK_TOKEN — ещё и последние записи со стены группы.

Без токена текст и фото берутся из открытого превью поста (og-теги).
С токеном — через VK API (полный текст, дата, все фото).
Новости, созданные или отредактированные в админке, скрипт не трогает.
"""
import io, json, os, re, sys, time, html
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LINKS = ROOT / "data" / "vk-links.txt"
OUT = ROOT / "data" / "news.json"
HIDDEN = ROOT / "data" / "news-hidden.json"
IMG_DIR = ROOT / "img" / "news"
GROUP_ID = -234054681
TOKEN = os.environ.get("VK_TOKEN", "").strip()
WALL_COUNT = int(os.environ.get("VK_WALL_COUNT", "20"))
UA = {"User-Agent": "TelegramBot (like TwitterBot)"}

RX = re.compile(r"wall(-?\d+)_(\d+)")


def read_links():
    ids = []
    if LINKS.exists():
        for line in LINKS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = RX.search(line)
            if m:
                ids.append((int(m.group(1)), int(m.group(2))))
            else:
                print("Не похоже на ссылку на пост ВК:", line, file=sys.stderr)
    return ids


def post_url(owner, pid):
    return f"https://vk.ru/wall{owner}_{pid}"


def save_image(url, owner, pid, n=0):
    if not url:
        return ""
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{abs(owner)}_{pid}.jpg" if n == 0 else f"{abs(owner)}_{pid}_{n}.jpg"
    dst = IMG_DIR / name
    if not dst.exists():
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            im.thumbnail((1600, 1600))
            im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
        except Exception as e:  # noqa
            print("Фото не скачалось:", url, e, file=sys.stderr)
            return ""
    return f"img/news/{name}"


def download_list(urls, owner, pid):
    """Скачивает фото поста по прямым ссылкам (поле photo_urls, заполняется вручную/из админки)."""
    out = []
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    for i, u in enumerate(urls):
        name = f"{abs(owner)}_{pid}_v{i}.jpg"
        dst = IMG_DIR / name
        if not dst.exists():
            try:
                r = requests.get(u, headers=UA, timeout=60)
                r.raise_for_status()
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
                im.thumbnail((1600, 1600))
                im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
            except Exception as e:  # noqa
                print("Фото не скачалось:", u[:80], e, file=sys.stderr)
                continue
        out.append(f"img/news/{name}")
    return out


def all_photos(attachments):
    out = []
    for a in attachments or []:
        if a.get("type") == "photo":
            sizes = a["photo"].get("sizes") or []
            if sizes:
                out.append(max(sizes, key=lambda s: s.get("width", 0) * s.get("height", 0)).get("url", ""))
    return [u for u in out if u][:12]


def best_photo(attachments):
    for a in attachments or []:
        if a.get("type") == "photo":
            sizes = a["photo"].get("sizes") or []
            if sizes:
                return max(sizes, key=lambda s: s.get("width", 0) * s.get("height", 0)).get("url", "")
        if a.get("type") == "video":
            imgs = a["video"].get("image") or []
            if imgs:
                return max(imgs, key=lambda s: s.get("width", 0)).get("url", "")
    return ""


def api(method, **params):
    params.update(access_token=TOKEN, v="5.199")
    r = requests.get(f"https://api.vk.com/method/{method}", params=params, timeout=30).json()
    if "error" in r:
        raise RuntimeError(r["error"].get("error_msg"))
    return r["response"]


def from_api_item(p):
    text = p.get("text", "")
    if not text and p.get("copy_history"):
        text = p["copy_history"][0].get("text", "")
    atts = p.get("attachments") or (p.get("copy_history") or [{}])[0].get("attachments")
    urls = all_photos(atts) or [u for u in [best_photo(atts)] if u]
    imgs = [x for x in (save_image(u, p["owner_id"], p["id"], i) for i, u in enumerate(urls)) if x]
    return {
        "id": p["id"],
        "owner": p["owner_id"],
        "source": "vk",
        "url": post_url(p["owner_id"], p["id"]),
        "date": time.strftime("%Y-%m-%d", time.gmtime(p["date"])),
        "title": "",
        "text": text.strip(),
        "image": imgs[0] if imgs else "",
        "images": imgs,
    }


def via_og(owner, pid):
    url = f"https://vk.com/wall{owner}_{pid}"
    r = requests.get(url, headers=UA, timeout=30)
    r.encoding = r.encoding or "utf-8"
    page = r.text

    def meta(prop):
        m = re.search(r'<meta[^>]+property="%s"[^>]+content="([^"]*)"' % re.escape(prop), page) or \
            re.search(r'<meta[^>]+content="([^"]*)"[^>]+property="%s"' % re.escape(prop), page)
        return html.unescape(m.group(1)).strip() if m else ""

    text = re.sub(r"\s*\.{3}\s*Смотрите полностью ВКонтакте\.?\s*$", "…", meta("og:description")).strip()
    img = meta("og:image")
    if not text and not img:
        raise RuntimeError("превью поста недоступно")
    saved = save_image(img, owner, pid)
    date = ""
    m = re.search(r'"date":\s*(\d{10})', page)
    if m:  # дата публикации поста, по Москве
        date = time.strftime("%Y-%m-%d", time.gmtime(int(m.group(1)) + 3 * 3600))
    return {
        "id": pid, "owner": owner, "source": "vk", "url": post_url(owner, pid), "date": date,
        "title": "", "text": text, "image": saved, "images": [saved] if saved else [],
    }


def main():
    old = {}
    manual = []
    if OUT.exists():
        try:
            for n in json.loads(OUT.read_text(encoding="utf-8")):
                if n.get("source") == "manual":
                    manual.append(n)
                else:
                    old[(n.get("owner", GROUP_ID), n["id"])] = n
        except Exception:
            pass
    hidden = set()
    if HIDDEN.exists():
        try:
            hidden = set(str(x) for x in json.loads(HIDDEN.read_text(encoding="utf-8")))
        except Exception:
            pass

    wanted = read_links()
    result = {}

    if TOKEN:
        try:
            for p in api("wall.get", owner_id=GROUP_ID, count=WALL_COUNT).get("items", []):
                if p.get("is_pinned") and not p.get("text"):
                    continue
                n = from_api_item(p)
                result[(n["owner"], n["id"])] = n
        except Exception as e:
            print("wall.get:", e, file=sys.stderr)
        missing = [w for w in wanted if w not in result]
        for i in range(0, len(missing), 50):
            chunk = missing[i:i + 50]
            try:
                for p in api("wall.getById", posts=",".join(f"{o}_{p}" for o, p in chunk)).get("items", []):
                    n = from_api_item(p)
                    result[(n["owner"], n["id"])] = n
            except Exception as e:
                print("wall.getById:", e, file=sys.stderr)

    for key in wanted:
        if key in result:
            continue
        prev = old.get(key)
        if prev and prev.get("text") and prev.get("date"):
            result[key] = prev
            continue
        try:
            result[key] = via_og(*key)
        except Exception as e:
            print(f"Пост {key}: {e}", file=sys.stderr)
            if prev:
                result[key] = prev

    # Новости, отредактированные в админке, не перезаписываем
    for key in list(result):
        prev = old.get(key) or {}
        if prev.get("edited"):
            result[key] = prev
            continue
        n = result[key]
        for f in ("title", "date"):
            if prev.get(f) and not n.get(f):
                n[f] = prev[f]
    for key in list(result):
        if f"{key[0]}_{key[1]}" in hidden:
            del result[key]

    # Фото по прямым ссылкам (photo_urls) -> в репозиторий
    for n in list(result.values()) + manual:
        urls = n.get("photo_urls")
        if not urls:
            continue
        imgs = download_list(urls, n.get("owner", GROUP_ID), n["id"])
        if imgs:
            n["images"] = imgs
            n["image"] = imgs[0]
            n.pop("photo_urls", None)

    items = list(result.values()) + manual
    items.sort(key=lambda n: (n.get("date") or "", str(n["id"]).zfill(20)), reverse=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Новостей на сайте: {len(items)}")


if __name__ == "__main__":
    main()
