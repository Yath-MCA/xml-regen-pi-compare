"""The shared HTML page shell (CSS + JS + page()) used by every report."""
from ..config import *  # noqa: F401,F403
from .text import *     # noqa: F401,F403

# --------------------------------------------------------------------- pages

CSS = """
*{box-sizing:border-box}
body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0;color:#1f2328}
header#top{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid #d0d7de;
  padding:12px 24px;display:flex;flex-wrap:wrap;align-items:center;gap:8px 20px}
header#top .ttl{font-size:18px;font-weight:700}
.chips{display:flex;flex-wrap:wrap;gap:6px;flex:1}
.chip{font-size:12px;background:#f6f8fa;border:1px solid #d0d7de;border-radius:999px;padding:2px 10px;color:#57606a}
.chip b{color:#1f2328;font-weight:600}
.chip.warn{background:#ffebe9;border-color:#f0625d;color:#b42318}
.chip.good{background:#dafbe1;border-color:#4ac26b;color:#1a7f37}
main{padding:16px 24px 32px}
.legend{font-size:12px;color:#57606a;margin-bottom:12px}
.legend .pi{padding:0 4px}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:14px;
  border-left:1px solid #d0d7de;border-top:1px solid #d0d7de}
th,td{border-right:1px solid #d0d7de;border-bottom:1px solid #d0d7de;padding:8px 10px;
  text-align:left;vertical-align:top}
th{background:#f6f8fa}
table.files th{position:sticky;top:calc(var(--hh,64px) + var(--th,0px));z-index:2}
tr:nth-child(even) td{background:#fafbfc}
td.fid{white-space:nowrap;font-weight:600}
td.na{color:#9aa4ad}
td.err{color:#b42318;background:#fff1f0}
td.docid{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#57606a;word-break:break-all}
td.chk ul{margin:0;padding-left:16px;font-size:12px;color:#b42318}
td.chk .ok{color:#1a7f37;font-size:12px}
.pi{background:#fff3b0;border-radius:2px}
.pi.bad{background:#ffd8d3;outline:1px solid #f0625d}
.pi.miss{background:#ffd8d3;color:#b42318;font-weight:700;padding:0 2px;outline:1px solid #f0625d}
.badge{display:inline-block;margin-left:6px;font-size:11px;font-weight:600;color:#b42318;
  background:#ffebe9;border:1px solid #f0625d;border-radius:999px;padding:0 7px;cursor:help}
.toggle{display:inline-flex;border:1px solid #d0d7de;border-radius:6px;overflow:hidden}
.toggle button{border:0;background:#fff;padding:6px 14px;font-size:13px;cursor:pointer;color:#1f2328}
.toggle button.on{background:#0969da;color:#fff}
body[data-view=preview] .v-raw{display:none}
body[data-view=raw] .v-preview{display:none}
pre.raw{margin:0;font:12px/1.45 ui-monospace,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;tab-size:2}
sup{font-size:.75em}
a{color:#0969da;text-decoration:none} a:hover{text-decoration:underline}
tr[id]{scroll-margin-top:calc(var(--hh,64px) + var(--th,0px) + 44px)}
tr:target td{background:#fff8c5!important}
.tags{margin-top:6px;display:flex;gap:4px;flex-wrap:wrap}
.tag{font-size:11px;border:1px solid #d0d7de;border-radius:4px;padding:0 5px;color:#57606a;background:#fff}
.tag.bad{border-color:#f0625d;background:#ffebe9;color:#b42318;font-weight:600}
.hlinks{display:flex;gap:8px}
.hlinks a{font-size:13px;border:1px solid #d0d7de;border-radius:6px;padding:4px 10px;background:#fff}
.elems{padding:4px 14px 14px}
.elems h3{font-size:14px;margin:16px 0 6px}
.elems small{color:#57606a}
table.elem{width:100%;margin-bottom:16px}
table.elem th{position:static}
table.elem td{vertical-align:top;font-size:13px}
table.elem details{font-size:12px}
table.elem summary{cursor:pointer}
.part{background:#fff8c5;border:1px solid #d4a72c;border-radius:999px;padding:0 6px;font-size:11px;color:#7d4e00}
.pv{margin-top:6px;padding:6px 8px;background:#fff;border:1px dashed #d0d7de;border-radius:6px;font-size:13px}
.pv-l{display:block;font-size:11px;color:#57606a;margin-bottom:2px}
.okbox{margin-bottom:20px;padding:10px 14px;border:1px solid #4ac26b;background:#dafbe1;color:#1a7f37;border-radius:8px;font-size:13px}
table.fix{width:calc(100% - 24px);margin:12px}
table.fix th{position:static}
table.fix td{font-size:13px;vertical-align:top}
table.fix td.det{font-size:12px}
.toolbar{margin:0 0 10px;font-size:13px}
table.files.only tr[data-row]:not([data-issue]){display:none}
.flag{display:inline-block;margin:1px 3px 1px 0;font-size:11px;border-radius:999px;padding:0 7px;border:1px solid #d0d7de;background:#f6f8fa;color:#57606a;cursor:help}
.flag.partial{background:#fff8c5;border-color:#d4a72c;color:#7d4e00}
.flag.rare{background:#fbefff;border-color:#c297ff;color:#6e40c9}
.flag.repeats{background:#ddf4ff;border-color:#54aeff;color:#0550ae}
.flag.empty{background:#eaeef2;border-color:#8c959f;color:#424a53}
.rv{background:#fbefff;border-radius:3px;padding:0 3px;color:#6e40c9}
.tag.xref{background:#ddf4ff;border-color:#54aeff;color:#0550ae}
.xg{margin-bottom:14px}
.xg-h{display:flex;gap:8px;align-items:baseline;margin:0 0 6px;font-size:13px}
.xg-h b{background:#ddf4ff;border:1px solid #54aeff;border-radius:999px;padding:0 9px;color:#0550ae}
.xg-h .cnt{color:#57606a;font-size:12px}
details.stats{margin-bottom:20px;border:1px solid #d0d7de;border-radius:8px;background:#fff}
details.stats>summary{cursor:pointer;font-weight:600;padding:10px 14px;background:#f6f8fa;border-radius:8px}
details.stats>summary .sub{font-weight:400;color:#57606a;font-size:12px;margin-left:8px}
table.stat{width:calc(100% - 24px);margin:12px}
table.stat th{position:static}
table.stat th.rl{white-space:nowrap;width:1%}
table.stat td{background:#fff!important;width:33%}
.pat{border:1px solid #d0d7de;border-radius:6px;padding:8px;margin-bottom:8px;background:#fff}
.pat.minor{border-color:#f0625d;background:#fff8f7}
.pat.na{background:#f6f8fa}
.pat-h{font-size:13px;margin-bottom:6px;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.pat-h .cnt{font-weight:700}
.pat-h .pct{color:#57606a;font-size:12px}
.pat-h .lbl{font-size:11px;padding:0 6px;border-radius:999px;border:1px solid #d0d7de;color:#57606a}
.pat.minor .lbl{border-color:#f0625d;color:#b42318}
ol.seq{margin:0 0 6px;padding-left:22px;font-size:12px}
ol.seq li{margin:2px 0}
ol.seq li.none{list-style:none;color:#9aa4ad;margin-left:-22px}
ol.seq li.bad code{background:#ffd8d3;outline:1px solid #f0625d}
code.tok{background:#eef1f4;border-radius:3px;padding:0 4px;font:12px ui-monospace,Consolas,monospace;white-space:pre-wrap}
.diff{font-size:12px;margin:4px 0 6px}
.diff .k{font-size:11px;text-transform:uppercase;margin-right:4px}
.diff .k.differs{color:#9a6700}.diff .k.missing{color:#b42318}.diff .k.extra{color:#8250df}
.pat details{font-size:12px}
.pat summary{cursor:pointer;color:#57606a}
.frow{display:flex;gap:8px;align-items:baseline;padding:2px 0}
.frow a{font-weight:600;white-space:nowrap}
.frow .did{font:11px ui-monospace,Consolas,monospace;color:#57606a;word-break:break-all}
nav.tabs{position:sticky;top:var(--hh,64px);z-index:4;background:#fff;display:flex;flex-wrap:wrap;align-items:center;
  gap:4px 6px;padding:8px 0 0;margin:0 0 14px;border-bottom:2px solid #d0d7de}
nav.tabs button[role=tab]{border:1px solid #d0d7de;border-bottom:0;background:#f6f8fa;color:#1f2328;padding:8px 14px;
  font-size:14px;cursor:pointer;border-radius:8px 8px 0 0;margin-bottom:-2px}
nav.tabs button[role=tab][aria-selected=true]{background:#fff;border-color:#0969da;border-bottom:2px solid #fff;font-weight:700;color:#0969da}
nav.tabs .n{font-size:12px;color:#57606a;margin-left:4px;background:#eaeef2;border-radius:999px;padding:0 7px}
nav.tabs .w{font-size:12px;color:#b42318;margin-left:4px;background:#ffebe9;border:1px solid #f0625d;border-radius:999px;padding:0 6px}
nav.tabs .tools{margin-left:auto;display:flex;gap:12px;align-items:center;font-size:13px;padding-bottom:6px}
nav.tabs input[type=search]{font-size:13px;padding:4px 8px;border:1px solid #d0d7de;border-radius:6px;width:220px}
html.js .pane{display:none}
html.js .pane.on{display:block}
@media print{html.js .pane{display:block!important}nav.tabs{display:none}}
.ghead{font-size:14px;margin:0 0 12px;color:#1f2328}
.small{font-size:11px;color:#7d4e00;background:#fff8c5;border:1px solid #d4a72c;border-radius:999px;padding:0 7px;margin-left:6px}
.cb{font-size:11px;font-weight:400;color:#57606a;background:#eaeef2;border-radius:999px;padding:0 6px;margin-left:4px}
.ctl{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:center;margin:10px 12px 0}
.seg{display:inline-flex;align-items:center;border:1px solid #d0d7de;border-radius:6px;overflow:hidden}
.seg button{border:0;background:#fff;padding:4px 12px;font-size:12px;cursor:pointer;color:#1f2328}
.seg button.on{background:#0969da;color:#fff}
.seg .seg-l{font-size:12px;color:#57606a;padding:0 8px;background:#f6f8fa;align-self:stretch;display:flex;align-items:center}
body[data-kind=attr] tr.kr-pos{display:none}
body[data-kind=pos] tr.kr-attr{display:none}
.pane[data-xref="0"] .xg:not([data-xk="0"]),.pane[data-xref="1"] .xg:not([data-xk="1"]),
.pane[data-xref="2"] .xg:not([data-xk="2"]),.pane[data-xref="3"] .xg:not([data-xk="3"]){display:none}
tr.hid{display:none}
tr.flash td{background:#fff8c5!important}
.emptymsg{padding:10px 14px;color:#57606a;font-size:13px}
button.copy,button.pv-next{font-size:11px;border:1px solid #d0d7de;border-radius:6px;background:#fff;padding:1px 8px;cursor:pointer;color:#0969da}
button.copy.done{background:#dafbe1;border-color:#4ac26b;color:#1a7f37}
.frow-tools{margin:4px 0}
.pvs .pv[hidden]{display:none}
.pvs{margin-top:6px}
.pvs .pv{margin-top:0;margin-bottom:4px}
tr.cg-bad td{background:#fff8f7!important}
.okmark{color:#1a7f37;font-weight:600}
.cg-n{font-size:11px;color:#57606a}
.cg-l{margin:2px 0;font-size:12px}
.cg-bad .k.differs{color:#9a6700;text-transform:uppercase;font-size:11px}
"""

TOGGLE = (
    '<div class="toggle" role="group" aria-label="Column view">'
    '<button type="button" data-view="preview" class="on">Preview HTML</button>'
    '<button type="button" data-view="raw">Raw XML</button></div>'
)

LEGEND = (
    '<div class="legend"><span class="pi">text</span> restored from pistart &middot; '
    '<span class="pi bad">text</span> differs from the most common value at the same position &middot; '
    '<span class="pi miss">&#9888;</span> pistart missing where other files have it</div>'
)

JS = """<script>
(function () {
  var root = document.documentElement, body = document.body;
  var hdr = document.getElementById('top');
  var nav = document.querySelector('nav.tabs');
  function fit() {
    root.style.setProperty('--hh', hdr.offsetHeight + 'px');
    root.style.setProperty('--th', (nav ? nav.offsetHeight : 0) + 'px');
  }
  fit(); window.addEventListener('resize', fit); window.addEventListener('load', fit);

  var tabs = [].slice.call(document.querySelectorAll('nav.tabs [data-tab]'));
  var panes = [].slice.call(document.querySelectorAll('.pane'));
  var state = { tab: nav ? nav.getAttribute('data-default') : '' };
  var cb = document.getElementById('onlyIssues'), q = document.getElementById('q');

  function setTab(id) {
    if (!panes.length || !document.getElementById('pane-' + id)) return;
    state.tab = id;
    panes.forEach(function (p) { p.classList.toggle('on', p.getAttribute('data-pane') === id); });
    tabs.forEach(function (t) { t.setAttribute('aria-selected', t.getAttribute('data-tab') === id ? 'true' : 'false'); });
    fit();
  }
  function setKind(k) {
    if (['both', 'attr', 'pos'].indexOf(k) < 0) k = 'both';
    body.setAttribute('data-kind', k);
    [].forEach.call(document.querySelectorAll('.seg.kind button'), function (b) {
      b.classList.toggle('on', b.getAttribute('data-kind') === k);
    });
  }
  function sync() {
    if (!panes.length) return;
    try { history.replaceState(null, '', '#tab=' + state.tab + '&kind=' + body.getAttribute('data-kind')); } catch (e) {}
  }
  function applyFilter() {
    var only = cb && cb.checked, s = q ? q.value.trim().toLowerCase() : '';
    panes.forEach(function (p) {
      var rows = p.querySelectorAll('tr[data-row]'), shown = 0;
      [].forEach.call(rows, function (tr) {
        var hide = (only && !tr.hasAttribute('data-issue')) || (s && (tr.getAttribute('data-s') || '').indexOf(s) < 0);
        tr.classList.toggle('hid', hide);
        if (!hide) shown++;
      });
      var m = p.querySelector('.emptymsg');
      if (m) m.style.display = rows.length && !shown ? 'block' : 'none';
    });
  }
  function gotoRow(id) {
    var el = document.getElementById(id);
    if (!el) return;
    var pane = el.closest('.pane');
    if (pane) setTab(pane.getAttribute('data-pane'));
    if (el.classList.contains('hid')) { if (cb) cb.checked = false; if (q) q.value = ''; applyFilter(); }
    for (var d = el.parentElement; d; d = d.parentElement) if (d.tagName === 'DETAILS') d.open = true;
    el.scrollIntoView({ block: 'start' });
    el.classList.add('flash');
    setTimeout(function () { el.classList.remove('flash'); }, 2500);
  }
  function route() {
    var h = decodeURIComponent(location.hash.slice(1));
    if (h.indexOf('row-') === 0) { gotoRow(h); return; }
    if (h.indexOf('tab=') >= 0 || h.indexOf('kind=') >= 0) {
      var p = {};
      h.split('&').forEach(function (kv) { var a = kv.split('='); p[a[0]] = a[1]; });
      if (p.kind) setKind(p.kind);
      if (p.tab) setTab(p.tab);
    }
  }

  setKind('both');
  if (state.tab) setTab(state.tab);
  route();
  window.addEventListener('hashchange', route);
  if (cb) cb.addEventListener('change', applyFilter);
  if (q) q.addEventListener('input', applyFilter);

  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { setTab(t.getAttribute('data-tab')); sync(); });
    t.addEventListener('keydown', function (e) {
      var j = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : -1;
      if (j < 0) return;
      j = (j + tabs.length) % tabs.length;
      tabs[j].focus(); setTab(tabs[j].getAttribute('data-tab')); sync(); e.preventDefault();
    });
  });

  document.addEventListener('click', function (e) {
    var t = e.target;
    var a = t.closest && t.closest('a[href^="#row-"]');
    if (a) {
      e.preventDefault();
      var href = a.getAttribute('href');
      if (location.hash !== href) { try { history.pushState(null, '', href); } catch (x) {} }
      gotoRow(decodeURIComponent(href.slice(1)));
      return;
    }
    var b = t.closest && t.closest('.toggle button');
    if (b) {
      body.setAttribute('data-view', b.getAttribute('data-view'));
      [].forEach.call(document.querySelectorAll('.toggle button'), function (x) { x.classList.toggle('on', x === b); });
      return;
    }
    b = t.closest && t.closest('.seg.kind button');
    if (b) { setKind(b.getAttribute('data-kind')); sync(); return; }
    b = t.closest && t.closest('.seg.xref button');
    if (b) {
      var pane = b.closest('.pane');
      pane.setAttribute('data-xref', b.getAttribute('data-x'));
      [].forEach.call(b.parentNode.querySelectorAll('button'), function (x) { x.classList.toggle('on', x === b); });
      return;
    }
    b = t.closest && t.closest('button.pv-next');
    if (b) {
      var items = [].slice.call(b.parentNode.querySelectorAll('.pv'));
      var cur = items.findIndex(function (x) { return !x.hasAttribute('hidden'); });
      var nx = (cur + 1) % items.length;
      items.forEach(function (x, k) { if (k === nx) x.removeAttribute('hidden'); else x.setAttribute('hidden', ''); });
      b.textContent = 'next sample (' + (nx + 1) + '/' + items.length + ')';
      return;
    }
    b = t.closest && t.closest('button.copy');
    if (b) {
      var text = b.getAttribute('data-ids'), old = b.textContent;
      var ok = function () {
        b.classList.add('done'); b.textContent = 'copied';
        setTimeout(function () { b.classList.remove('done'); b.textContent = old; }, 1500);
      };
      var fallback = function () {
        var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta);
        ta.select(); try { document.execCommand('copy'); ok(); } catch (x) {} document.body.removeChild(ta);
      };
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(ok, fallback);
      else fallback();
    }
  });
})();
</script>"""


def page(title: str, chips: list, body: str, toggle: bool = False, links=None, legend: bool = True) -> str:
    """chips: list of (label, value, style) with style in '', 'warn', 'good'."""
    chips_html = "".join(
        f'<span class="chip {style}"><b>{esc(label)}</b> {esc(str(value))}</span>'
        for label, value, style in chips
    )
    links_html = "".join(f'<a href="{esc_attr(h)}">{esc(l)}</a>' for l, h in (links or []))
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title><script>document.documentElement.className+=' js'</script><style>{CSS}</style></head>"
        '<body data-view="preview">'
        f'<header id="top"><div class="ttl">{esc(title)}</div>'
        f'<div class="chips">{chips_html}</div><div class="hlinks">{links_html}</div>{TOGGLE if toggle else ""}</header>'
        f"<main>{LEGEND if legend else ''}{body}</main>{JS}</body></html>"
    )


def issue_chip(n: int) -> tuple:
    return ("PI issues (all contribs)", n, "warn" if n else "good")


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


