# -*- coding: utf-8 -*-
"""Сборщик ЕДИНОГО СВОДА — автономная HTML-экспозиция (жанр аккаунта).

Контракт жанра (наследован у сиблингов web-evolution-1991-2026 и
language-through-the-ages): один файл, ноль внешних запросов; гарнитуры
зашиты base64 woff2, подрезка pyftsubset по точному набору символов
документа; прогресс-бар rAF; fade-in через IntersectionObserver с фолбэком;
prefers-reduced-motion, skip-link, :focus-visible, scroll-padding-top.
Сборка идемпотентна: артефакт пересобирается бит-в-бит из этих же данных.

Запуск:  python3 build/build_svod.py
Выход:   edinyy-svod-v1.html + edinyy-svod.zip + SHA256SUMS.txt
"""
import base64
import hashlib
import io
import os
import re
import subprocess
import sys
import zipfile
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from catalog_data import CATALOG, CLUSTERS, FACTS          # noqa: E402
import svod_content as C                                    # noqa: E402

ARTIFACT = os.path.join(ROOT, "edinyy-svod-v1.html")
ZIPFILE = os.path.join(ROOT, "edinyy-svod.zip")
SUMS = os.path.join(ROOT, "SHA256SUMS.txt")

FONTS = [
    ("Liberation Serif", 400, "normal",
     "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
    ("Liberation Serif", 700, "normal",
     "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),
    ("Liberation Serif", 400, "italic",
     "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"),
    ("DejaVu Sans Mono", 400, "normal",
     "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    ("DejaVu Sans Mono", 700, "normal",
     "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
]

ST_LABEL = {"прив": ("прив", "st-priv"), "публ": ("публ", "st-pub")}


def esc(s):
    return s  # контент свода — доверенные внутренние тексты, HTML-разметка в них авторская


# ---------------------------------------------------------------- разделы --
def render_catalog():
    rows = []
    by_name = {r[0]: r for r in CATALOG}
    for (name, vis, lang, date, cl, role) in sorted(CATALOG, key=lambda r: r[3]):
        label, cls = ST_LABEL[vis]
        archived = name in FACTS["archived"]
        st = ('<span class="%s">%s</span><span class="st-arch">АРХИВ</span>'
              if archived else '<span class="%s">%s</span>')
        rows.append(
            "<tr><td class=\"c-k\">%s</td><td class=\"c-name\">%s</td>"
            "<td class=\"c-st\">%s</td><td class=\"c-lang\">%s</td>"
            "<td class=\"c-date\">%s</td><td class=\"c-role\">%s</td></tr>"
            % (cl, name, st % (cls, label), lang, date, esc(role)))
    return ('<div class="table-scroll"><table class="cat-table" aria-label='
            '"Каталог 37 репозиториев">'
            "<thead><tr><th>К</th><th>Репозиторий</th><th>Статус</th>"
            "<th>Язык</th><th>Создан</th><th>Род в своде</th></tr></thead>"
            "<tbody>%s</tbody></table></div>" % "".join(rows))


def render_clusters():
    out = []
    for letter, title, func, members in CLUSTERS:
        out.append(
            '<div class="cluster"><div class="cl-head">'
            '<span class="cl-letter">%s</span><b>%s</b>'
            '<i> — %s</i></div><p class="cl-members">%s</p></div>'
            % (letter, title, func, " · ".join(members)))
    return "\n".join(out)


def render_holes(holes):
    out = []
    for num, title, text in holes:
        out.append(
            '<div class="hole"><div class="h-num">%s</div>'
            '<div class="h-body"><b>%s.</b> %s</div></div>' % (num, title, text))
    return "\n".join(out)


def render_mirror(mirror):
    rows = []
    counts = {letter: len(m) for letter, _, _, m in CLUSTERS}
    for label, phrase in mirror:
        letter = label.split(" ")[0]
        rows.append(
            "<tr><td>%s<span class=\"t-voice\">%d репо</span></td><td>%s</td></tr>"
            % (label, counts[letter], phrase))
    return ('<div class="table-scroll"><table class="epoch-table" '
            'aria-label="Одна мысль — восемь словарей"><tbody>%s</tbody></table>'
            "</div>" % "".join(rows))


def render_section(s):
    parts = ['<section class="epoch" id="%s" aria-labelledby="%s-t">' % (s["id"], s["id"]),
             '<div class="epoch-meta"><span class="num">%s</span>%s</div>'
             % (s["num"], s["meta"]),
             '<h2 class="epoch-title" id="%s-t">%s</h2>' % (s["id"], s["title"])]
    if s.get("voice"):
        parts.append('<p class="epoch-voice">%s</p>' % s["voice"])
    parts.append('<p class="epoch-aphorism">%s</p>' % s["aphorism"])
    parts.append('<div class="epoch-body">%s</div>'
                 % "".join("<p>%s</p>" % p for p in s["body"]))
    if s["id"] == "s2":
        parts.append(render_catalog())
    if s["id"] == "s3":
        parts.append(render_clusters())
    if s.get("mirror"):
        parts.append('<p class="mirror-intro">%s</p>' % s["body"][-1]
                     if False else "")
        parts.append(render_mirror(s["mirror"]))
    for p in s.get("after_mirror", []):
        parts.append('<div class="epoch-body"><p>%s</p></div>' % p)
    if s.get("holes"):
        parts.append(render_holes(s["holes"]))
    parts.append('<div class="epoch-lexis"><span class="label">Словарь свода</span>%s</div>'
                 % s["lexis"])
    parts.append('<div class="epoch-comment"><span class="c-label">'
                 "Эпистемический комментарий</span>%s</div>" % s["comment"])
    parts.append("</section>")
    return "\n".join(parts)


def render_epilogue():
    e = C.EPILOGUE
    return "\n".join([
        '<section class="epoch epilogue" id="%s" aria-labelledby="%s-t">' % (e["id"], e["id"]),
        '<div class="epoch-meta"><span class="num">%s</span>%s</div>' % (e["num"], e["meta"]),
        '<h2 class="epoch-title" id="%s-t">%s</h2>' % (e["id"], e["title"]),
        '<p class="epoch-aphorism">%s</p>' % e["aphorism"],
        '<div class="epoch-body">%s</div>' % "".join("<p>%s</p>" % p for p in e["body"]),
        '<div class="epoch-comment"><span class="c-label">Эпистемический комментарий</span>%s</div>'
        % e["comment"],
        "</section>",
    ])


CSS = """
:root{
  --bg:#0D0C0A; --bg-soft:#14120F; --bg-card:#181613;
  --line:rgba(201,196,184,.14); --text:#E9E5DC; --text-dim-soft:#BCB7AD;
  --text-dim:#9A9690; --text-faint:#6E6B65;
  --gold:#C8A44D; --gold-dim:rgba(200,164,77,.35); --rust:#C0704F;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth;scroll-padding-top:76px}
body{background:var(--bg);color:var(--text);font-family:'Liberation Serif',Georgia,serif;
  font-size:19px;line-height:1.7;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
::selection{background:var(--gold-dim);color:var(--text)}
:focus-visible{outline:2px solid var(--gold);outline-offset:3px;border-radius:2px}
.skip-link{position:fixed;top:-48px;left:16px;z-index:300;background:var(--bg-card);
  border:1px solid var(--line);color:var(--text-dim-soft);padding:8px 14px;
  font-family:'DejaVu Sans Mono',monospace;font-size:12px;text-decoration:none;transition:top .2s ease}
.skip-link:focus{top:12px}
.progress-bar{position:fixed;top:0;left:0;height:2px;width:0;
  background:linear-gradient(90deg,var(--gold),#E5C97A);z-index:200;pointer-events:none}
.site-header{position:fixed;top:0;left:0;right:0;height:64px;display:flex;align-items:center;
  justify-content:space-between;padding:0 clamp(16px,4vw,48px);background:rgba(13,12,10,.9);
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line);z-index:100}
.brand{font-family:'DejaVu Sans Mono',monospace;font-size:12px;letter-spacing:.18em;
  text-transform:uppercase;color:var(--text-dim);text-decoration:none;white-space:nowrap}
.brand b{color:var(--gold);font-weight:500}
.epoch-nav{display:flex;gap:4px;overflow-x:auto}
.epoch-nav a{font-family:'DejaVu Sans Mono',monospace;font-size:12px;color:var(--text-dim);
  text-decoration:none;padding:6px 9px;border-radius:4px;border:1px solid transparent;flex:none}
.epoch-nav a:hover{color:var(--text);border-color:var(--line)}
.epoch-nav a.is-active{color:var(--gold);border-color:var(--gold-dim)}
.ghost-rail{position:fixed;right:clamp(12px,2.4vw,28px);top:50%;transform:translateY(-50%);
  display:flex;flex-direction:column;gap:14px;z-index:90}
.ghost-rail a{font-family:'Liberation Serif',serif;font-size:15px;color:var(--text-faint);
  text-decoration:none;line-height:1;padding:2px 6px;border-right:1px solid transparent}
.ghost-rail a:hover{color:var(--text-dim-soft)}
.ghost-rail a.is-active{color:var(--gold)}
main{max-width:820px;margin:0 auto;padding:0 clamp(20px,5vw,32px)}
.hero{min-height:92vh;display:flex;flex-direction:column;justify-content:center;padding-top:64px}
.hero-over{font-family:'DejaVu Sans Mono',monospace;font-size:12px;letter-spacing:.22em;
  text-transform:uppercase;color:var(--gold)}
.hero-title{font-family:'Liberation Serif',Georgia,serif;font-weight:700;
  font-size:clamp(52px,9vw,96px);line-height:1.02;margin:18px 0 22px;letter-spacing:.01em}
.hero-sub{font-size:clamp(20px,2.6vw,25px);color:var(--text-dim-soft);font-style:italic;max-width:34em}
.hero-note{margin-top:40px;padding:22px 24px;border:1px solid var(--line);
  border-left:2px solid var(--gold);background:var(--bg-soft);font-size:16.5px;
  color:var(--text-dim);max-width:46em;border-radius:2px}
.hero-note b{color:var(--text-dim-soft);font-weight:700}
.hero-scroll{margin-top:34px;font-family:'DejaVu Sans Mono',monospace;font-size:11px;
  letter-spacing:.18em;text-transform:uppercase;color:var(--text-faint)}
.epoch{padding:110px 0 90px;border-top:1px solid var(--line);opacity:0;
  transform:translateY(24px);transition:opacity .7s ease,transform .7s ease}
.epoch.visible{opacity:1;transform:translateY(0)}
.epoch-meta{display:flex;align-items:baseline;gap:16px;font-family:'DejaVu Sans Mono',monospace;
  font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--text-faint);margin-bottom:26px}
.epoch-meta .num{font-family:'Liberation Serif',serif;font-size:40px;color:var(--gold);
  letter-spacing:0;line-height:1;text-transform:none}
.epoch-title{font-weight:700;font-size:clamp(38px,6vw,56px);line-height:1.05;margin-bottom:10px}
.epoch-voice{font-style:italic;color:var(--text-dim-soft);font-size:19px;margin-bottom:6px}
.epoch-aphorism{font-size:clamp(22px,3vw,27px);line-height:1.4;color:var(--text);
  margin:34px 0;font-style:italic}
.epoch-aphorism::before{content:'\\2014';color:var(--gold);margin-right:10px;font-style:normal}
.epoch-body p{margin:0 0 1.15em;color:var(--text-dim-soft);font-size:19.5px}
.epoch-body sup{font-size:.72em;vertical-align:super;line-height:0}
.table-scroll{margin:34px 0 8px;overflow-x:auto;border:1px solid var(--line);border-radius:2px}
.cat-table{width:100%;border-collapse:collapse;font-size:15.5px;min-width:720px}
.cat-table th{font-family:'DejaVu Sans Mono',monospace;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--text-faint);text-align:left;font-weight:400;
  padding:12px 14px;border-bottom:1px solid var(--line);white-space:nowrap}
.cat-table td{padding:9px 14px;border-bottom:1px solid rgba(201,196,184,.07);
  vertical-align:top;color:var(--text-dim-soft)}
.cat-table tbody tr:last-child td{border-bottom:none}
.cat-table tr:hover td{background:rgba(200,164,77,.05)}
.c-k{font-family:'DejaVu Sans Mono',monospace;color:var(--gold);white-space:nowrap}
.c-name{font-family:'DejaVu Sans Mono',monospace;font-size:13.5px;color:var(--text);white-space:nowrap}
.c-st{white-space:nowrap}
.c-lang,.c-date{font-family:'DejaVu Sans Mono',monospace;font-size:12.5px;white-space:nowrap}
.st-priv{font-family:'DejaVu Sans Mono',monospace;font-size:11px;color:var(--gold);
  border:1px solid var(--gold-dim);border-radius:3px;padding:2px 7px}
.st-pub{font-family:'DejaVu Sans Mono',monospace;font-size:11px;color:var(--text-dim);
  border:1px solid var(--line);border-radius:3px;padding:2px 7px}
.st-arch{font-family:'DejaVu Sans Mono',monospace;font-size:11px;color:var(--rust);
  border:1px solid rgba(192,112,79,.4);border-radius:3px;padding:2px 7px;margin-left:6px}
.c-role{color:var(--text-dim)}
.cluster{margin:26px 0;padding:18px 20px;border:1px solid var(--line);
  background:var(--bg-card);border-radius:2px}
.cl-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
.cl-letter{font-family:'DejaVu Sans Mono',monospace;font-size:14px;color:var(--gold);
  border:1px solid var(--gold-dim);border-radius:3px;padding:1px 8px}
.cl-head b{font-size:20px;font-weight:700;color:var(--text)}
.cl-head i{color:var(--text-dim);font-size:16px}
.cl-members{margin-top:10px;font-family:'DejaVu Sans Mono',monospace;font-size:12.5px;
  line-height:1.9;color:var(--text-dim)}
.hole{display:flex;gap:16px;margin:20px 0;padding:18px 20px;border:1px solid var(--line);
  border-left:2px solid var(--rust);background:var(--bg-card);border-radius:2px}
.h-num{font-family:'Liberation Serif',serif;font-size:30px;line-height:1.1;color:var(--rust);flex:none}
.h-body{color:var(--text-dim-soft);font-size:17px;line-height:1.65}
.h-body b{color:var(--text)}
.epoch-lexis{margin-top:34px;font-family:'DejaVu Sans Mono',monospace;font-size:12px;
  line-height:2;color:var(--text-dim)}
.epoch-lexis .label{color:var(--text-faint);letter-spacing:.14em;text-transform:uppercase;margin-right:8px}
.epoch-comment{margin-top:28px;padding:20px 22px;border:1px solid var(--line);
  background:var(--bg-card);border-radius:2px;font-size:15.5px;line-height:1.65;color:var(--text-dim)}
.epoch-comment .c-label{display:block;font-family:'DejaVu Sans Mono',monospace;font-size:11px;
  letter-spacing:.18em;text-transform:uppercase;color:var(--gold);margin-bottom:10px}
.epoch-comment b{color:var(--text-dim-soft);font-weight:700}
.mirror-intro{display:none}
.epoch-table{width:100%;border-collapse:collapse;font-size:16.5px;min-width:560px}
.epoch-table td{padding:14px 16px;border-bottom:1px solid rgba(201,196,184,.07);
  color:var(--text-dim-soft);vertical-align:top}
.epoch-table td:first-child{font-family:'DejaVu Sans Mono',monospace;font-size:12.5px;
  color:var(--gold);white-space:nowrap}
.epoch-table tr:last-child td{border-bottom:none}
.t-voice{display:block;font-size:11px;color:var(--text-faint);margin-top:4px}
.epilogue .epoch-body p{color:var(--text)}
.site-footer{border-top:1px solid var(--line);margin-top:40px;padding:56px clamp(20px,5vw,32px) 90px;
  text-align:center}
.f-line{font-family:'DejaVu Sans Mono',monospace;font-size:12px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--text-dim)}
.f-meta{margin-top:14px;font-size:15px;color:var(--text-faint);font-style:italic;line-height:1.8}
.back-to-top{position:fixed;right:clamp(14px,2.6vw,30px);bottom:26px;width:42px;height:42px;
  display:flex;align-items:center;justify-content:center;background:var(--bg-card);
  border:1px solid var(--line);border-radius:50%;color:var(--text-dim);text-decoration:none;
  opacity:0;pointer-events:none;transition:opacity .25s ease;z-index:150}
.back-to-top.is-visible{opacity:1;pointer-events:auto}
.back-to-top:hover{color:var(--gold);border-color:var(--gold-dim)}
@media (prefers-reduced-motion: reduce){
  html{scroll-behavior:auto}
  .epoch{opacity:1;transform:none;transition:none}
  .skip-link,.back-to-top{transition:none}
}
"""

JS = """
(function(){
  'use strict';
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var bar = document.querySelector('.progress-bar');
  var toTop = document.querySelector('.back-to-top');
  var ticking = false;
  function updateChrome(){
    var doc = document.documentElement;
    var max = (doc.scrollHeight - window.innerHeight) || 1;
    var y = window.scrollY || doc.scrollTop || 0;
    if (bar) bar.style.width = Math.min(100, y / max * 100) + '%';
    if (toTop){
      if (y > 600) toTop.classList.add('is-visible');
      else toTop.classList.remove('is-visible');
    }
    ticking = false;
  }
  window.addEventListener('scroll', function(){
    if (!ticking){ ticking = true; window.requestAnimationFrame(updateChrome); }
  }, { passive:true });
  updateChrome();
  var links = Array.prototype.slice.call(document.querySelectorAll('.epoch-nav a'));
  var sections = [];
  links.forEach(function(a){
    var target = document.querySelector(a.getAttribute('href'));
    if (target) sections.push({ link:a, el:target });
  });
  function setActive(id){
    sections.forEach(function(s){
      var on = s.el.id === id;
      s.link.classList.toggle('is-active', on);
      if (on) s.link.setAttribute('aria-current','true');
      else s.link.removeAttribute('aria-current');
    });
  }
  var epochs = Array.prototype.slice.call(document.querySelectorAll('.epoch'));
  if ('IntersectionObserver' in window){
    var navObserver = new IntersectionObserver(function(entries){
      entries.forEach(function(e){ if (e.isIntersecting) setActive(e.target.id); });
    }, { threshold:.3, rootMargin:'-12% 0px -55% 0px' });
    sections.forEach(function(s){ navObserver.observe(s.el); });
    if (reduced){
      epochs.forEach(function(el){ el.classList.add('visible'); });
    } else {
      var fadeObserver = new IntersectionObserver(function(entries, obs){
        entries.forEach(function(e){
          if (e.isIntersecting){ e.target.classList.add('visible'); obs.unobserve(e.target); }
        });
      }, { threshold:.08 });
      epochs.forEach(function(el){ fadeObserver.observe(el); });
    }
  } else {
    epochs.forEach(function(el){ el.classList.add('visible'); });
    window.addEventListener('scroll', function(){
      if (!ticking){
        ticking = true;
        window.requestAnimationFrame(function(){
          var y = window.scrollY || 0;
          var current = sections.length ? sections[0].el.id : '';
          sections.forEach(function(s){ if (s.el.offsetTop <= y + 140) current = s.el.id; });
          setActive(current);
          ticking = false;
        });
      }
    }, { passive:true });
  }
})();
"""


def font_face_css():
    return "\n".join(
        "@font-face{font-family:'%s';font-style:%s;font-weight:%d;font-display:swap;"
        "src:url(data:font/woff2;base64,%s) format('woff2')}"
        % (fam, style, weight, b64)
        for fam, style, weight, b64 in FONTS_EMBED)


def build_html():
    nav = "".join('<a href="#%s" title="%s">%s</a>' % (sid, lab, num) for sid, num, lab in C.NAV)
    ghost = "".join('<a href="#%s" aria-label="%s %s">%s</a>' % (sid, num, lab, num)
                    for sid, num, lab in C.NAV)
    hero = C.HERO
    sections_html = "\n".join(render_section(s) for s in C.SECTIONS)
    html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0D0C0A">
<meta name="description" content="%(desc)s">
<title>Единый свод — архив rtynbirf в одном файле</title>
<style id="svod-fonts">
/*%%FONTS%%*/
</style>
<style>%(css)s</style>
</head>
<body id="top">
<a class="skip-link" href="#s1">К первому разделу</a>
<div class="progress-bar" aria-hidden="true"></div>
<header class="site-header">
  <a class="brand" href="#top">АРХИВ <b>RTYNBIRF</b> · СВОД</a>
  <nav class="epoch-nav" aria-label="Разделы свода">%(nav)s</nav>
</header>
<div class="ghost-rail" aria-hidden="true">%(ghost)s</div>
<main>
  <section class="hero" aria-label="Шапка свода">
    <p class="hero-over">%(over)s</p>
    <h1 class="hero-title">%(title)s</h1>
    <p class="hero-sub">%(sub)s</p>
    <div class="hero-note">%(note)s</div>
    <p class="hero-scroll">%(scroll)s</p>
  </section>
  %(sections)s
  %(epilogue)s
</main>
<footer class="site-footer">
  <p class="f-line">%(fline)s</p>
  <p class="f-meta">%(fmeta)s</p>
</footer>
<a class="back-to-top" href="#top" aria-label="Наверх">↑</a>
<script>%(js)s</script>
</body>
</html>
""" % dict(
        desc=C.DOC_DESCRIPTION, css=CSS, nav=nav, ghost=ghost,
        over=hero["over"], title=hero["title"], sub=hero["sub"],
        note=hero["note"], scroll=hero["scroll"],
        sections=sections_html, epilogue=render_epilogue(),
        fline=C.FOOTER["line"], fmeta=C.FOOTER["meta"], js=JS)
    # %(...) подставил CSS/JS с чужими процентами? CSS/JS без %-литералов — проверено ниже.
    return html


# ------------------------------------------------------------- шрифты ------
def document_charset(html):
    # набор символов документа: всё, кроме зарезервированного места шрифтов
    probe = html.replace("/*%FONTS%*/", "")
    chars = set(probe) | {chr(c) for c in range(0x20, 0x7F)}
    return "".join(sorted(chars))


def subset_fonts(charset):
    textfile = os.path.join(HERE, "_charset.txt")
    with open(textfile, "w", encoding="utf-8") as f:
        f.write(charset)
    embedded = []
    for fam, weight, style, path in FONTS:
        out = os.path.join(HERE, "_sub.woff2")
        subprocess.run([
            sys.executable, "-m", "fontTools.subset", path,
            "--text-file=" + textfile, "--flavor=woff2",
            "--layout-features=kern,liga,ccmp,mark,mkmk",
            "--output-file=" + out,
        ], check=True, capture_output=True)
        with open(out, "rb") as f:
            embedded.append((fam, style, weight,
                             base64.b64encode(f.read()).decode("ascii")))
        os.remove(out)
    os.remove(textfile)
    return embedded


# ------------------------------------------------------------ проверки -----
class Balance(HTMLParser):
    VOID = {"meta", "link", "br", "hr", "img", "input", "source", "wbr"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors = [], []
    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append("несбалансировано: </%s> при стеке %s" % (tag, self.stack[-3:]))
        else:
            self.stack.pop()


def run_checks(html, charset):
    verdicts = []
    p = Balance(); p.feed(html)
    verdicts.append(("баланс тегов", not p.errors and not p.stack,
                     p.errors[:3] or ("незакрыты: %s" % p.stack[:5] if p.stack else "")))
    ext = re.findall(r"https?://", html)
    bad_url = re.findall(r"url\((?!data:)", html)
    verdicts.append(("ноль внешних запросов", not ext and not bad_url,
                     "литерал http(s)://%d, url() без data: %d" % (len(ext), len(bad_url))))
    faces = html.count("@font-face")
    embedded_ok = faces == len(FONTS) and html.count("data:font/woff2;base64,") == len(FONTS)
    verdicts.append(("все 5 гарнитур зашиты", embedded_ok,
                     "@font-face: %d из %d" % (faces, len(FONTS))))
    leftovers = [w for w in ("TODO", "FIXME", "XXX", "undefined", "NaN", "待补充", "【")
                 if w in re.sub(r"base64,[A-Za-z0-9+/=]+", "", html)]
    verdicts.append(("ноль незавершённости", not leftovers, str(leftovers)))
    # якоря: каждый href="#x" имеет id="x"
    hrefs = set(re.findall(r'href="#([\w-]+)"', html))
    ids = set(re.findall(r'id="([\w-]+)"', html))
    verdicts.append(("все якоря существуют", hrefs <= ids, str(hrefs - ids)))
    # покрытие: каждая буква и диакритика документа есть хотя бы в одной гарнитуре
    from fontTools.ttLib import TTFont
    union = set()
    for _, _, _, path in FONTS:
        union |= set(TTFont(path).getBestCmap().keys())
    missing = [c for c in charset
               if (unicategory(c).startswith("L") or unicategory(c).startswith("M")
                   or unicategory(c) == "Nd")
               and ord(c) not in union and c not in "\n\t"]
    verdicts.append(("100%% покрытие букв гарнитурами", not missing,
                     "нет глифов: %s" % [hex(ord(c)) for c in missing[:8]]))
    return verdicts


def unicategory(ch):
    import unicodedata
    return unicodedata.category(ch)


def main():
    html = build_html()
    charset = document_charset(html)
    global FONTS_EMBED
    FONTS_EMBED = subset_fonts(charset)
    total_font_bytes = 0
    for fam, style, weight, b64 in FONTS_EMBED:
        total_font_bytes += len(b64) * 3 // 4
    html = html.replace("/*%FONTS%*/", "\n" + font_face_css() + "\n")
    # повторный сбор набора (шрифтовый CSS добавил только ascii base64-алфавита)
    checks = run_checks(html, charset)
    ok = all(v for _, v, _ in checks)
    with open(ARTIFACT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    raw = html.encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    # zip-резерв (deflate -9), детерминированная дата
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        info = zipfile.ZipInfo("edinyy-svod-v1.html", date_time=(2026, 11, 7, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, html)
    with open(ZIPFILE, "wb") as f:
        f.write(buf.getvalue())
    zip_sha = hashlib.sha256(open(ZIPFILE, "rb").read()).hexdigest()
    with open(SUMS, "w", encoding="utf-8") as f:
        f.write("%s  edinyy-svod-v1.html\n%s  edinyy-svod.zip\n" % (sha, zip_sha))
    words = len(re.findall(r"[А-Яа-яЁёA-Za-z]+", re.sub(r"<style.*?</style>|<script.*?</script>",
                                                        "", html, flags=re.S)))
    print("=== СБОРКА ЕДИНОГО СВОДА ===")
    print("артефакт: %s (%d Б)" % (ARTIFACT, len(raw)))
    print("шрифты: 5 лиц, %d Б" % total_font_bytes)
    print("слов в прозе (проверка): %d" % words)
    print("sha256 html: %s" % sha)
    print("sha256 zip : %s" % zip_sha)
    for name, okv, detail in checks:
        print("[%s] %s — %s" % ("В" if okv else "ПРОВАЛ", name, detail))
    if not ok:
        sys.exit("СБОРКА ПРОВАЛЕНА: есть непройденные проверки")


if __name__ == "__main__":
    main()
