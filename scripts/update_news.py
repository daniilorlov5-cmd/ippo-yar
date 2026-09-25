"""Собирает новости сайта из постов ВКонтакте.

Источники постов:
  1. data/vk-links.txt — ссылки, добавленные вручную (по одной в строке).
  2. Если задан секрет VK_TOKEN — ещё и последние записи со стены группы.

Без токена текст и фото берутся из открытого превью поста (og-теги).
С токеном — через VK API (полный текст, дата, фото в хорошем качестве).
"""
import io, json, os, re, sys, time, html
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LINKS = ROOT / "data" / "vk-links.txt"
OUT = ROOT / "data" / "news.json"
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


def save_image(url, owner, pid):
    if not url:
        return ""
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{abs(owner)}_{pid}.jpg"
    dst = IMG_DIR / name
    if not dst.exists():
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            im.thumbnail((900, 900))
            im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
        except Exception as e:  # noqa
            print("Фото не скачалось:", url, e, file=sys.stderr)
            return ""
    return f"img/news/{name}"


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
    photo = best_photo(p.get("attachments")) or best_photo((p.get("copy_history") or [{}])[0].get("attachments"))
    return {
        "id": p["id"],
        "owner": p["owner_id"],
        "url": post_url(p["owner_id"], p["id"]),
        "date": time.strftime("%Y-%m-%d", time.gmtime(p["date"])),
        "text": text.strip(),
        "image": save_image(photo, p["owner_id"], p["id"]),
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

    text = meta("og:description")
    img = meta("og:image")
    if not text and not img:
        raise RuntimeError("превью поста недоступно")
    return {
        "id": pid, "owner": owner, "url": post_url(owner, pid), "date": "",
        "text": text, "image": save_image(img, owner, pid),
    }


def main():
    old = {}
    if OUT.exists():
        try:
            for n in json.loads(OUT.read_text(encoding="utf-8")):
                old[(n.get("owner", GROUP_ID), n["id"])] = n
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
        if prev and prev.get("text"):
            result[key] = prev
            continue
        try:
            result[key] = via_og(*key)
        except Exception as e:
            print(f"Пост {key}: {e}", file=sys.stderr)
            if prev:
                result[key] = prev

    # Сохраняем вручную поправленные заголовки/даты
    for key, n in result.items():
        prev = old.get(key) or {}
        for f in ("title", "date"):
            if prev.get(f) and not n.get(f):
                n[f] = prev[f]
        if prev.get("title"):
            n["title"] = prev["title"]

    items = sorted(result.values(), key=lambda n: (n.get("date") or "", n["id"]), reverse=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Новостей на сайте: {len(items)}")


if __name__ == "__main__":
    main()
