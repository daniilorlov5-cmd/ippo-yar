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
    var full = feed.hasAttribute("data-full");
    getJSON("data/news.json")
      .then(function (items) { render(items || [], limit, full); })
      .catch(function () { render([], limit, full); });
  }

  function titleOf(n) {
    if (n.title) return n.title;
    var t = (n.text || "").split(/\n|(?<=[.!?])\s/)[0] || "Новость отделения";
    return t.length > 120 ? t.slice(0, 117).trim() + "…" : t;
  }

  function render(items, limit, full) {
    items = items.slice().sort(function (a, b) { return (b.date || "").localeCompare(a.date || "") || b.id - a.id; });
    if (limit) items = items.slice(0, limit);
    if (!items.length) {
      feed.innerHTML = '<p class="news_empty">Новости появятся здесь в ближайшее время. Пока их можно читать в <a href="https://vk.ru/club234054681" target="_blank" rel="noopener">группе ВКонтакте</a>.</p>';
      return;
    }
    feed.innerHTML = items.map(function (n) {
      var text = n.text || "";
      var body;
      if (full) {
        body = text.split(/\n+/).filter(Boolean).map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("");
      } else {
        var short = text.length > 320 ? text.slice(0, 317).replace(/\s+\S*$/, "") + "…" : text;
        body = "<p>" + esc(short) + "</p>";
      }
      var date = n.date ? new Date(n.date).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" }) : "";
      return '<div class="news">' +
        '<h4><a href="' + esc(n.url) + '" target="_blank" rel="noopener">' + esc(titleOf(n)) + "</a></h4>" +
        (date ? '<div class="date">' + date + "</div>" : "") +
        '<div class="body">' + (n.image ? '<img src="' + esc(n.image) + '" alt="" loading="lazy">' : "") +
        "<div>" + body + '<a class="more" href="' + esc(n.url) + '" target="_blank" rel="noopener">' + (full ? "Запись во ВКонтакте" : "Читать полностью") + "</a></div></div>" +
        "</div>";
    }).join("");
  }
})();
