(function () {
  "use strict";

  // Мобильное меню
  var btn = document.querySelector(".openmenu");
  var menu = document.querySelector(".main_menu");
  if (btn && menu) {
    btn.addEventListener("click", function () {
      var open = menu.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  function getJSON(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    });
  }

  function esc(s) {
    return String(s || "").replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // ---------- Слайдер ----------
  var slider = document.querySelector(".main_slider2");
  if (slider) {
    var fallback = ["img/main.jpg"];
    getJSON("data/slider.json")
      .then(function (list) { return list && list.length ? list : fallback; })
      .catch(function () { return fallback; })
      .then(buildSlider);
  }

  function buildSlider(list) {
    var slides = list.map(function (src, i) {
      var d = document.createElement("div");
      d.className = "image" + (i === 0 ? " active" : "");
      if (i < 2) d.style.backgroundImage = "url('" + src + "')";
      d.setAttribute("data-src", src);
      slider.appendChild(d);
      return d;
    });
    if (slides.length < 2) return;
    var n = slides.length, cur = 0, timer, buttons = [], count;
    function load(i) { var d = slides[(i + n) % n]; if (!d.style.backgroundImage) d.style.backgroundImage = "url('" + d.getAttribute("data-src") + "')"; }
    if (n <= 10) {
      var dots = document.createElement("div");
      dots.className = "dots";
      buttons = slides.map(function (_, i) {
        var b = document.createElement("button");
        b.type = "button";
        b.setAttribute("aria-label", "Фото " + (i + 1));
        if (i === 0) b.className = "active";
        b.addEventListener("click", function () { show(i); restart(); });
        dots.appendChild(b);
        return b;
      });
      slider.appendChild(dots);
    } else {
      count = document.createElement("div");
      count.className = "sl_count";
      count.textContent = "1 / " + n;
      slider.appendChild(count);
    }
    ["prev", "next"].forEach(function (k) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "sl_btn sl_" + k;
      b.setAttribute("aria-label", k === "prev" ? "Предыдущее фото" : "Следующее фото");
      b.textContent = k === "prev" ? "‹" : "›";
      b.addEventListener("click", function () { show(cur + (k === "prev" ? -1 : 1)); restart(); });
      slider.appendChild(b);
    });
    function show(i) {
      slides[cur].classList.remove("active"); if (buttons[cur]) buttons[cur].classList.remove("active");
      cur = (i + n) % n;
      load(cur); load(cur + 1);
      slides[cur].classList.add("active"); if (buttons[cur]) buttons[cur].classList.add("active");
      if (count) count.textContent = (cur + 1) + " / " + n;
    }
    function restart() { clearInterval(timer); timer = setInterval(function () { show(cur + 1); }, 5000); }
    var x0 = null;
    slider.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    slider.addEventListener("touchend", function (e) {
      if (x0 === null) return; var d = e.changedTouches[0].clientX - x0; x0 = null;
      if (Math.abs(d) > 40) { show(cur + (d < 0 ? 1 : -1)); restart(); }
    });
    restart();
  }

  // ---------- Новости ----------
  var feed = document.querySelector("[data-news]");
  if (feed) {
    var limit = parseInt(feed.getAttribute("data-news"), 10) || 0;
    getJSON("data/news.json")
      .then(function (items) { renderFeed(items || [], limit); })
      .catch(function () { renderFeed([], limit); });
  }

  function cleanText(t) {
    return String(t || "").replace(/\s*\.{3}\s*Смотрите полностью ВКонтакте\.?\s*$/i, "…").trim();
  }

  function titleOf(n) {
    if (n.title) return n.title;
    var t = cleanText(n.text).split(/\n|(?<=[а-яёa-z»)]{3}[.!?])\s+(?=[А-ЯЁA-Z«"\d])/)[0] || "Новость отделения";
    t = t.replace(/…$/, "");
    return t.length > 110 ? t.slice(0, 107).replace(/\s+\S*$/, "") + "…" : t;
  }

  function fmtDate(d) {
    if (!d) return "";
    var dt = new Date(d + "T12:00:00");
    return isNaN(dt) ? "" : dt.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
  }

  function sortNews(items) {
    return items.slice().sort(function (a, b) {
      return (b.date || "").localeCompare(a.date || "") || String(b.id).localeCompare(String(a.id), undefined, { numeric: true });
    });
  }

  function renderFeed(items, limit) {
    items = sortNews(items);
    if (limit) items = items.slice(0, limit);
    if (!items.length) {
      feed.innerHTML = '<p class="news_empty">Новости появятся здесь в ближайшее время. Пока их можно читать в <a href="https://vk.ru/club234054681" target="_blank" rel="noopener">группе ВКонтакте</a>.</p>';
      return;
    }
    feed.innerHTML = items.map(function (n) {
      var link = "news-item.html?id=" + encodeURIComponent(n.id);
      var text = cleanText(n.text).replace(/\n+/g, " ");
      var short = text.length > 300 ? text.slice(0, 297).replace(/\s+\S*$/, "") + "…" : text;
      var date = fmtDate(n.date);
      return '<div class="news">' +
        '<h4><a href="' + link + '">' + esc(titleOf(n)) + "</a></h4>" +
        '<div class="body">' + (n.image ? '<a href="' + link + '"><img src="' + esc(n.image) + '" alt="" loading="lazy"></a>' : "") +
        "<div><p>" + esc(short) + "</p></div></div>" +
        '<div class="news_foot"><a class="more" href="' + link + '">Читать полностью</a>' +
        (date ? '<span class="news_date">' + date + "</span>" : "") + "</div>" +
        "</div>";
    }).join("");
  }

  // ---------- Страница новости ----------
  var article = document.querySelector("[data-news-item]");
  if (article) {
    var id = new URLSearchParams(location.search).get("id");
    getJSON("data/news.json").then(function (items) {
      var n = (items || []).filter(function (x) { return String(x.id) === id; })[0];
      if (!n) { article.innerHTML = '<h1>Новость не найдена</h1><p><a href="news.html">Все новости</a></p>'; return; }
      document.title = titleOf(n) + " — Ярославское отделение ИППО";
      var pics = (n.images && n.images.length ? n.images : (n.image ? [n.image] : []));
      var paras = cleanText(n.text).split(/\n+/).map(function (p) { return p.trim(); }).filter(Boolean)
        .map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("");
      var date = fmtDate(n.date);
      article.innerHTML =
        '<p class="back"><a href="news.html">← Все новости</a></p>' +
        "<h1>" + esc(titleOf(n)) + "</h1>" +
        (date ? '<div class="article_date">' + date + "</div>" : "") +
        (pics.length ? carouselHtml(pics) : "") +
        '<div class="article_text">' + paras + "</div>" +
        (n.url ? '<p class="source">Источник: <a href="' + esc(n.url) + '" target="_blank" rel="noopener">запись во ВКонтакте</a></p>' : "");
      if (pics.length) initCarousel(article.querySelector(".carousel"), pics);
    }).catch(function () {
      article.innerHTML = "<h1>Не удалось загрузить новость</h1>";
    });
  }

  function carouselHtml(pics) {
    var many = pics.length > 1;
    return '<div class="carousel' + (many ? " many" : "") + '">' +
      '<div class="car_stage">' +
        '<div class="car_track">' + pics.map(function (p, i) {
          return '<div class="car_slide"><img src="' + esc(p) + '" alt="Фото ' + (i + 1) + '"' + (i ? ' loading="lazy"' : "") + "></div>";
        }).join("") + "</div>" +
        (many ? '<button class="car_btn car_prev" type="button" aria-label="Предыдущее фото">‹</button>' +
                '<button class="car_btn car_next" type="button" aria-label="Следующее фото">›</button>' +
                '<div class="car_count"><span>1</span> / ' + pics.length + "</div>" : "") +
        '<button class="car_zoom" type="button" aria-label="Открыть на весь экран">⤢</button>' +
      "</div>" +
      (many ? '<div class="car_thumbs">' + pics.map(function (p, i) {
        return '<button type="button" class="car_thumb' + (i ? "" : " on") + '" data-i="' + i + '" aria-label="Фото ' + (i + 1) + '"><img src="' + esc(p) + '" alt="" loading="lazy"></button>';
      }).join("") + "</div>" : "") +
      "</div>";
  }

  function initCarousel(root, pics) {
    var track = root.querySelector(".car_track"), cur = 0, n = pics.length;
    var thumbs = root.querySelectorAll(".car_thumb"), count = root.querySelector(".car_count span");
    function go(i, instant) {
      cur = (i + n) % n;
      track.style.transition = instant ? "none" : "";
      track.style.transform = "translateX(" + (-100 * cur) + "%)";
      if (count) count.textContent = cur + 1;
      thumbs.forEach(function (t, k) { t.classList.toggle("on", k === cur); });
      if (thumbs[cur]) thumbs[cur].scrollIntoView({ block: "nearest", inline: "center", behavior: instant ? "auto" : "smooth" });
    }
    var prev = root.querySelector(".car_prev"), next = root.querySelector(".car_next");
    if (prev) prev.onclick = function () { go(cur - 1); };
    if (next) next.onclick = function () { go(cur + 1); };
    thumbs.forEach(function (t) { t.onclick = function () { go(+t.getAttribute("data-i")); }; });
    var lb = lightbox(pics, function (i) { go(i, true); });
    root.querySelector(".car_zoom").onclick = function () { lb(cur); };
    track.addEventListener("click", function () { if (!moved) lb(cur); });
    // свайп
    var x0 = null, dx = 0, moved = false, w = 1;
    track.addEventListener("touchstart", function (e) { if (n < 2) return; x0 = e.touches[0].clientX; dx = 0; moved = false; w = track.clientWidth; track.style.transition = "none"; }, { passive: true });
    track.addEventListener("touchmove", function (e) {
      if (x0 === null) return; dx = e.touches[0].clientX - x0; if (Math.abs(dx) > 6) moved = true;
      track.style.transform = "translateX(calc(" + (-100 * cur) + "% + " + dx + "px))";
    }, { passive: true });
    track.addEventListener("touchend", function () {
      if (x0 === null) return; x0 = null; track.style.transition = "";
      if (Math.abs(dx) > w * 0.15) go(cur + (dx < 0 ? 1 : -1)); else go(cur);
      setTimeout(function () { moved = false; }, 50);
    });
    root.setAttribute("tabindex", "0");
    root.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") go(cur - 1);
      if (e.key === "ArrowRight") go(cur + 1);
    });
  }

  function lightbox(pics, onChange) {
    var box = document.createElement("div");
    box.className = "lightbox";
    box.innerHTML = '<button class="lb_close" aria-label="Закрыть">×</button>' +
      (pics.length > 1 ? '<button class="lb_prev" aria-label="Назад">‹</button><button class="lb_next" aria-label="Вперёд">›</button><div class="lb_count"></div>' : "") +
      '<img alt="">';
    document.body.appendChild(box);
    var img = box.querySelector("img"), cnt = box.querySelector(".lb_count"), cur = 0;
    function show(i) { cur = (i + pics.length) % pics.length; img.src = pics[cur]; if (cnt) cnt.textContent = (cur + 1) + " / " + pics.length; }
    function open(i) { show(i); box.classList.add("open"); document.body.style.overflow = "hidden"; }
    function close() { box.classList.remove("open"); document.body.style.overflow = ""; if (onChange) onChange(cur); }
    box.querySelector(".lb_close").onclick = close;
    if (pics.length > 1) {
      box.querySelector(".lb_prev").onclick = function (e) { e.stopPropagation(); show(cur - 1); };
      box.querySelector(".lb_next").onclick = function (e) { e.stopPropagation(); show(cur + 1); };
    }
    box.addEventListener("click", function (e) { if (e.target === box) close(); });
    var x0 = null;
    box.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    box.addEventListener("touchend", function (e) {
      if (x0 === null) return; var d = e.changedTouches[0].clientX - x0; x0 = null;
      if (Math.abs(d) > 50 && pics.length > 1) show(cur + (d < 0 ? 1 : -1));
    });
    document.addEventListener("keydown", function (e) {
      if (!box.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") show(cur - 1);
      if (e.key === "ArrowRight") show(cur + 1);
    });
    return open;
  }
})();
