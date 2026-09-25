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
      d.style.backgroundImage = "url('" + src + "')";
      slider.appendChild(d);
      return d;
    });
    if (slides.length < 2) return;
    var dots = document.createElement("div");
    dots.className = "dots";
    var buttons = slides.map(function (_, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("aria-label", "Фото " + (i + 1));
      if (i === 0) b.className = "active";
      b.addEventListener("click", function () { show(i); restart(); });
      dots.appendChild(b);
      return b;
    });
    slider.appendChild(dots);
    var cur = 0, timer;
    function show(n) {
      slides[cur].classList.remove("active"); buttons[cur].classList.remove("active");
      cur = (n + slides.length) % slides.length;
      slides[cur].classList.add("active"); buttons[cur].classList.add("active");
    }
    function restart() { clearInterval(timer); timer = setInterval(function () { show(cur + 1); }, 5000); }
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
    var t = cleanText(n.text).split(/\n|(?<=[.!?])\s/)[0] || "Новость отделения";
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
      var paras = cleanText(n.text).split(/\n+/).filter(Boolean).map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("");
      var date = fmtDate(n.date);
      article.innerHTML =
        '<p class="back"><a href="news.html">← Все новости</a></p>' +
        "<h1>" + esc(titleOf(n)) + "</h1>" +
        (date ? '<div class="article_date">' + date + "</div>" : "") +
        (pics.length ? '<img class="article_cover" src="' + esc(pics[0]) + '" alt="">' : "") +
        '<div class="article_text">' + paras + "</div>" +
        (pics.length > 1 ? '<div class="gallery">' + pics.map(function (p, i) {
          return '<a href="' + esc(p) + '" data-i="' + i + '"><img src="' + esc(p) + '" alt="" loading="lazy"></a>';
        }).join("") + "</div>" : "") +
        (n.url ? '<p class="source">Источник: <a href="' + esc(n.url) + '" target="_blank" rel="noopener">запись во ВКонтакте</a></p>' : "");
      initLightbox(pics);
    }).catch(function () {
      article.innerHTML = "<h1>Не удалось загрузить новость</h1>";
    });
  }

  function initLightbox(pics) {
    var box = document.createElement("div");
    box.className = "lightbox";
    box.innerHTML = '<button class="lb_close" aria-label="Закрыть">×</button><button class="lb_prev" aria-label="Назад">‹</button><img alt=""><button class="lb_next" aria-label="Вперёд">›</button>';
    document.body.appendChild(box);
    var img = box.querySelector("img"), cur = 0;
    function open(i) { cur = (i + pics.length) % pics.length; img.src = pics[cur]; box.classList.add("open"); }
    function close() { box.classList.remove("open"); }
    document.querySelectorAll(".gallery a, .article_cover").forEach(function (a) {
      a.addEventListener("click", function (e) { e.preventDefault(); open(parseInt(a.getAttribute("data-i") || "0", 10)); });
    });
    box.querySelector(".lb_close").onclick = close;
    box.querySelector(".lb_prev").onclick = function () { open(cur - 1); };
    box.querySelector(".lb_next").onclick = function () { open(cur + 1); };
    box.addEventListener("click", function (e) { if (e.target === box) close(); });
    document.addEventListener("keydown", function (e) {
      if (!box.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") open(cur - 1);
      if (e.key === "ArrowRight") open(cur + 1);
    });
  }
})();
