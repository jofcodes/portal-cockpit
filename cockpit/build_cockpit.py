#!/usr/bin/env python3
"""Build the Cockpit dashboard — one self-contained HTML page for the Portal.

Reads portal_data/{brief,inbox,workplace,wrap}.json and renders a four-tab
glanceable UI: Now/Next · Inbox · Workplace · Wrap. All data is inlined into the
page so it works offline inside the Portal WebView (no network, no file fetches),
exactly like the beehive dashboard.

    python -m cockpit.build_cockpit
    python cockpit/build_cockpit.py --open   # also open the preview in a browser
"""

from __future__ import annotations

import argparse
import json
import logging
import webbrowser
from datetime import datetime

from .config import DASHBOARD_ASSET, DASHBOARD_PREVIEW, PORTAL_DATA_DIR

log = logging.getLogger("cockpit.build")


def _load(name: str) -> dict:
    path = PORTAL_DATA_DIR / f"{name}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            log.warning("Bad JSON in %s", path)
    return {}


def generate() -> str:
    data = {
        "brief": _load("brief"),
        "inbox": _load("inbox"),
        "workplace": _load("workplace"),
        "wrap": _load("wrap"),
        "meetings": _load("meetings"),
    }
    blob = json.dumps(data).replace("</", "<\\/")  # safe to embed in <script>
    generated = datetime.now().strftime("%a %b %-d · %-I:%M %p")
    return _TEMPLATE.replace("__DATA__", blob).replace("__GENERATED__", generated)


def build(open_preview: bool = False) -> None:
    html = generate()
    DASHBOARD_PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_PREVIEW.write_text(html)
    log.info("Wrote preview %s", DASHBOARD_PREVIEW)
    if DASHBOARD_ASSET.parent.exists() or True:
        DASHBOARD_ASSET.parent.mkdir(parents=True, exist_ok=True)
        DASHBOARD_ASSET.write_text(html)
        log.info("Wrote app asset %s", DASHBOARD_ASSET)
    if open_preview:
        webbrowser.open(f"file://{DASHBOARD_PREVIEW}")


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Cockpit</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  :root {
    --bg:#0e1117; --panel:#161b24; --panel2:#1d2430; --line:#283142;
    --txt:#e8edf4; --muted:#94a3b8; --accent:#5b9dff; --accent2:#9d7bff;
    --good:#3ecf8e; --warn:#ffb454; --bad:#ff6b6b;
  }
  html,body { height:100%; }
  body {
    background:var(--bg); color:var(--txt);
    font-family:-apple-system,system-ui,"Segoe UI",Roboto,sans-serif;
    height:100vh; width:100vw; overflow:hidden; display:flex; flex-direction:column;
  }
  header {
    display:flex; align-items:center; justify-content:space-between;
    padding:14px 22px; background:linear-gradient(135deg,#11161f,#1a2230);
    border-bottom:1px solid var(--line);
  }
  header .brand { display:flex; align-items:center; gap:12px; }
  header h1 { font-size:1.5em; font-weight:700; letter-spacing:.5px; }
  header .clock { font-variant-numeric:tabular-nums; color:var(--muted); font-size:1.1em; }
  header .ctrls button {
    background:var(--panel2); color:var(--txt); border:1px solid var(--line);
    border-radius:10px; padding:8px 14px; font-size:.95em; margin-left:8px; cursor:pointer;
  }
  header .ctrls button:active { background:var(--accent); border-color:var(--accent); }
  nav {
    display:flex; gap:6px; padding:10px 16px; background:var(--bg);
    border-bottom:1px solid var(--line); flex-shrink:0;
  }
  nav button {
    flex:1; padding:12px; font-size:1.05em; font-weight:600; border:none; cursor:pointer;
    background:transparent; color:var(--muted); border-radius:12px; transition:all .15s;
  }
  nav button.active { background:var(--panel2); color:var(--txt); box-shadow:inset 0 -3px 0 var(--accent); }
  main { flex:1; overflow-y:auto; padding:18px 22px 40px; }
  .tab { display:none; } .tab.active { display:block; animation:fade .2s; }
  @keyframes fade { from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:none;} }
  .headline { font-size:1.5em; line-height:1.35; font-weight:600; margin-bottom:16px; }
  .card {
    background:var(--panel); border:1px solid var(--line); border-radius:16px;
    padding:16px 18px; margin-bottom:14px;
  }
  .card h3 { font-size:.8em; text-transform:uppercase; letter-spacing:1.2px; color:var(--muted); margin-bottom:12px; }
  .row { display:flex; gap:12px; padding:10px 0; border-bottom:1px solid var(--line); }
  .row:last-child { border-bottom:none; }
  .row .when { color:var(--accent); font-weight:700; font-variant-numeric:tabular-nums; min-width:64px; }
  .row .what { flex:1; }
  .row .sub { color:var(--muted); font-size:.88em; margin-top:2px; }
  .next {
    background:linear-gradient(135deg,#1a2742,#231a42); border:1px solid #34406a;
    border-radius:18px; padding:20px; margin-bottom:18px;
  }
  .next .label { color:var(--accent); font-size:.8em; text-transform:uppercase; letter-spacing:1.2px; }
  .next .title { font-size:1.7em; font-weight:700; margin:6px 0; }
  .next .meta { color:var(--muted); }
  .pill { display:inline-block; padding:3px 10px; border-radius:20px; font-size:.75em; font-weight:700; margin-left:8px; }
  .pill.high { background:#3a1d22; color:var(--bad); } .pill.medium { background:#3a2f1d; color:var(--warn); }
  .pill.low { background:#1d2a3a; color:var(--accent); }
  .focus li { list-style:none; padding:8px 0 8px 26px; position:relative; font-size:1.05em; }
  .focus li:before { content:"›"; position:absolute; left:6px; color:var(--accent); font-weight:700; }
  .draft { background:var(--panel2); border-left:3px solid var(--accent2); border-radius:8px;
           padding:10px 12px; margin-top:8px; font-size:.92em; color:var(--muted); }
  .badge-sample { background:var(--warn); color:#1a1206; padding:2px 9px; border-radius:8px; font-size:.7em; font-weight:700; }
  .post { white-space:pre-wrap; line-height:1.5; background:var(--panel2); border-radius:12px; padding:16px; margin-top:10px; }
  .stat { display:inline-block; margin-right:24px; }
  .stat b { font-size:1.8em; display:block; color:var(--accent); }
  .stat span { color:var(--muted); font-size:.85em; }
  .empty { color:var(--muted); text-align:center; padding:40px 0; font-size:1.1em; }
  .ann { color:var(--muted); font-size:.8em; margin-top:18px; text-align:center; }
</style></head><body>

<header>
  <div class="brand"><h1>🛫 Cockpit</h1><span id="clock" class="clock"></span></div>
  <div class="ctrls">
    <button onclick="doRefresh()">↻ Refresh</button>
    <button onclick="doExit()">✕ Exit</button>
  </div>
</header>

<nav>
  <button class="active" data-tab="now">Now / Next</button>
  <button data-tab="inbox">Inbox</button>
  <button data-tab="workplace">Workplace</button>
  <button data-tab="wrap">Wrap</button>
</nav>

<main>
  <section id="now" class="tab active"></section>
  <section id="inbox" class="tab"></section>
  <section id="workplace" class="tab"></section>
  <section id="wrap" class="tab"></section>
</main>

<script>
const DATA = __DATA__;
const GENERATED = "__GENERATED__";
const esc = s => (s==null?"":String(s)).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
const sampleBadge = o => (o && o.sample) ? ' <span class="badge-sample">SAMPLE</span>' : '';

function renderNow() {
  const b = DATA.brief || {};
  const n = b.next_meeting;
  let h = '';
  if (b.headline) h += `<div class="headline">${esc(b.headline)}${sampleBadge(b)}</div>`;
  if (n) h += `<div class="next"><div class="label">Next up</div>
      <div class="title">${esc(n.summary||"Meeting")}</div>
      <div class="meta">${esc(n.start||"")} · ${esc(n.location||"")}</div></div>`;
  // A3 — meeting prep packet for the next meeting
  const mp = DATA.meetings || {};
  if (mp.next_meeting && (mp.prep_note || (mp.attendees||[]).length)) {
    h += `<div class="card"><h3>Meeting prep${sampleBadge(mp)}</h3>`;
    if (mp.prep_note) h += `<div style="margin-bottom:10px">${esc(mp.prep_note)}</div>`;
    if ((mp.attendees||[]).length) h += `<div class="sub" style="margin-bottom:6px">With: `
        + mp.attendees.map(a=>esc(a.name) + (a.title?` (${esc(a.title)})`:"")).join(', ') + `</div>`;
    if ((mp.threads||[]).length) h += mp.threads.map(t=>
        `<div class="row"><span class="what">${esc(t.subject||"")}<div class="sub">${esc(t.from||"")}</div></span></div>`).join('');
    h += `</div>`;
  }
  if (b.focus && b.focus.length) h += `<div class="card"><h3>Today's focus</h3><ul class="focus">`
      + b.focus.map(f=>`<li>${esc(f)}</li>`).join('') + `</ul></div>`;
  if (b.agenda && b.agenda.length) h += `<div class="card"><h3>Agenda</h3>`
      + b.agenda.map(e=>`<div class="row"><span class="when">${esc(e.start||"")}</span>
          <span class="what">${esc(e.summary||"")}<div class="sub">${esc(e.location||"")}</div></span></div>`).join('')
      + `</div>`;
  if (b.docs && b.docs.length) h += `<div class="card"><h3>Shared with you</h3>`
      + b.docs.map(d=>`<div class="row"><span class="what">${esc(d.name||"")}<div class="sub">${esc(d.owner||"")}</div></span></div>`).join('')
      + `</div>`;
  return h || `<div class="empty">No morning brief yet — run the brief job.</div>`;
}

function renderInbox() {
  const x = DATA.inbox || {};
  let h = '';
  h += `<div class="card"><span class="stat"><b>${x.unread_count||0}</b><span>unread</span></span>
        <span class="stat"><b>${x.drafted_count||0}</b><span>replies drafted</span></span>
        <span class="stat"><b>${(x.awaiting||[]).length}</b><span>waiting on</span></span>${sampleBadge(x)}</div>`;
  if (x.priority && x.priority.length) h += `<div class="card"><h3>Priority</h3>`
      + x.priority.map(m=>`<div class="row"><span class="what">${esc(m.subject||"")}
          <span class="pill ${esc(m.priority||"medium")}">${esc(m.priority||"")}</span>
          <div class="sub">${esc(m.from||"")}${m.needs_reply?" · reply suggested":""}</div></span></div>`).join('')
      + `</div>`;
  if (x.drafts && x.drafts.length) h += `<div class="card"><h3>Drafted replies — review before sending</h3>`
      + x.drafts.map(d=>`<div class="row"><span class="what">${esc(d.subject||"")}
          <div class="sub">to ${esc(d.to||"")}</div><div class="draft">${esc(d.preview||"")}</div></span></div>`).join('')
      + `</div>`;
  if (x.nudges && x.nudges.length) h += `<div class="card"><h3>Waiting on — draft nudges</h3>`
      + x.nudges.map(d=>`<div class="row"><span class="what">${esc(d.subject||"")}
          <div class="sub">to ${esc(d.to||"")} · ${esc(d.sent_ago||"")}</div>
          <div class="draft">${esc(d.preview||"")}</div></span></div>`).join('')
      + `</div>`;
  return h || `<div class="empty">No inbox data yet — run the inbox job.</div>`;
}

function renderWorkplace() {
  const w = DATA.workplace || {};
  if (!w.draft) return `<div class="empty">No Top of Mind draft yet — runs Monday mornings.</div>`;
  return `<div class="card"><h3>Monday Top of Mind — draft ready${sampleBadge(w)}</h3>
      <div class="sub">Group: ${esc(w.group||"(not set)")}</div>
      <div class="post">${esc(w.draft)}</div>
      ${w.doc_url?`<div class="sub" style="margin-top:10px">Staged in Doc: ${esc(w.doc_url)}</div>`:""}
      <div class="sub" style="margin-top:8px">Review &amp; approve before posting — nothing is auto-posted.</div></div>`;
}

function renderWrap() {
  const x = DATA.wrap || {};
  let h = '';
  if (x.recap) h += `<div class="headline">${esc(x.recap)}${sampleBadge(x)}</div>`;
  h += `<div class="card"><span class="stat"><b>${x.meetings_today||0}</b><span>meetings today</span></span>
        <span class="stat"><b>${x.unread_remaining||0}</b><span>unread left</span></span></div>`;
  if (x.tomorrow && x.tomorrow.length) h += `<div class="card"><h3>Tomorrow</h3>`
      + x.tomorrow.map(e=>`<div class="row"><span class="when">${esc(e.start||"")}</span>
          <span class="what">${esc(e.summary||"")}<div class="sub">${esc(e.location||"")}</div></span></div>`).join('')
      + `</div>`;
  return h || `<div class="empty">No wrap yet — runs at 5pm.</div>`;
}

function render() {
  document.getElementById('now').innerHTML = renderNow() + `<div class="ann">Updated ${esc(GENERATED)}</div>`;
  document.getElementById('inbox').innerHTML = renderInbox();
  document.getElementById('workplace').innerHTML = renderWorkplace();
  document.getElementById('wrap').innerHTML = renderWrap();
}

// Tabs
document.querySelectorAll('nav button').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(btn.dataset.tab).classList.add('active');
}));

// Clock
function tick(){ const d=new Date(); document.getElementById('clock').textContent =
  d.toLocaleString(undefined,{weekday:'short',hour:'numeric',minute:'2-digit'}); }
tick(); setInterval(tick, 15000);

// Android bridge (window.Cockpit) with browser fallbacks
function doExit(){ try{ if(window.Cockpit&&Cockpit.exit){Cockpit.exit();return;} }catch(e){} history.back(); }
function doRefresh(){ try{ if(window.Cockpit&&Cockpit.refresh){Cockpit.refresh();return;} }catch(e){}
  location.reload(); }

render();
</script>
</body></html>"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true", help="Open the preview in a browser")
    args = ap.parse_args()
    build(open_preview=args.open)
    print(f"Built dashboard → {DASHBOARD_PREVIEW}")


if __name__ == "__main__":
    main()
